import time
import io
import re
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# List of VN30 stocks (You can update this list)
VN30_STOCKS = [
    "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG", 
    "MBB", "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSB", "SSI", "STB", 
    "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE"
]

def extract_and_clean_table(driver, xpath, name):
    """Extracts and cleans a financial table from the current page."""
    print(f"Attempting to extract {name}...")
    try:
        element = driver.find_element(By.XPATH, xpath)
        html = element.get_attribute('outerHTML')
        df = pd.read_html(io.StringIO(html))[0]
        
        # Clean columns
        new_columns = []
        for col in df.columns:
            col_str = str(col) if not isinstance(col, tuple) else '_'.join(map(str, col))
            match = re.search(r"(Q[1-4]/\d{4})", col_str)
            if match:
                new_columns.append(match.group(1))
            else:
                if "Indicator" in col_str or name in col_str or "Net revenue" in col_str or "Current assets" in col_str or "Total assets" in col_str: 
                    if col_str == df.columns[0] or "Indicator" in col_str: 
                        new_columns.append("Indicator")
                    else:
                        new_columns.append(col_str)
                else:
                    new_columns.append(col_str)
        
        if "Indicator" not in new_columns and len(new_columns) > 0:
             new_columns[0] = "Indicator"
             
        df.columns = new_columns
        return df
    except Exception as e:
        print(f"Failed to extract {name}: {e}")
        return None

def crawl_stock_data(driver, symbol):
    """Crawls financial data for the current stock page."""
    print(f"Starting crawl for {symbol}...")
    
    income_xpath = "/html/body/div[4]/div[15]/div/div[5]/div[3]/div[2]/div/div[4]/div/div/div[2]/div/table"
    balance_xpath = "/html/body/div[4]/div[15]/div/div[5]/div[3]/div[2]/div/div[4]/div/div/div[2]/div[2]/table"
    # Fallback XPaths or more robust finders could be added here
    
    all_frames = []
    
    # Try to find the previous button to ensure we are on a page that allows paging
    # or just start extracting
    
    for i in range(6):
        print(f"--- Processing Page {i+1} for {symbol} ---")
        
        # Extract data
        income_df = extract_and_clean_table(driver, income_xpath, "Income Statement")
        balance_df = extract_and_clean_table(driver, balance_xpath, "Balance Sheet")
        
        current_page_frames = []
        if income_df is not None:
            current_page_frames.append(income_df)
        if balance_df is not None:
            current_page_frames.append(balance_df)
            
        if current_page_frames:
            page_df = pd.concat(current_page_frames, ignore_index=True)
            all_frames.append(page_df)
        
        # Click Previous Button
        if i < 5:
            try:
                # Need to re-find the previous button on each page
                # Generic robust selector for the 'Previous' pagination button
                prev_btns = driver.find_elements(By.XPATH, "//i[contains(@class, 'fa-chevron-left')]/parent::div | //i[contains(@class, 'fa-angle-left')]/parent::div | //div[contains(@class, 'btn-previous')]")
                
                # Filter for visible one
                prev_btn = None
                for btn in prev_btns:
                    if btn.is_displayed():
                        prev_btn = btn
                        break
                
                if not prev_btn:
                     # Specific XPath fallback from original script
                     prev_btn = driver.find_element(By.XPATH, "/html/body/div[4]/div[15]/div/div[5]/div[3]/div[2]/div/div[4]/div/div/div/div[2]/div[2]")

                driver.execute_script("arguments[0].scrollIntoView(true);", prev_btn)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", prev_btn)
                
                print("Clicked Previous, waiting for reload...")
                time.sleep(3) 

            except Exception as e:
                print(f"Could not click Previous button on page {i+1}: {e}")
                break

    if all_frames:
        final_df = all_frames[0]
        for df in all_frames[1:]:
            try:
                final_df = pd.merge(final_df, df, on='Indicator', how='outer')
            except Exception as merge_error:
                print(f"Error merging frames: {merge_error}")
        
        # Sort Columns
        cols = final_df.columns.tolist()
        valid_quarter_cols = []
        other_cols = []
        
        for c in cols:
            match = re.search(r"Q([1-4])/(\d{4})", str(c))
            if match:
                q = int(match.group(1))
                y = int(match.group(2))
                if y > 2020 or (y == 2020 and q >= 1):
                    valid_quarter_cols.append(c)
            else:
                other_cols.append(c)
        
        def sort_key(col_name):
            match = re.search(r"Q([1-4])/(\d{4})", col_name)
            if match:
                return int(match.group(2)), int(match.group(1))
            return 0, 0
        
        valid_quarter_cols.sort(key=sort_key)
        final_df = final_df[other_cols + valid_quarter_cols]
        
        # Save
        os.makedirs('data/finance', exist_ok=True)
        output_path = f"data/finance/{symbol}.csv"
        final_df.to_csv(output_path, index=False)
        print(f"Saved data for {symbol} to {output_path}")
    else:
        print(f"No data extracted for {symbol}.")

