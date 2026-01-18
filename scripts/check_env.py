#!/usr/bin/env python3
"""
Stooq Downloader Environment Check Script (Playwright version)
"""

import os
import sys
import subprocess
from datetime import datetime

def print_result(msg, success=True):
    prefix = "  ✅" if success else "  ❌"
    print(f"{prefix} {msg}")

def check_env():
    print("="*60)
    print(f"🔍 Stooq Downloader Health Check ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    print("="*60)
    
    all_passed = True
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. Required Libraries
    print("\n📦 [1/4] Checking Required Libraries")
    required_libs = ['PIL', 'numpy', 'scipy', 'playwright', 'requests']
    for lib in required_libs:
        try:
            if lib == 'PIL': import PIL
            elif lib == 'numpy': import numpy
            elif lib == 'scipy': import scipy
            elif lib == 'playwright': import playwright
            elif lib == 'requests': import requests
            print_result(f"{lib} found")
        except ImportError:
            print_result(f"{lib} NOT found (run: pip install -r requirements.txt)", False)
            all_passed = False

    # 2. Playwright Browser Engines
    print("\n🌐 [2/4] Checking Playwright Browsers")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
                browser.close()
                print_result("Chromium engine found")
            except Exception as e:
                print_result(f"Chromium engine fail to load ({e})", False)
                print("     (Run: playwright install chromium)")
                all_passed = False
    except ImportError:
        print_result("playwright library not loaded", False)
        all_passed = False

    # 3. Template Database
    print("\n💾 [3/4] Checking Template Database")
    pkl_path = os.path.join(project_root, 'captcha', 'model.pkl')
    if os.path.exists(pkl_path):
        size = os.path.getsize(pkl_path)
        print_result(f"model.pkl found ({size:,} bytes)")
    else:
        print_result("captcha/model.pkl NOT found.", False)
        print("     (Run: scripts/captcha/build_templates.py)")
        all_passed = False

    # 4. Data Directory Permissions
    print("\n📂 [4/4] Checking Data Directory Permissions")
    target_path = os.path.join(project_root, 'data')
    try:
        os.makedirs(target_path, exist_ok=True)
        test_file = os.path.join(target_path, '.env_check')
        with open(test_file, 'w') as f: f.write('ok')
        os.remove(test_file)
        print_result(f"Write permission verified: {target_path}")
    except Exception as e:
        print_result(f"Cannot use directory: {target_path} ({type(e).__name__})", False)
        all_passed = False

    print("\n" + "="*60)
    if all_passed:
        print("✨ All checks passed!")
    else:
        print("❌ Some requirements are missing. Check the solutions above.")
    print("="*60)
    return all_passed

if __name__ == "__main__":
    sys.exit(0 if check_env() else 1)
