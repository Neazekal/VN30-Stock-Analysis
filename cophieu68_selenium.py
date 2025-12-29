import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def check_and_close_ad(driver):
    """
    Checks for Google Vignette or other common ads and closes them.
    This should be called before every interaction that might be blocked.
    """
    try:
        # Check for Google Vignette (ins or iframe)
        # Usually it's an iframe with id starting with 'aswift' or similar, 
        # but the close button is often in a specific container outside or inside.
        # We look for the common 'Dismiss' or 'Close' button for Google ads.
        
        # This is a generic check for the "Dismiss" button often seen in these vignettes
        # Selector observed in analysis: #dismiss-button or div[aria-label='Close ad'] or similar
        # Based on previous analysis: PageID 2647194A0D47C2E04BECA4AC968E88D4 step 20 used 'click_browser_pixel'
        # so we might need a robust finder.
        
        # Common Google Vignette close button selectors
        ad_close_selectors = [
            (By.ID, "dismiss-button"),
            (By.CSS_SELECTOR, "div[aria-label='Close ad']"),
            (By.CSS_SELECTOR, ".close-popup-icon-x"), # Custom popup
            (By.ID, "cboxClose"), # Colorbox
        ]
        
        for by, selector in ad_close_selectors:
            try:
                element = driver.find_element(by, selector)
                if element.is_displayed():
                    print("Ad detected. Closing...")
                    element.click()
                    time.sleep(1) # Wait for animation
                    return
            except:
                pass
            
        # Also check for iframes that might contain the ad
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            try:
                # Sometimes the close button is inside the iframe
                driver.switch_to.frame(iframe)
                for by, selector in ad_close_selectors:
                    try:
                        element = driver.find_element(by, selector)
                        if element.is_displayed():
                            print("Ad detected inside iframe. Closing...")
                            element.click()
                            driver.switch_to.default_content()
                            time.sleep(1)
                            return
                    except:
                        pass
                driver.switch_to.default_content()
            except:
                driver.switch_to.default_content()

    except Exception as e:
        print(f"Error checking for ads: {e}")
        # Ensure we are back to default content
        driver.switch_to.default_content()

