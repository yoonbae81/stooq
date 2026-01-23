
def configure_stooq_settings(page):
    """
    Robustly configures Stooq settings for all 3 data frequencies (Daily, Hourly, 5-Min).
    Discovered via browser investigation:
    - Main categories use IDs like d_1, d_3.
    - Sub-items use NAMES like d1_1, d3_X.
    - Prefix '5' implies name starts with '51' or '53'.
    """
    max_total_attempts = 10
    for attempt in range(1, max_total_attempts + 1):
        try:
            print(f"   🔄 Configuration Attempt {attempt}/{max_total_attempts}...")
            
            # 1. Navigation / Reload
            # On first attempt, only navigate if not already there. 
            # On subsequent attempts, force reload.
            if "stooq.com/db" not in page.url or attempt > 1:
                 print("   🌐 Navigating/Reloading Stooq DB...")
                 page.goto("https://stooq.com/db/", timeout=90000, wait_until="domcontentloaded")
                 
            # 2. Open Panel
            print("   ⚙️  Opening Settings Panel...")
            settings_link = page.locator("a:has-text('Setting Files Content')").first
            # Ensure it's attached and visible
            settings_link.wait_for(state="visible", timeout=15000)
            settings_link.click()
            
            # Wait for the panel to be active (the #bs button appearing)
            page.wait_for_selector("#bs", timeout=15000)
            
            # 3. Clean and Configure via JS
            print("   🚀 Applying World/Indices and U.S. All configuration...")
            page.evaluate("""
                (function() {
                    const prefixes = ['d', 'h', '5'];
                    // Clear EVERYTHING first
                    document.querySelectorAll('input[type="checkbox"]').forEach(cb => { cb.checked = false; });
                    
                    prefixes.forEach(p => {
                        // Check Main Categories (UI state)
                        const worldMain = document.getElementById(p + '_1');
                        if (worldMain) worldMain.checked = true;
                        const usMain = document.getElementById(p + '_3');
                        if (usMain) usMain.checked = true;
                        
                        // Check World Indices
                        const worldIndicesName = (p === '5' ? '51' : (p + '1')) + '_1';
                        const worldIndices = document.querySelector(`input[name="${worldIndicesName}"]`);
                        if (worldIndices) worldIndices.checked = true;
                        
                        // Check ALL U.S. markets
                        const usGroupPrefix = (p === '5' ? '53' : (p + '3')) + '_';
                        document.querySelectorAll(`input[name^="${usGroupPrefix}"]`).forEach(el => {
                            el.checked = true;
                        });
                    });
                })();
            """)
            
            # 4. Save and Verify
            print("   💾 Saving configuration...")
            save_button = page.locator("#bs").first
            save_button.click(timeout=10000)
            
            try:
                # Wait for "Done!" confirmation
                # Stooq changes the 'value' of the input element to 'Done!'
                page.wait_for_function(
                    "document.getElementById('bs') && document.getElementById('bs').value.includes('Done')", 
                    timeout=15000
                )
                print("   ✅ Configuration saved successfully (Done! detected).")
                return True
            except Exception:
                if attempt < max_total_attempts:
                    print(f"   ⚠️  'Done!' not detected. Waiting 10s before Reload & Retry...")
                    page.wait_for_timeout(10000)
                    continue
                else:
                    print(f"   ❌ Final attempt failed. 'Done!' never detected.")
                    return False

        except Exception as e:
            print(f"   ⚠️  Error during attempt {attempt}: {e}")
            if attempt < max_total_attempts:
                print("   Waiting 10s before retry...")
                page.wait_for_timeout(10000)
            else:
                print(f"   ❌ Configuration failed after {max_total_attempts} attempts.")
                return False

    return False
