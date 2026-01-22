
import os
import time

def start_download(session, download_url, filename, data_dir):
    """
    DEPRECATED: Use download_with_browser instead.
    """
    pass

def download_with_browser(page, download_url, filename, data_dir):
    """
    Download file using the authenticated Playwright page.
    Uses the server-suggested filename as requested by the user.
    """
    print(f"🚀 Starting Browser Download: {filename}")
    
    # Small delay to avoid rapid-fire triggers
    time.sleep(2)
    
    try:
        # Set Referer to satisfy Stooq verification
        referer = "https://stooq.com/db/"
        
        # Use expect_download context
        with page.expect_download(timeout=60000) as download_info:
            try:
                # Use headers if possible, but page.goto only supports limited options
                # The most reliable way to set referer in Playwright is via the context or page.goto options
                page.goto(download_url, timeout=30000, referer=referer)
            except Exception as e:
                # Navigation might fail if it's a "download-only" response
                pass

        download = download_info.value
        suggested_name = download.suggested_filename
        save_path = os.path.join(data_dir, suggested_name)
        
        print(f"   ⬇️  Download started... ({suggested_name})")
        
        download.save_as(save_path)
        print(f"✅ Download complete: {save_path}")
        
        # Quick Check for HTML error content
        if os.path.exists(save_path):
            with open(save_path, 'rb') as f:
                header = f.read(100)
                if b"<!DOCTYPE" in header or b"<html" in header:
                     print("❌ Downloaded file appears to be HTML (Auth Error?).")
                     return None
        return suggested_name # Return the actual filename saved

    except Exception as e:
        print(f"❌ Browser download failed: {e}")
        return None

def clean_downloaded_data(data_dir):
    """
    Placeholder for future cleanup logic if needed. 
    Listing logs removed per user request.
    """
    pass
