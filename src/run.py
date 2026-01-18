#!/usr/bin/env python3
import os
import sys
import warnings
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright

# Suppress urllib3 v2 OpenSSL warning on macOS
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL 1.1.1+")

# Ensure src is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modular components
from session_manager import create_session, load_session, save_session, setup_directories, get_cookie_path
from captcha import solve_stooq_captcha
from configurator import configure_stooq_settings
from link_finder import get_latest_download_link
from downloader import download_with_browser, clean_downloaded_data

def main():
    parser = argparse.ArgumentParser(description="Stooq Data Downloader")
    parser.add_argument("--force", action="store_true", help="Force download even if files exist")
    args = parser.parse_args()

    # Print execution time
    now = datetime.now()
    try:
        cet = now.astimezone(ZoneInfo("Europe/Warsaw"))
        cet_str = cet.strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        cet_str = "CET conversion failed"
        
    print(f"⏰ Execution Time: {now.strftime('%Y-%m-%d %H:%M:%S')}  ({cet_str})")

    data_dir, cookie_dir = setup_directories()
    cookie_path = get_cookie_path(cookie_dir)
    session = create_session()
    
    # Try to load session
    if load_session(session, cookie_path):
        print("✅ Received existing session cookies.")
    else:
        print("ℹ️  No existing session. Starting fresh.")

    # ---------------------------------------------------------
    # STEP 1: INITIAL LINK SCAN
    # ---------------------------------------------------------
    print("\n🔍 Step 1: Identifying target files from Stooq...")
    links = get_latest_download_link(session)
    if not links:
        print("⚠️  Could not find links with current session data. Will proceed to Browser flow.")
    else:
        print(f"   Found potential targets: {[name for _, name in links]}")

    # ---------------------------------------------------------
    # STEP 1.5: CHECK IF DOWNLOAD IS NEEDED
    # ---------------------------------------------------------
    skip_browser = False
    downloaded_filenames = {} # Map base_name -> actual_filename
    
    if links:
        files_exist = True
        for _, full_name in links:
            # full_name now includes .txt from link_finder
            file_path = os.path.join(data_dir, full_name)
            
            # Also check for .csv as fallback in case of legacy files
            legacy_csv = file_path.replace(".txt", ".csv")
            
            if os.path.exists(file_path):
                downloaded_filenames[full_name] = full_name
            elif os.path.exists(legacy_csv):
                downloaded_filenames[full_name] = os.path.basename(legacy_csv)
            else:
                files_exist = False
                break
        
        if files_exist and not args.force:
            print(f"✨ All target files already exist in '{data_dir}'. Stopping execution (Use --force to override).")
            return
        elif files_exist and args.force:
            print("🚀 Files exist but --force is active. Proceeding to fresh download...")
    else:
        # If no links found, we MUST run browser to find them
        pass

    # ---------------------------------------------------------
    # STEP 2 & 3 & 4: BROWSER ORCHESTRATION (Config -> Auth -> Download)
    # ---------------------------------------------------------
    if not skip_browser:
        print("\n🔐 Step 2-4: Launching Browser for Full Workflow...")
        headless_mode = True
        
        with sync_playwright() as p:
            print(f"   🌐 Browser Mode: {'HEADLESS' if headless_mode else 'VISIBLE'}")
            browser = p.chromium.launch(headless=headless_mode)
            context = browser.new_context(user_agent=session.headers.get('User-Agent'))
            
            # Load known cookies
            if session.cookies:
                for cookie in session.cookies:
                    if 'stooq.com' in cookie.domain or cookie.domain == '':
                        try:
                            context.add_cookies([{
                                'name': cookie.name, 
                                'value': cookie.value,
                                'domain': cookie.domain if cookie.domain and cookie.domain.startswith('.') else '.stooq.com',
                                'path': cookie.path if cookie.path else '/'
                            }])
                        except: pass
            
            page = context.new_page()

            # [Config]
            print("\n   ⚙️  Configuring Stooq Settings...")
            if not configure_stooq_settings(page):
                print("   ❌ Settings configuration failed. Aborting.")
                browser.close()
                return

            # [Auth]
            print("\n   🧩 Verifying Authorization & CAPTCHA...")
            if not solve_stooq_captcha(page):
                print("   ❌ Authorization failed. Aborting.")
                browser.close()
                return

            # [Save Session]
            save_session(context, session, cookie_path)
            
            # [Download]
            print("\n   📥 Downloading Files via Browser...")
            page.wait_for_timeout(1000)
            
            links = get_latest_download_link(session)
            if not links:
                 print("❌ Could not find download links even after auth. Exiting.")
                 browser.close()
                 return

            for url, expected_name in links:
                 # expected_name is used just for logging in download_with_browser
                 actual_fname = download_with_browser(page, url, expected_name, data_dir)
                 if actual_fname:
                     downloaded_filenames[expected_name] = actual_fname
                 
            browser.close()

    # ---------------------------------------------------------
    # STEP 5: VERIFY & CLEANUP
    # ---------------------------------------------------------
    print("\n🔍 Step 5: Verifying data quality...")
    all_verified = True
    
    if not links:
        print("⚠️  No links to verify.")
        return

    for _, expected_name in links:
        actual_name = downloaded_filenames.get(expected_name)
        if not actual_name:
            print(f"   ❌ Missing file record for: {expected_name}")
            all_verified = False
            continue
            
        file_path = os.path.join(data_dir, actual_name)
        if not os.path.exists(file_path):
            print(f"   ❌ File not found: {actual_name}")
            all_verified = False
            continue
            
        try:
            passed_file = True
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                content = "".join(lines)
                row_count = max(0, len(lines) - 1)
                
            print(f"   📊 {actual_name}: {row_count} rows found.")

            if "Unauthorized" in content:
                print(f"   ❌ {actual_name}: Unauthorized access detected in file content.")
                passed_file = False
            
            if passed_file:
                # Check AAPL.US in 5min/Hourly
                if "_5" in actual_name or "_h" in actual_name:
                    if "AAPL.US" in content:
                        print(f"   ✅ {actual_name} contains AAPL.US")
                    else:
                        print(f"   ❌ {actual_name} DOES NOT contain AAPL.US")
                        passed_file = False
                
                # Check 9823.JP in Daily
                if "_d" in actual_name:
                    if "9823.JP" in content:
                         print(f"   ❌ {actual_name} contains excluded ticker 9823.JP")
                         passed_file = False
                    else:
                         print(f"   ✅ {actual_name} cleanly excludes 9823.JP")

            if not passed_file:
                print(f"      🗑️ Deleting invalid file: {actual_name}")
                os.remove(file_path)
                all_verified = False

        except Exception as e:
            print(f"   ⚠️  Could not read {actual_name}: {e}")
            all_verified = False
    
    if all_verified:
        print("\n✨ SUCCESS: Data verification passed.")
    else:
        print("\n⚠️  WARNING: Data verification failed. Local invalid files removed.")
    
    clean_downloaded_data(data_dir)

if __name__ == "__main__":
    main()