def run_automation():
    driver = webdriver.Chrome()
    driver.maximize_window()
    wait = WebDriverWait(driver, 10)
    
    try:
        # 1. Navigation
        print("Navigating to https://www.cophieu68.vn/index.php ...")
        driver.get("https://www.cophieu68.vn/index.php")
        time.sleep(2) # Initial load
        
        # 2. Search for ACB
        check_and_close_ad(driver)
        print("Searching for ACB...")
        search_input = wait.until(EC.visibility_of_element_located((By.ID, "id"))) # Based on previous finding
        search_input.clear()
        search_input.send_keys("ACB")
        search_input.send_keys(Keys.ENTER)
        
        # 3. Wait for summary page
        print("Waiting for summary page...")
        wait.until(EC.url_contains("id=ACB"))
        time.sleep(2)
        
        # 4. Click 'Lịch sự kiện'
        check_and_close_ad(driver)
        print("Clicking 'Lich su kien'...")
        # Selector from analysis: a[href*="quote/event.php?id=acb"]
        event_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='quote/event.php?id=acb']")))
        # Use JS click to avoid element intercepted errors if ad overlay is partial
        driver.execute_script("arguments[0].click();", event_link)
        
        # Check for ad that appears AFTER click (Interstitial)
        time.sleep(2)
        check_and_close_ad(driver)
        
        # 5. Wait for Event page
        print("Waiting for Event page...")
        wait.until(EC.url_contains("event.php"))
        time.sleep(2)
        
        # 6. Click 'Công thức tính khối lượng'
        check_and_close_ad(driver)
        print("Clicking 'Cong thuc tinh khoi luong'...")
        # Selector from analysis: a[href*="event_calc_volume.php?id=acb"]
        calc_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='event_calc_volume.php']")))
        driver.execute_script("arguments[0].click();", calc_link)
        
        # Check for ad post-click
        time.sleep(2)
        check_and_close_ad(driver)
        
        # 7. Verify Final Page
        print("Waiting for Volume Formula page...")
        wait.until(EC.url_contains("event_calc_volume.php"))
        print("Successfully reached 'Cong thuc tinh khoi luong' page!")
        
        # 8. Data Extraction
        print("Extracting data via JS...")
        try:
            check_and_close_ad(driver)
            
            # Use JS to extract data directly with debug
            script = """
            var debug = {};
            var tables = document.querySelectorAll('table');
            debug.tableCount = tables.length;
            debug.tables = [];
            
            var targetTable = null;
            // distinct tables
            tables.forEach(function(t, idx) {
                var txt = t.innerText;
                var hasHeader = txt.includes('Ngày bổ sung') && txt.includes('Cổ phiếu Lưu Hành');
                debug.tables.push({index: idx, id: t.id, className: t.className, hasHeader: hasHeader, rowCount: t.rows.length});
                if (hasHeader) targetTable = t;
            });

            if (!targetTable) {
                return {error: "Table not found", debug: debug};
            }
            
            var rows = targetTable.rows;
            var data = [];
            
            // Find column index
            var colIndex = -1;
            
            // Search all rows for header
            for(var r=0; r<Math.min(rows.length, 5); r++) {
                var cells = rows[r].cells;
                for(var c=0; c<cells.length; c++) {
                    if(cells[c].innerText.includes('Ngày bổ sung')) {
                        colIndex = c;
                        break;
                    }
                }
                if(colIndex !== -1) break;
            }
            
            if (colIndex === -1) return {error: "Column not found", debug: debug};
            
            for (var i = 0; i < rows.length; i++) {
                var cells = rows[i].cells;
                if (cells.length > colIndex) {
                    var html = cells[colIndex].innerHTML;
                    if (html.includes('<br>')) {
                        var parts = html.split('<br>');
                        if (parts.length >= 2) {
                            var date = parts[0].trim();
                            // Skip header row if it matches textual header
                            if (date.includes('Ngày bổ sung')) continue;
                            
                            var volRaw = parts[1];
                            var volClean = volRaw.replace(/<[^>]+>/g, '').trim();
                            data.push({'Ngay bo sung': date, 'Co phieu luu hanh': volClean});
                        }
                    }
                }
            }
            return data;
            """
            
            extracted_data = driver.execute_script(script)
            
            if isinstance(extracted_data, dict) and 'error' in extracted_data:
                print("JS Extraction Error:", extracted_data['error'])
                print("Debug Info:", extracted_data.get('debug'))
                extracted_data = [] # Reset
            
            if not extracted_data:
                print("JS returned empty data even after robust search.")
                time.sleep(3)
                # One retry
                extracted_data = driver.execute_script(script)
                if isinstance(extracted_data, dict) and 'error' in extracted_data:
                     print("Retry JS Error:", extracted_data['error'])
                     extracted_data = []

            print(f"Extracted {len(extracted_data)} records.")
            
            for item in extracted_data:
                 pass # data is already in dict format

            
            # Print results
            # Safe print for Windows console
            import sys
            try:
                sys.stdout.reconfigure(encoding='utf-8')
            except:
                pass

            print("\nExtracted Data:")
            print(f"{'Ngay bo sung':<15} | {'Vol':<20}")
            print("-" * 40)
            for item in extracted_data:
                try:
                    print(f"{item['Ngay bo sung']:<15} | {item['Co phieu luu hanh']:<20}")
                except Exception:
                    # Fallback if reconfigure fails or console doesn't support it
                    print(f"{item['Ngay bo sung']:<15} | {str(item['Co phieu luu hanh']).encode('ascii', 'ignore').decode('ascii'):<20}")
                
            # Basic CSV save
            import csv
            with open("acb_volume_data.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["Ngay bo sung", "Co phieu luu hanh"])
                writer.writeheader()
                writer.writerows(extracted_data)
            print("Data saved to acb_volume_data.csv")
            
        except Exception as e:
            print(f"Error during extraction: {e}")
            import traceback
            traceback.print_exc()

        # Screenshot for verification
        time.sleep(3)
        driver.save_screenshot("cophieu68_success.png")
        print("Screenshot saved to cophieu68_success.png")

    except Exception as e:
        import traceback
        print(f"An error occurred: {e}")
        traceback.print_exc()
        driver.save_screenshot("cophieu68_error.png")
    finally:
        print("Closing driver in 5 seconds...")
        time.sleep(5)
        driver.quit()

if __name__ == "__main__":
    run_automation()
