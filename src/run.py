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
    parser.add_argument("-d", "--date", type=str, help="Target date in YYYY-MM-DD format (e.g. 2026-01-17)")
    args = parser.parse_args()

    target_date_clean = None
    if args.date:
        try:
            # Validate format and convert to YYYYMMDD
            target_date_obj = datetime.strptime(args.date, "%Y-%m-%d")
            target_date_clean = target_date_obj.strftime("%Y%m%d")
            print(f"🎯 Target Date Filter: {args.date} ({target_date_clean})")
        except ValueError:
            print(f"❌ Invalid date format: {args.date}. Please use YYYY-MM-DD.")
            return

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
    # ---------------------------------------------------------
    # STEP 1: INITIAL ROW SCAN
    # ---------------------------------------------------------
    print("\n🔍 Step 1: Identifying target rows from Stooq...")
    candidate_rows = get_latest_download_link(session)
    if not candidate_rows:
        print("⚠️  Could not find download links. Will proceed to Browser flow to trigger scan.")
    else:
        # If target_date is specified, filter now
        if target_date_clean:
            # Check if any row matches the target date in its filename
            candidate_rows = [row for row in candidate_rows if any(target_date_clean in t[1] for t in row)]
            if not candidate_rows:
                print(f"❌ Target date {args.date} not found in available links.")
                return
            print(f"✅ Found matching row for {args.date}")
        
        # Check if we already have the data fully verified
        selected_row = candidate_rows[0]
        all_exist = True
        for _, full_name in selected_row:
            if not os.path.exists(os.path.join(data_dir, full_name)):
                all_exist = False
                break
        
        if all_exist and not args.force:
            target_desc = args.date if args.date else "Latest"
            print(f"✨ {target_desc} row files already exist in '{data_dir}'. Stopping execution.")
            return

    # ---------------------------------------------------------
    # STEP 2-4: BROWSER ORCHESTRATION (Config -> Auth -> Download with Fallback)
    # ---------------------------------------------------------
    print("\n🔐 Step 2-4: Launching Browser for Full Workflow...")
    headless_mode = True
    
    with sync_playwright() as p:
        print(f"   🌐 Browser Mode: {'HEADLESS' if headless_mode else 'VISIBLE'}")
        browser = p.chromium.launch(headless=headless_mode)
        context = browser.new_context(user_agent=session.headers.get('User-Agent'))
        
        # Load cookies
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
        
        # [Download Loop with Row Fallback]
        print("\n   📥 Starting Download with Row Fallback...")
        page.wait_for_timeout(1000)
        
        # Refresh candidate rows after auth (might have updated)
        candidate_rows = get_latest_download_link(session)
        if not candidate_rows:
            print("❌ No download links found after auth. Exiting.")
            browser.close()
            return

        # Apply target date filter if present
        if target_date_clean:
            candidate_rows = [row for row in candidate_rows if any(target_date_clean in t[1] for t in row)]
            if not candidate_rows:
                print(f"❌ Target date {args.date} not found in available links.")
                browser.close()
                return

        success_row_index = -1
        # Limit to top 3 rows as requested, unless a specific date is specified
        limit_rows = 3 if not target_date_clean else len(candidate_rows)
        
        for row_idx, row_links in enumerate(candidate_rows[:limit_rows]):
            print(f"\n   📂 Processing Row {row_idx + 1}/{min(limit_rows, len(candidate_rows))}: {[t[1] for t in row_links]}")
            
            downloaded_files = [] # list of full file paths for this row
            row_failed = False

            for url, expected_name in row_links:
                actual_fname = download_with_browser(page, url, expected_name, data_dir)
                if not actual_fname:
                    row_failed = True
                    break
                
                fpath = os.path.join(data_dir, actual_fname)
                downloaded_files.append(fpath)

                # IMMEDIATE VERIFICATION
                print(f"   🔍 Verifying {actual_fname}...")
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        content = "".join(lines)
                        row_count = max(0, len(lines) - 1)
                    
                    print(f"   📊 {actual_fname}: {row_count} rows found.")

                    if "Unauthorized" in content:
                        print(f"   ❌ {actual_fname}: Unauthorized access detected.")
                        row_failed = True
                    else:
                        # Required strings for ALL files
                        required_markers = ["GLD.US"]
                        missing = [m for m in required_markers if m not in content]
                        
                        if not missing:
                            print(f"   ✅ {actual_fname} contains required markers ({', '.join(required_markers)})")
                        else:
                            print(f"   ❌ {actual_fname} MISSING required markers: {', '.join(missing)}")
                            row_failed = True
                            
                except Exception as e:
                    print(f"   ⚠️  Error reading {actual_fname}: {e}")
                    row_failed = True
                
                if row_failed:
                    break

            if row_failed:
                print(f"   🗑️  Row {row_idx + 1} failed verification. Discarding partial set...")
                for fpath in downloaded_files:
                    if os.path.exists(fpath): os.remove(fpath)
                
                # If a specific date was requested, do not fallback
                if target_date_clean:
                    break
                continue

            # If we reach here, all 3 files passed verification
            print(f"   ✨ SUCCESS: Row {row_idx + 1} set passed verification.")
            success_row_index = row_idx
            break
        
        browser.close()

    if success_row_index != -1:
        print("\n✨ FINAL SUCCESS: Verified data obtained and cleaned.")
    else:
        if target_date_clean:
            print(f"\n❌ FINAL FAILURE: Data for {args.date} failed verification and was discarded.")
        else:
            print("\n❌ FINAL FAILURE: All candidate rows failed verification.")
    

if __name__ == "__main__":
    main()
