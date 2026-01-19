import re
import os
import datetime

def get_latest_download_link(session):
    """
    Get the topmost (newest) row's download links for _d, _h, _5.
    Returns filenames in YYYYMMDD_suffix.txt format (server-side filename style).
    """
    print("🔍 Searching for the latest download link...")
    try:
        res = session.get("https://stooq.com/db/", timeout=15)
        os.makedirs("tmp", exist_ok=True)
        with open("tmp/debug_db_page.html", "w") as f:
            f.write(res.text)
            
        rows = res.text.split('</tr>')
        
        # Find the first row that has all three link types: _d, _h, _5
        print("🕵️  Scanning for the topmost row with _d, _h, _5 links...")
        
        # Pattern to match links like: href='db/d/?d=20260119&t=d'>0119_d
        pattern = r'href=["\']?([^"\'>]*[?&]t=[dh5])["\']?[^>]*>([^<]*)'
        
        required = ["_d", "_h", "_5"]
        
        for row in rows:
            row_links = re.findall(pattern, row)
            matches = {suffix: None for suffix in required}
            
            for href, text in row_links:
                for suffix in required:
                    if text.endswith(suffix):
                        matches[suffix] = (href, text)
            
            # If we found all three types in this row, use it
            if all(matches.values()):
                print(f"✅ Found topmost row with all link types")
                
                # Extract date from the first link text (e.g., "0119_d" -> "0119")
                first_text = matches["_d"][1]
                mmdd = first_text.replace("_d", "")
                
                # Determine year
                now = datetime.datetime.now()
                month = int(mmdd[:2])
                
                # If we're in January and see December data, use previous year
                if now.month == 1 and month == 12:
                    year = now.year - 1
                else:
                    year = now.year
                
                yyyymmdd = f"{year}{mmdd}"
                print(f"📅 Date: {yyyymmdd}")
                
                target_links = []
                for suffix in required:
                    href, text = matches[suffix]
                    
                    # Build full URL
                    href = href.lstrip('/')
                    if href.startswith("http"):
                        url = href
                    elif "db/" in href:
                        url = f"https://stooq.com/{href}"
                    else:
                        url = f"https://stooq.com/db/{href}"
                    
                    # Build filename: YYYYMMDD_suffix.txt
                    final_name = f"{yyyymmdd}{suffix}.txt"
                    target_links.append((url, final_name))
                
                print(f"🎯 Selected targets: {[t[1] for t in target_links]}")
                return target_links
        
        print("⚠️  Could not find a row with all three link types (_d, _h, _5).")
        return None
        
    except Exception as e:
        print(f"❌ Error while searching for links: {e}")
    return None
