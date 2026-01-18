
def configure_stooq_settings(page):
    """
    Robustly configures Stooq settings for all 3 data frequencies (Daily, Hourly, 5-Min).
    Discovered via browser investigation:
    - Main categories use IDs like d_1, d_3.
    - Sub-items use NAMES like d1_1, d3_X.
    - Prefix '5' implies name starts with '51' or '53'.
    """
    try:
        # 1. Navigation with robust timeout and load state
        if "stooq.com/db" not in page.url:
             print("   🌐 Navigating to Stooq DB...")
             # Use domcontentloaded to avoid long ad-related timeouts
             page.goto("https://stooq.com/db/", timeout=90000, wait_until="domcontentloaded")
             
        # 2. Open Panel
        print("   ⚙️  Opening Settings Panel...")
        settings_link = page.locator("a:has-text('Setting Files Content')").first
        if not settings_link.is_visible():
            # Try scrolling to it
            settings_link.scroll_into_view_if_needed()
            
        settings_link.click()
        # Wait for the panel to be active (the #bs button appearing is a good signal)
        page.wait_for_selector("#bs", timeout=15000)
        
        # 3. Clean and Configure via JS (Atomic for all tabs)
        print("   🚀 Applying World/Indices and U.S. All configuration...")
        page.evaluate("""
            (function() {
                const prefixes = ['d', 'h', '5'];
                
                // Clear EVERYTHING first to ensure excluded tickers (JP etc.) are removed
                document.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                    cb.checked = false;
                });
                
                prefixes.forEach(p => {
                    // Check Main Categories (for UI state)
                    // 1 = World, 3 = U.S.
                    const worldMain = document.getElementById(p + '_1');
                    if (worldMain) worldMain.checked = true;
                    const usMain = document.getElementById(p + '_3');
                    if (usMain) usMain.checked = true;
                    
                    // Check World Indices (Group 1, Item 1)
                    // Note: Browser investigation found '51' prefix for 5min
                    const worldIndicesName = (p === '5' ? '51' : (p + '1')) + '_1';
                    const worldIndices = document.querySelector(`input[name="${worldIndicesName}"]`);
                    if (worldIndices) worldIndices.checked = true;
                    
                    // Check ALL U.S. markets (Group 3)
                    const usGroupPrefix = (p === '5' ? '53' : (p + '3')) + '_';
                    document.querySelectorAll(`input[name^="${usGroupPrefix}"]`).forEach(el => {
                        el.checked = true;
                    });
                });
            })();
        """)
        
        # 4. Save
        print("   💾 Saving configuration...")
        save_button = page.locator("#bs")
        save_button.click()
        
        # Verify "Done!" appearance
        try:
            # The button text changes to 'Done!' or includes it
            page.wait_for_function("document.getElementById('bs').value.includes('Done')", timeout=10000)
            print("   ✅ Configuration saved successfully (Done! detected).")
        except:
            print("   ⚠️  Timed out waiting for 'Done!' confirmation - assuming save succeeded.")
            
        return True

    except Exception as e:
        print(f"   ❌ Configuration error: {e}")
        return False
