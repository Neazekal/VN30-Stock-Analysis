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
        
        income_df = extract_and_clean_table(driver, income_xpath, "Income Statement")
        balance_df = extract_and_clean_table(driver, balance_xpath, "Balance Sheet")
        
        frames = []
        if income_df is not None:
            print("Extracted Income Statement")
            frames.append(income_df)
        if balance_df is not None:
             print("Extracted Balance Sheet")
             frames.append(balance_df)
             
        if frames:
            result = pd.concat(frames, ignore_index=True)
            print("Combined Data:")
            print(result.head())
            print(result.tail())
            
            output_path = "d:/VN30-Stock-Analysis/finance_data_combined.csv"
            result.to_csv(output_path, index=False)
            print(f"Saved combined data to {output_path}")
        else:
            print("No data extracted.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
