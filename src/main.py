#!/usr/bin/env python3
import os
import sys
import warnings
import argparse
import traceback
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright
from script_reporter import ScriptReporter
from dotenv import load_dotenv

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

# Load environment variables
load_dotenv()

def run(sr: ScriptReporter, args):
    """Business logic for the script"""
    target_date_clean = None
    if args.date:
        try:
            # Validate format and convert to YYYYMMDD
            target_date_obj = datetime.strptime(args.date, "%Y-%m-%d")
            target_date_clean = target_date_obj.strftime("%Y%m%d")
            print(f"Target Date Filter: {args.date} ({target_date_clean})")
        except ValueError:
            sr.fail(f"Invalid date format: {args.date}. Please use YYYY-MM-DD.")
            return False
    else:
        target_date_obj = datetime.now() - timedelta(days=1)
        target_date_clean = target_date_obj.strftime("%Y%m%d")
        print(f"Target Date (default): {target_date_obj.strftime('%Y-%m-%d')} ({target_date_clean})")

    # Print execution time
    now = datetime.now()
    try:
        cet = now.astimezone(ZoneInfo("Europe/Warsaw"))
        cet_str = cet.strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        cet_str = "CET conversion failed"

    print(f"Execution Time: {now.strftime('%Y-%m-%d %H:%M:%S')}  ({cet_str})")

    sr.stage("PREPARING")
    data_dir, cookie_dir = setup_directories()
    cookie_path = get_cookie_path(cookie_dir)
    session = create_session()

    # Try to load session
    if load_session(session, cookie_path):
        print("Received existing session cookies.")
    else:
        print("No existing session. Starting fresh.")

    # ---------------------------------------------------------
    # STEP 1: INITIAL ROW SCAN
    # ---------------------------------------------------------
    sr.stage("SCANNING_LINKS")
    print("Step 1: Identifying target rows from Stooq...")
    candidate_rows = get_latest_download_link(session)
    if not candidate_rows:
        print("Could not find download links. Will proceed to Browser flow to trigger scan.")
    else:
        # If target_date is specified, filter now
        if target_date_clean:
            # Check if any row matches the target date in its filename
            candidate_rows = [row for row in candidate_rows if any(target_date_clean in t[1] for t in row)]
            if not candidate_rows:
                sr.fail(f"Target date {args.date} not found in available links.")
                return False
            print(f"Found matching row for {args.date}")

        # Check if we already have the data fully verified
        selected_row = candidate_rows[0]
        all_exist = True
        for _, full_name in selected_row:
            if not os.path.exists(os.path.join(data_dir, full_name)):
                all_exist = False
                break

        if all_exist and not args.force:
            files_existing = [full_name for _, full_name in selected_row]
            if not args.date:
                sr.success({
                    "message": f"Latest row files already exist in '{data_dir}'. Stopping execution.",
                    "status": "skipped",
                    "files": ", ".join(files_existing)
                })
                return True
            else:
                print(f"Files for {args.date} already exist in '{data_dir}', but proceeding to refresh as requested.")

    # ---------------------------------------------------------
    # STEP 2-4: BROWSER ORCHESTRATION (Config -> Auth -> Download with Fallback)
    # ---------------------------------------------------------
    sr.stage("BROWSER_WORKFLOW")
    print("Launching Browser for Full Workflow...")
    headless_mode = True

    with sync_playwright() as p:
        print(f"   Browser Mode: {'HEADLESS' if headless_mode else 'VISIBLE'}")
        browser = p.chromium.launch(headless=headless_mode)
        context = browser.new_context(user_agent=session.headers.get('User-Agent'))

        # Load cookies
        if session.cookies:
            for cookie in session.cookies:
                domain = cookie.domain
                if 'stooq.com' in domain or domain == '':
                    try:
                        # Ensure domain has leading dot for proper subdomain matching
                        if not domain.startswith('.'):
                            domain = '.' + domain
                        context.add_cookies([{
                            'name': cookie.name,
                            'value': cookie.value,
                            'domain': domain,
                            'path': cookie.path if cookie.path else '/'
                        }])
                    except: pass

        page = context.new_page()

        # [Config]
        print("   Configuring Stooq Settings...")
        if not configure_stooq_settings(page):
            sr.fail("Settings configuration failed. Aborting.")
            browser.close()
            return False

        # [Auth]
        print("   Verifying Authorization & CAPTCHA...")
        if not solve_stooq_captcha(page):
            sr.fail("Authorization failed. Aborting.")
            browser.close()
            return False

        # [Save Session]
        save_session(context, session, cookie_path)

        # [Verify Session Validity]
        print("   Verifying session validity...")
        if not load_session(session, cookie_path):
            sr.fail("Session verification failed. Cookies may be invalid. Aborting.")
            browser.close()
            return False
        print("   Session verified as valid.")

        # [Download Loop with Row Fallback]
        sr.stage("DOWNLOADING")
        print("   Starting Download with Row Fallback...")
        page.wait_for_timeout(1000)

        # Refresh candidate rows after auth (might have updated)
        candidate_rows = get_latest_download_link(session)
        if not candidate_rows:
            sr.fail("No download links found after auth. Exiting.")
            browser.close()
            return False

        # Apply target date filter if present
        if target_date_clean:
            candidate_rows = [row for row in candidate_rows if any(target_date_clean in t[1] for t in row)]
            if not candidate_rows:
                sr.fail(f"Target date {args.date} not found in available links.")
                browser.close()
                return False

        success_row_index = -1
        # Limit to top 3 rows as requested, unless a specific date is specified
        limit_rows = 3 if not target_date_clean else len(candidate_rows)

        for row_idx, row_links in enumerate(candidate_rows[:limit_rows]):
            print(f"\n   Processing Row {row_idx + 1}/{min(limit_rows, len(candidate_rows))}: {[t[1] for t in row_links]}")

            downloaded_files = [] # list of full file paths for this row
            row_failed = False
            unauthorized_detected = False

            for url, expected_name in row_links:
                sr.stage(f"Downloading {expected_name}")
                actual_fname = download_with_browser(page, url, expected_name, data_dir)
                if not actual_fname:
                    row_failed = True
                    break

                fpath = os.path.join(data_dir, actual_fname)
                downloaded_files.append(fpath)

                # IMMEDIATE VERIFICATION
                print(f"   Verifying {actual_fname}...")
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        content = "".join(lines)
                        row_count = max(0, len(lines) - 1)

                    print(f"   {actual_fname}: {row_count} rows found.")

                    if "Unauthorized" in content:
                        print(f"   {actual_fname}: Unauthorized access detected.")
                        unauthorized_detected = True
                        row_failed = True
                        break
                    elif row_count < 5:
                        print(f"   {actual_fname}: File has insufficient data ({row_count} rows, minimum 5 required).")
                        row_failed = True
                    else:
                        env_markers = os.getenv("STOOQ_VERIFICATION_MARKERS", "")
                        required_markers = [m.strip() for m in env_markers.split(",") if m.strip()] if env_markers else ["AAPL.US", "^SPX", "^DJI", "GLD.US"]

                        found_markers = [m for m in required_markers if m in content]
                        missing_markers = [m for m in required_markers if m not in content]

                        if found_markers:
                            print(f"   {actual_fname} contains {len(found_markers)} verification marker(s): {', '.join(found_markers)}")
                            if missing_markers:
                                print(f"   Note: Missing markers: {', '.join(missing_markers)}")
                        else:
                            print(f"   {actual_fname} MISSING all verification markers: {', '.join(required_markers)}")
                            row_failed = True

                except Exception as e:
                    print(f"   Error reading {actual_fname}: {e}")
                    row_failed = True

                if row_failed:
                    break

            if row_failed:
                # If unauthorized detected, stop everything and report error
                if unauthorized_detected:
                    print(f"   Unauthorized access detected. Stopping immediately.")
                    for fpath in downloaded_files:
                        if os.path.exists(fpath): os.remove(fpath)
                    browser.close()
                    sr.fail(f"Unauthorized access detected when downloading {expected_name}. Stopping.")
                    return False

                print(f"   Row {row_idx + 1} failed verification. Discarding partial set...")
                for fpath in downloaded_files:
                    if os.path.exists(fpath): os.remove(fpath)

                # If a specific date was requested, do not fallback
                if target_date_clean:
                    break
                continue

            # If we reach here, all 3 files passed verification
            print(f"   SUCCESS: Row {row_idx + 1} set passed verification.")
            success_row_index = row_idx
            # Capture filenames for reporting
            final_files = [os.path.basename(f) for f in downloaded_files]
            break

        browser.close()

    if success_row_index != -1:
        sr.success({
            "status": "completed",
            "message": "Verified data obtained and cleaned.",
            "files": ", ".join(final_files)
        })
        return True
    else:
        if target_date_clean:
            sr.fail(f"Data for {args.date} failed verification and was discarded.")
        else:
            sr.fail("All candidate rows failed verification.")
        return False

def main():
    parser = argparse.ArgumentParser(description="Stooq Data Downloader")
    parser.add_argument("--force", action="store_true", help="Force download even if files exist")
    parser.add_argument("-d", "--date", type=str, help="Target date in YYYY-MM-DD format (e.g. 2026-01-17)")
    args = parser.parse_args()

    sr = ScriptReporter("Stooq Data Downloader")

    try:
        run(sr, args)
    except Exception:
        sr.fail(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
