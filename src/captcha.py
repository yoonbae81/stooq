#!/usr/bin/env python3
"""
CAPTCHA Recognition Engine - Fully Automated Version
"""

import os
import time
import pickle
import numpy as np
from PIL import Image
import scipy.ndimage as nd
from collections import defaultdict
import re

try:
    from src.session_manager import save_session
except ImportError:
    from session_manager import save_session

class CaptchaTemplateDB:
    def __init__(self):
        self.templates = defaultdict(list)

class CaptchaRecognizer:
    def __init__(self, template_db):
        self.db = template_db

    def _extract_red_mask(self, img):
        data = np.array(img)
        r, g, b = data[:,:,0], data[:,:,1], data[:,:,2]
        mask = (r > 100) & (g < 140) & (b < 140)
        cleaned = nd.median_filter(mask, size=3)
        return cleaned

    def _extract_characters(self, mask):
        labels, num = nd.label(mask)
        if num == 0: return []
        objs = nd.find_objects(labels)
        valid_chars = []
        for i, obj in enumerate(objs):
            h, w = mask[obj].shape
            if h > 5 and w > 2:
                char_mask = (labels[obj] == (i + 1))
                char_arr = char_mask.astype(np.uint8)
                valid_chars.append((obj[1].start, char_arr))
        valid_chars.sort(key=lambda x: x[0])
        return [char for _, char in valid_chars]

    def _normalize_char(self, char_arr):
        rows = np.any(char_arr, axis=1)
        cols = np.any(char_arr, axis=0)
        if not rows.any() or not cols.any(): return None
        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]
        cropped = char_arr[rmin:rmax+1, cmin:cmax+1]
        target_size = 40
        h, w = cropped.shape
        img = Image.fromarray((cropped * 255).astype(np.uint8))
        scale = min(target_size / h, target_size / w)
        new_h, new_w = int(h * scale), int(w * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        result = np.zeros((target_size, target_size), dtype=np.uint8)
        y_offset = (target_size - new_h) // 2
        x_offset = (target_size - new_w) // 2
        result[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = np.array(img) > 128
        return result

    def recognize_char(self, char_arr):
        normalized = self._normalize_char(char_arr)
        if normalized is None: return "?"
        best_char, max_score = "?", -1
        for char, templates in self.db.templates.items():
            for template in templates:
                intersection = np.sum(normalized & template)
                union = np.sum(normalized | template)
                score = (intersection / union) if union > 0 else 0
                if score > max_score:
                    max_score, best_char = score, char
        return best_char

    def recognize(self, image_path):
        img = Image.open(image_path).convert('RGB')
        mask = self._extract_red_mask(img)
        chars = self._extract_characters(mask)
        result = ""
        for char_arr in chars:
            result += self.recognize_char(char_arr)
        return result

_recognizer = None

def load_recognizer(template_file=None):
    if template_file is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        template_file = os.path.join(project_root, 'captcha', 'model.pkl')
    if not os.path.exists(template_file):
        raise FileNotFoundError(f"Template DB not found: {template_file}")
    with open(template_file, 'rb') as f:
        template_db = pickle.load(f)
    return CaptchaRecognizer(template_db)

def get_recognizer():
    global _recognizer
    if _recognizer is None:
        _recognizer = load_recognizer()
    return _recognizer

def solve_text_from_image(image_path):
    return get_recognizer().recognize(image_path)

def solve_stooq_captcha(page, max_retries=10):
    """
    Session Authorization Logic (re-uses existing Page/Context)
    """
    print("🔐 Triggering CAPTCHA...")
    
    # 1. Page Load
    if "stooq.com/db" not in page.url:
        page.goto("https://stooq.com/db/", timeout=60000)
    
    page.wait_for_load_state("domcontentloaded")
    
    # Reset/Reload to clear old state - use domcontentloaded to avoid ad-related timeouts
    page.reload(wait_until="domcontentloaded", timeout=60000) 
    page.wait_for_timeout(2000)

    captcha_solved = False
    for c_attempt in range(max_retries):
        print(f"   🎟️  CAPTCHA Attempt {c_attempt + 1}/{max_retries}...")
        
        downloads = []
        def on_download(download):
                downloads.append(download)
        
        listener_added = False
        try:
            page.on("download", on_download)
            listener_added = True
            
            # Find download link
            download_link = page.locator("a").filter(has_text="_d").first
            if not download_link.is_visible():
                download_link = page.locator("xpath=//a[contains(@href, 't=d')]").first
            
            # Click and wait for response OR download
            try:
                # Small retry for the click itself if page state is unstable
                click_success = False
                for click_attempt in range(2):
                    try:
                        with page.expect_response(lambda r: "/q/l/s/i/" in r.url, timeout=5000) as resp:
                            download_link.click(timeout=5000)
                        click_success = True
                        break
                    except:
                        if downloads: # If download started, we are authorized
                            click_success = True
                            break
                        page.wait_for_timeout(1000)
                
                if not click_success and not downloads:
                    raise Exception("Could not trigger CAPTCHA or Download after click retries.")

                if not downloads:
                    # If we get here, we got an image response -> CAPTCHA needed
                    temp_captcha = "tmp/current_captcha.png"
                    os.makedirs("tmp", exist_ok=True)
                    with open(temp_captcha, 'wb') as f:
                        f.write(resp.value.body())
                    
                    solution = solve_text_from_image(temp_captcha)
                    print(f"      🧠 Auto-solver: {solution}")
                    
                    # Fill and submit
                    page.fill("#f15", "")
                    page.fill("#f15", solution)
                    page.keyboard.press("Enter")
                    
                    # Wait to see result
                    page.wait_for_timeout(3000)
                    
                    content = page.content()
                    if "Authorization successful!" in content:
                        print("      ✅ Authorization successful!")
                        page.reload(wait_until="domcontentloaded", timeout=60000)
                        page.wait_for_timeout(2000)
                        captcha_solved = True
                        break
                    elif "Incorrect code" in content or "f15" in content:
                        print("      ❌ Incorrect code or retry required. Retrying...")
                        continue
                    else:
                        if not page.locator("#f15").is_visible():
                                print("      ❓ Overlay gone, assuming success.")
                                captcha_solved = True
                                break
                else:
                    print("      ✅ Already authorized!")
                    downloads[0].cancel()
                    captcha_solved = True
                    break
                            
            except Exception as e:
                # Check for download (Already Authorized)
                if downloads:
                    print("      ✅ Download started. Already authorized!")
                    downloads[0].cancel()
                    captcha_solved = True
                    break
                    
                if "Timeout" in str(e):
                    print("         (Timeout waiting for CAPTCHA response)")
                else:
                    print(f"      ⚠️  Error during inner CAPTCHA step: {e}")
                
                page.reload(wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(2000)

        finally:
            if listener_added:
                page.remove_listener("download", on_download)

        if captcha_solved:
             break

    return captcha_solved
