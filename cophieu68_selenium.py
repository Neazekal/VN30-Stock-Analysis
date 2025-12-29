import time
import os
import csv
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# List of VN30 stocks
VN30_STOCKS = [
    "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG", 
    "MBB", "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSB", "SSI", "STB", 
    "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE"
]
# VN30_STOCKS = ["BCM"]

def check_and_close_ad(driver):
    """
    Checks for Google Vignette or other common ads and closes them.
    This should be called before every interaction that might be blocked.
    """
    try:
        # Common Google Vignette close button selectors
        ad_close_selectors = [
            (By.ID, "dismiss-button"),
            (By.CSS_SELECTOR, "div[aria-label='Close ad']"),
            (By.CSS_SELECTOR, ".close-popup-icon-x"), # Custom popup
            (By.ID, "cboxClose"), # Colorbox
            (By.XPATH, "//div[contains(@class, 'ad-close') or contains(@id, 'ad-close')]") 
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
                # specific check for google ads iframe to avoid checking every iframe
                if "aswift" in iframe.get_attribute("id") or "google_ads" in iframe.get_attribute("id"):
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
        # print(f"Error checking for ads: {e}")
        # Ensure we are back to default content
        driver.switch_to.default_content()

def crawl_stock(driver, wait, symbol):
    print(f"\n--- Processing {symbol} ---")
    try:
        # 1. Search for Stock
        check_and_close_ad(driver)
        print(f"Searching for {symbol}...")
        
        # Ensure we are on a page with search bar, if not, go to home
        try:
             driver.find_element(By.ID, "id")
        except:
             driver.get("https://www.cophieu68.vn/index.php")
             
        search_input = wait.until(EC.visibility_of_element_located((By.ID, "id")))
        search_input.clear()
        search_input.send_keys(symbol)
        search_input.send_keys(Keys.ENTER)
        
        # 2. Wait for summary page
        print("Waiting for summary page...")
        wait.until(EC.url_contains(f"id={symbol}"))
        time.sleep(1)
        
        # 3. Click 'Lịch sự kiện'
        check_and_close_ad(driver)
        print("Clicking 'Lich su kien'...")
        # Selector from analysis: a[href*="quote/event.php?id=acb"]
        # Use generic selector with symbol
        event_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"a[href*='quote/event.php?id={symbol.lower()}']")))
        driver.execute_script("arguments[0].click();", event_link)
        
        # Check for ad that appears AFTER click (Interstitial)
        time.sleep(2)
        check_and_close_ad(driver)
        
        # 4. Wait for Event page
        print("Waiting for Event page...")
        wait.until(EC.url_contains("event.php"))
        time.sleep(1)
        
        # 5. Click 'Công thức tính khối lượng'
        check_and_close_ad(driver)
        print("Clicking 'Cong thuc tinh khoi luong'...")
        # Selector from analysis: a[href*="event_calc_volume.php?id=acb"]
        calc_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"a[href*='event_calc_volume.php']")))
        driver.execute_script("arguments[0].click();", calc_link)
        
        # Check for ad post-click
        time.sleep(2)
        check_and_close_ad(driver)
        
        # 6. Verify Final Page
        print("Waiting for Volume Formula page...")
        wait.until(EC.url_contains("event_calc_volume.php"))
        print("Successfully reached 'Cong thuc tinh khoi luong' page!")
        
        # 7. Data Extraction via JS
        print(f"[{symbol}] Extracting data via JS...")
        try:
            check_and_close_ad(driver)
            
            # Use JS to extract data directly
            # Use JS to find table by content and extract
            script = """
            var debug = [];
            var tables = document.querySelectorAll('table');
            var targetTable = null;
            
            // 1. Find the correct table
            var candidates = [];
            for (var i = 0; i < tables.length; i++) {
                var txt = tables[i].innerText;
                if (txt.includes('Ngày bổ sung') && (txt.includes('Cổ phiếu Lưu Hành') || txt.includes('Khối lượng'))) {
                    candidates.push(tables[i]);
                    debug.push("Candidate table at index " + i + " with " + tables[i].rows.length + " rows.");
                }
            }
            
            // Pick candidate with most rows
            if (candidates.length > 0) {
                targetTable = candidates[0];
                for (var i = 1; i < candidates.length; i++) {
                    if (candidates[i].rows.length > targetTable.rows.length) {
                        targetTable = candidates[i];
                    }
                }
                debug.push("Selected table with " + targetTable.rows.length + " rows.");
            }
            
            if (!targetTable) {
                // Fallback: Look for the specific ID if text search fails 
                targetTable = document.getElementById('calc_volume');
                if (targetTable) debug.push("Found table by ID 'calc_volume' fallback.");
                else {
                    targetTable = document.getElementById('table_anchor_calc_volume');
                    if (targetTable) debug.push("Found table by ID 'table_anchor_calc_volume' fallback.");
                    
                    // If target table has only 1 row (header), try to find its sibling 'calc_volume'
                    if (targetTable && targetTable.rows.length <= 1) {
                         var sibling = document.getElementById('calc_volume');
                         if (sibling) {
                             targetTable = sibling;
                             debug.push("Switched to 'calc_volume' sibling with " + sibling.rows.length + " rows.");
                         }
                    }
                }
            }
            
            if (!targetTable) {
                var allTableText = [];
                for(var j=0; j<Math.min(tables.length, 3); j++) {
                    allTableText.push("Table " + j + ": " + tables[j].innerText.substring(0, 100).replace(/\\n/g, " "));
                }
                debug.push("Tables Found: " + tables.length);
                if (tables.length > 0) debug.push("Sample Content: " + allTableText.join(" | "));
                return {error: "Table not found", debug: debug};
            }
            
            var rows = targetTable.rows;
            var data = [];
            var colIndex = -1;
            
            // 2. Find the target column index
            // Scan first few rows for header
            for (var r = 0; r < Math.min(rows.length, 5); r++) {
                var cells = rows[r].cells;
                for (var c = 0; c < cells.length; c++) {
                    if (cells[c].innerText.includes('Ngày bổ sung')) {
                        colIndex = c;
                        break;
                    }
                }
                if (colIndex !== -1) break;
            }
            
            if (colIndex === -1) {
                 // Fallback: use 6th index (7th column) if text search fails
                 colIndex = 6;
                 debug.push("Column header not found, using default index 6");
            } else {
                 debug.push("Found column header at index " + colIndex);
            }
            
            debug.push("Total Rows: " + rows.length);
            
            // 3. Extract data
            var sampleCells = [];
            for (var i = 0; i < rows.length; i++) {
                var cells = rows[i].cells;
                if (cells.length > colIndex) {
                    var cell = cells[colIndex];
                    var html = cell.innerHTML;
                    
                    if (data.length < 3) {
                         sampleCells.push("Row " + i + ": " + html.substring(0, 50).replace(/\\n/g, " "));
                    }
                    
                    if (html.includes('<br>')) {
                         var parts = html.split('<br>');
                         if (parts.length >= 2) {
                             var date = parts[0].replace(/<[^>]+>/g, '').trim();
                             // skip if it's the header row itself
                             if (date.includes('Ngày bổ sung')) continue;
                             
                             var volRaw = parts[1];
                             var volClean = volRaw.replace(/<[^>]+>/g, '').trim();
                             // Remove commas for clean data
                             data.push({'Ngay bo sung': date, 'Co phieu luu hanh': volClean});
                         }
                    }
                }
            }
            
            if (data.length === 0) {
                 debug.push("Extraction Content Samples: " + sampleCells.join(" | "));
            }
            
            return {data: data, debug: debug};
            """
            
            # Retry loop for extraction (handle slow loading rows)
            debug_info = []
            for attempt in range(3):
                result = driver.execute_script(script)
                extracted_data = result.get('data', [])
                debug_info = result.get('debug', [])
                
                if extracted_data:
                    break
                time.sleep(2)

            print(f"[{symbol}] Extracted {len(extracted_data)} records.")
            
            # 8. Fallback: Single Listing Check (e.g., BCM)
            if not extracted_data:
                 print(f"[{symbol}] No table data. Checking for single listing info...")
                 script_single = """
                 var body = document.body.innerText;
                 var dateRegex = /Ngày niêm yết:\\s*(\\d{2}\\/\\d{2}\\/\\d{4})/;
                 var volRegex = /Khối lượng niêm yết lần đầu:\\s*([0-9,]+)/;
                 
                 var dateMatch = body.match(dateRegex);
                 var volMatch = body.match(volRegex);
                 
                 if (dateMatch && volMatch) {
                     return [{
                         'Ngay bo sung': dateMatch[1],
                         'Co phieu luu hanh': volMatch[1]
                     }];
                 }
                 return [];
                 """
                 extracted_data = driver.execute_script(script_single)
                 if extracted_data:
                     print(f"[{symbol}] Found single listing info: {extracted_data}")
            
            if extracted_data:
                # Save data
                os.makedirs("data/Shares_Outstanding", exist_ok=True)
                filename = f"data/Shares_Outstanding/{symbol}.csv"
                with open(filename, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=["Ngay bo sung", "Co phieu luu hanh"])
                    writer.writeheader()
                    writer.writerows(extracted_data)
                print(f"Data saved to {filename}")
            else:
                print(f"No data found for {symbol}")
                # Optional: print debug info only on failure
                # print(f"[{symbol}] Debug info: {debug_info}")

        except Exception as ex:
             print(f"Extraction error for {symbol}: {ex}")

    except Exception as e:
        print(f"Error processing {symbol}: {e}")
        # traceback.print_exc()

def run_automation():
    driver = webdriver.Chrome()
    driver.maximize_window()
    wait = WebDriverWait(driver, 10)
    
    try:
        # Initial Navigation
        print("Navigating to https://www.cophieu68.vn/index.php ...")
        driver.get("https://www.cophieu68.vn/index.php")
        time.sleep(2) 
        
        for stock in VN30_STOCKS:
            crawl_stock(driver, wait, stock)
            
    except Exception as e:
        import traceback
        print(f"Global Error: {e}")
        traceback.print_exc()
    finally:
        print("Closing driver in 5 seconds...")
        time.sleep(5)
        driver.quit()

if __name__ == "__main__":
    # Safe print for Windows console
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
    run_automation()
