import re
import os
import datetime

def get_latest_download_link(session):
    """
    Find the latest download links for _d, _h, _5.
    If the latest '12:00' row falls on a weekend, it skips back to the most recent Friday.
    Returns filenames in YYYYMMDD_suffix.txt format (server-side filename style).
    """
    print("🔍 Searching for the latest download link...")
    try:
        res = session.get("https://stooq.com/db/", timeout=15)
        os.makedirs("tmp", exist_ok=True)
        with open("tmp/debug_db_page.html", "w") as f:
            f.write(res.text)
            
        rows = res.text.split('</tr>')
        
        # 1. Find the date of the '12:00' row (most recent daily update)
        print("🕵️  Scanning rows for '12:00' data...")
        ref_date = None
        now = datetime.datetime.now()
        year = now.year
        
        for row in rows:
            if "12:00" in row:
                date_match = re.search(r'>([^<]*12:00)<', row)
                if date_match:
                    date_str = date_match.group(1).strip()
                    # Parse date like "18 Jan, 12:00"
                    parts = re.split(r'[\s,]+', date_str)
                    if len(parts) >= 2:
                        try:
                            day = int(parts[0])
                            month_name = parts[1][:3].title()
                            months = {
                                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                            }
                            month = months.get(month_name)
                            if month:
                                # Adjust year if we are in Jan and seeing Dec data
                                row_year = year
                                if now.month == 1 and month == 12:
                                    row_year -= 1
                                ref_date = datetime.date(row_year, month, day)
                                print(f"✅ Found '12:00' row. Reference Date: {ref_date.strftime('%Y-%m-%d')} ({ref_date.strftime('%A')})")
                        except Exception as e:
                            print(f"⚠️  Could parse date part from '{date_str}', but conversion failed: {e}")
                break

        # 2. Adjust for Weekend
        target_date_str = None
        if ref_date:
            weekday = ref_date.weekday() # 0=Mon, 5=Sat, 6=Sun
            if weekday == 5: # Saturday
                ref_date = ref_date - datetime.timedelta(days=1)
                print(f"   🕒 It's Saturday. Adjusting to Friday: {ref_date.strftime('%Y-%m-%d')}")
            elif weekday == 6: # Sunday
                ref_date = ref_date - datetime.timedelta(days=2)
                print(f"   🕒 It's Sunday. Adjusting to Friday: {ref_date.strftime('%Y-%m-%d')}")
            
            # Format MMDD for searching in names (e.g. 0116)
            target_date_str = ref_date.strftime("%m%d")

        # 3. Find links for the (possibly adjusted) target date
        print(f"🎯 Searching for files matching date: {target_date_str if target_date_str else 'Latest available'}")
        
        target_links = []
        for row in rows:
            # Look for links in this row
            pattern = r'href=(?:["\'])?([^\s"\'\>]*[dt]=[^\s"\'\>]*)(?:["\'])?[^>]*>([^<]*)'
            row_links = re.findall(pattern, row)
            
            # Suffixes we need
            required = ["_d", "_h", "_5"]
            matches = {suffix: None for suffix in required}
            
            for href, text in row_links:
                for suffix in required:
                    if text.endswith(suffix):
                        # If we have a target_date_str, it MUST match the start of text
                        if target_date_str:
                            if text.startswith(target_date_str):
                                matches[suffix] = (href, text)
                        else:
                            # If no target date, just take the first one we find
                            matches[suffix] = (href, text)
            
            if all(matches.values()):
                # Determine the full YYYY prefix.
                yyyy_prefix = ""
                if ref_date:
                    yyyy_prefix = ref_date.strftime("%Y")
                else:
                    yyyy_prefix = now.strftime("%Y")

                for suffix in required:
                    href, text = matches[suffix]
                    
                    # Transform text from MMDD_suffix to YYYYMMDD_suffix.txt
                    # Server suggested filename usually has .txt extension
                    final_name = yyyy_prefix + text + ".txt"
                    
                    href = href.lstrip('/')
                    if href.startswith("http"):
                        url = href
                    elif "db/" in href:
                        url = f"https://stooq.com/{href}"
                    else:
                        url = f"https://stooq.com/db/{href}"
                    target_links.append((url, final_name))
                break # Found the row for the correct date

        if target_links:
            print(f"🎯 Selected targets (Expected Filenames): {[t[1] for t in target_links]}")
            return target_links
            
        print("⚠️  Could not find matching links for the target date.")
        return None
        
    except Exception as e:
        print(f"❌ Error while searching for links: {e}")
    return None
