import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

def run_search():
    # Initialize the Chrome driver
    driver = webdriver.Chrome()
    
    try:
        # Navigate to Vietstock finance
        driver.get("https://finance.vietstock.vn/?languageid=2")
        driver.maximize_window()
        
        # Explicit wait
        wait = WebDriverWait(driver, 10)
        
        # --- Handle Login Popup if it appears ---
        def handle_login_popup():
            try:
                # Check directly for the login form container being visible
                # The user reported #login-form interfering, so we check that specifically.
                login_form = WebDriverWait(driver, 5).until(
                    EC.visibility_of_element_located((By.ID, "login-form"))
                )
                print("Login form detected. Attempting to close...")
                
                # Find the close button inside the form
                close_btn = login_form.find_element(By.CSS_SELECTOR, ".close-popup-icon-x")
                close_btn.click()
                print("Clicked close button.")
                
                # Wait for it to disappear
                WebDriverWait(driver, 3).until(
                    EC.invisibility_of_element_located((By.ID, "login-form"))
                )
                print("Login popup closed.")
            except Exception as e:
                # If normal click fails or element not found, try JS specific fallback
                try:
                    driver.execute_script("$('#login-form').modal('hide');")
                    print("Attempted to close details via JS.")
                except:
                    pass
                print(f"Popup handling trace: {str(e)}")
                print("No active login popup found or already closed. Proceeding...")

        # Optional: Uncomment the next line to 'simulate' the popup by clicking login first (for testing)
        # driver.find_element(By.CSS_SELECTOR, ".btnlogin-link").click(); time.sleep(1)
        
        handle_login_popup()
        # ----------------------------------------
        
        handle_login_popup()
        # ----------------------------------------
        
        stocks_to_search = ["ACB", "VIC", "VNM"]
        
        for stock in stocks_to_search:
            print(f"--- Searching for {stock} ---")
            
            # 1. Click the search icon
            # Use a try-except or check if search input is already visible to avoid re-clicking if it stays open
            # But usually it closes or we might need to re-open it.
            # Best is to check if input is visible. If not, click button.
            try:
                 # Check if search input is visible
                 search_input = driver.find_element(By.ID, "popup-search-txt")
                 if not search_input.is_displayed():
                     raise Exception("Input not displayed")
            except:
                 # Click button if input not found or not displayed
                 search_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-mobile-search")))
                 search_btn.click()
                 search_input = wait.until(EC.visibility_of_element_located((By.ID, "popup-search-txt")))

            # 2. Clear and Type Stock Symbol
            search_input.clear()
            search_input.send_keys(stock)
            
            # Wait 3 seconds as requested (after typing)
            print(f"Waiting 3 seconds for results for {stock}...")
            time.sleep(3)
            
            # 3. Wait for results and click the first one in a new tab
            # Use the specific container for stock results: #list-stock-search
            stock_list = wait.until(EC.visibility_of_element_located((By.ID, "list-stock-search")))
            first_result = stock_list.find_element(By.TAG_NAME, "a")
            
            print(f"Found result: {first_result.text}")
            print(f"Result href: {first_result.get_attribute('href')}")
            
            # Open in new tab using Control + Click
            actions = ActionChains(driver)
            actions.key_down(Keys.CONTROL).click(first_result).key_up(Keys.CONTROL).perform()
            
            # Wait for tab to open
            wait.until(lambda d: len(d.window_handles) > 1)
            
            # Switch to new tab
            driver.switch_to.window(driver.window_handles[-1])
            print(f"Switched to tab: {driver.title}")
            
            # Wait for page load (simulate 'load' by waiting for body or title)
            # Just wait a few seconds to let user 'see' it as requested "để nó load xong"
            try:
                # Wait for title to include stock name (basic check)
                wait.until(EC.title_contains(stock))
                print(f"Page loaded for {stock}.")
            except:
                print(f"Timed out waiting for title match for {stock}, but page loaded.")
            
            time.sleep(2) # Extra visual wait

            # Close current tab
            driver.close()
            print(f"Closed tab for {stock}")
            
            # Switch back to main tab
            driver.switch_to.window(driver.window_handles[0])
            print("Switched back to main tab.")
            
            # Pause briefly before next iteration
            time.sleep(1)

        print("All stocks processed.")
        time.sleep(2)
        
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_search()