def handle_login_popup(driver):
    try:
        # Check specific login form container
        login_form = WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.ID, "login-form"))
        )
        print("Login form detected. Attempting to close...")
        
        # Find close button
        close_btn = login_form.find_element(By.CSS_SELECTOR, ".close-popup-icon-x")
        close_btn.click()
        
        # Wait for invisibility
        WebDriverWait(driver, 3).until(
            EC.invisibility_of_element_located((By.ID, "login-form"))
        )
        print("Login popup closed.")
    except Exception:
        # Fallback JS
        try:
             driver.execute_script("$('#login-form').modal('hide');")
        except:
             pass
        # print(f"Popup check finished: {e}") 
        # Suppress noise if no popup

def run_crawler():
    driver = webdriver.Chrome()
    try:
        driver.get("https://finance.vietstock.vn/?languageid=2")
        driver.maximize_window()
        wait = WebDriverWait(driver, 10)
        
        handle_login_popup(driver)
        
        # Loop through stocks
        # For testing, we can limit the list, or run all. 
        # Using full VN30 list as requested.
        for stock in VN30_STOCKS:
            try:
                print(f"\n================ processing {stock} ================")
                
                # Check search input visibility or open it
                try:
                     search_input = driver.find_element(By.ID, "popup-search-txt")
                     if not search_input.is_displayed():
                         raise Exception("Input hidden")
                except:
                     search_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-mobile-search")))
                     search_btn.click()
                     search_input = wait.until(EC.visibility_of_element_located((By.ID, "popup-search-txt")))
                
                search_input.clear()
                search_input.send_keys(stock)
                
                print("Waiting 3 seconds for search results...")
                time.sleep(3)
                
                # Find result
                stock_list = wait.until(EC.visibility_of_element_located((By.ID, "list-stock-search")))
                first_result = stock_list.find_element(By.TAG_NAME, "a")
                
                # Open in new tab
                actions = ActionChains(driver)
                actions.key_down(Keys.CONTROL).click(first_result).key_up(Keys.CONTROL).perform()
                
                wait.until(lambda d: len(d.window_handles) > 1)
                driver.switch_to.window(driver.window_handles[-1])
                print(f"Opened tab for {stock}")
                
                # Wait for load - check for Financials (Tai chinh) section or just title
                try:
                    # Wait for title to ensure page load
                    wait.until(EC.title_contains(stock))
                    # Wait a bit more for dynamic content
                    time.sleep(3) 
                    
                    # === CRAWL DATA ===
                    crawl_stock_data(driver, stock)
                    # ==================
                    
                except Exception as e:
                    print(f"Error processing {stock} page: {e}")
                
                # Close tab and return
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                time.sleep(1)
                
            except Exception as e:
                print(f"Error in search loop for {stock}: {e}")
                # Ensure we are on main tab
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

    except Exception as e:
        print(f"Global Crawler Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_crawler()
