import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import io
import re

def setup_driver():
    """Sets up the Selenium WebDriver."""
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # Use existing profile if needed, or just clean session
    driver = webdriver.Chrome(options=options)
    return driver

def extract_and_clean_table(driver, xpath, name):
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
                     # Heuristic to name the first column 'Indicator' if it looks like the label column
                     # But pandas usually puts the header name there.
                     # Let's just default first col to 'Indicator' if it's not a quarter?
                     # Or trust the regex rejection
                    if col_str == df.columns[0] or "Indicator" in col_str: 
                        new_columns.append("Indicator")
                    else:
                        new_columns.append(col_str)
        
        # Force first column to be Indicator if not detected?
        # The first column in these tables is usually the row labels.
        if "Indicator" not in new_columns:
             new_columns[0] = "Indicator"
             
        df.columns = new_columns
        return df
    except Exception as e:
        print(f"Failed to extract {name}: {e}")
        return None

def main():
    driver = setup_driver()
    url = "https://finance.vietstock.vn/VNM-ctcp-sua-viet-nam.htm?languageid=2"
    
    try:
        print(f"Navigating to {url}...")
        driver.get(url)
        time.sleep(5)
        
        income_xpath = "/html/body/div[4]/div[15]/div/div[5]/div[3]/div[2]/div/div[4]/div/div/div[2]/div/table"
        balance_xpath = "/html/body/div[4]/div[15]/div/div[5]/div[3]/div[2]/div/div[4]/div/div/div[2]/div[2]/table"
        # XPath for the 'Previous' button (<) container or button itself
        prev_btn_xpath = "/html/body/div[4]/div[15]/div/div[5]/div[3]/div[2]/div/div[4]/div/div/div/div[2]/div[2]" 
        
        all_frames = []
        
        for i in range(6):
            print(f"\n--- Processing Page {i+1} ---")
            
            # Extract data from current page
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
            
            # Click Previous Button to go to older data (unless last iteration)
            if i < 5:
                try:
                    print("Attempting to click Previous button...")
                    try:
                        prev_btn = driver.find_element(By.XPATH, prev_btn_xpath)
                    except:
                        prev_btn = driver.find_element(By.XPATH, "//i[contains(@class, 'fa-chevron-left')]/.. | //i[contains(@class, 'fa-angle-left')]/..")
                    
                    driver.execute_script("arguments[0].scrollIntoView(true);", prev_btn)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", prev_btn)
                    
                    print("Clicked Previous, waiting for reload...")
                    time.sleep(5) 
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
            
            # Parsing and Sorting logic
            cols = final_df.columns.tolist()
            quarter_cols = []
            other_cols = []
            
            valid_quarter_cols = []
            
            for c in cols:
                match = re.search(r"Q([1-4])/(\d{4})", str(c))
                if match:
                    q = int(match.group(1))
                    y = int(match.group(2))
                    
                    # Filter: Keep if >= Q1/2020
                    # i.e. year > 2020 or (year == 2020 and q >= 1)
                    if y > 2020 or (y == 2020 and q >= 1):
                        valid_quarter_cols.append(c)
                else:
                    other_cols.append(c)
            
            # Sort chronologically
            def sort_key(col_name):
                match = re.search(r"Q([1-4])/(\d{4})", col_name)
                if match:
                    return int(match.group(2)), int(match.group(1))
                return 0, 0
            
            valid_quarter_cols.sort(key=sort_key)
            
            # Reconstruct DataFrame
            final_df = final_df[other_cols + valid_quarter_cols]
            
            print("\nCombined All Data (Filtered >= Q1/2020 & Sorted):")
            print(final_df.head())
            
            output_path = "d:/VN30-Stock-Analysis/finance_data_combined.csv"
            final_df.to_csv(output_path, index=False)
            print(f"Saved combined data to {output_path}")
        else:
            print("No data extracted.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()