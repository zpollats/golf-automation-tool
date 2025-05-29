# Jeremy Ranch Golf Club Scraper Configuration
# Based on HTML analysis of ClubEssential platform

import os
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging

class JeremyRanchScraper:
    def __init__(self):
        self.base_url = "https://www.thejeremy.com"
        self.login_url = f"{self.base_url}/login"
        self.username = os.getenv('GOLF_USERNAME')
        self.password = os.getenv('GOLF_PASSWORD')
        self.driver = None
        self.wait = None
        
        # Login form element IDs (from HTML analysis)
        self.username_field_id = "masterPageUC_MPCA396908_ctl00_ctl01_txtUsername"
        self.password_field_id = "masterPageUC_MPCA396908_ctl00_ctl01_txtPassword"
        self.login_button_id = "btnSecureLogin"
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def setup_driver(self, headless=True):
        """Initialize Chrome WebDriver with appropriate options"""
        options = Options()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # Connect to Selenium Grid in Docker
        selenium_url = os.getenv('SELENIUM_HUB_URL', 'http://selenium-chrome:4444')
        
        try:
            self.driver = webdriver.Remote(
                command_executor=selenium_url,
                options=options
            )
            self.wait = WebDriverWait(self.driver, 10)
            self.logger.info("WebDriver initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize WebDriver: {e}")
            return False

    def login(self):
        """Login to Jeremy Ranch Golf Club website"""
        try:
            self.logger.info("Navigating to login page...")
            self.driver.get(self.login_url)
            
            # Wait for page to load
            time.sleep(2)
            
            # Find and fill username field
            self.logger.info("Entering username...")
            username_field = self.wait.until(
                EC.presence_of_element_located((By.ID, self.username_field_id))
            )
            username_field.clear()
            username_field.send_keys(self.username)
            
            # Find and fill password field
            self.logger.info("Entering password...")
            password_field = self.driver.find_element(By.ID, self.password_field_id)
            password_field.clear()
            password_field.send_keys(self.password)
            
            # Click login button
            self.logger.info("Clicking login button...")
            login_button = self.driver.find_element(By.ID, self.login_button_id)
            login_button.click()
            
            # Wait for login to complete (check for redirect or success indicator)
            time.sleep(3)
            
            # Check if login was successful
            if self.is_logged_in():
                self.logger.info("Login successful!")
                return True
            else:
                self.logger.error("Login failed - still on login page")
                return False
                
        except TimeoutException:
            self.logger.error("Timeout waiting for login elements")
            return False
        except Exception as e:
            self.logger.error(f"Login error: {e}")
            return False

    def is_logged_in(self):
        """Check if successfully logged in by looking for member-specific elements"""
        try:
            # After login, we should be redirected away from login page
            current_url = self.driver.current_url
            if "login" not in current_url.lower():
                return True
            
            # Alternative: check for logout link or member menu
            try:
                # Look for common post-login elements
                member_elements = self.driver.find_elements(By.XPATH, 
                    "//a[contains(text(), 'Logout') or contains(text(), 'Member') or contains(text(), 'Account')]")
                return len(member_elements) > 0
            except:
                pass
                
            return False
        except Exception as e:
            self.logger.error(f"Error checking login status: {e}")
            return False

    def navigate_to_tee_times(self):
        """Navigate to tee time booking section"""
        try:
            self.logger.info("Looking for 'Book A Tee Time' link...")
            
            # First try the specific "Book A Tee Time" link from the dashboard
            book_tee_time_selectors = [
                "//a[contains(text(), 'Book A Tee Time')]",
                "//a[@href*='397060']",  # From the HTML: pageid=397060&tt=booking
                "//a[@href*='Tee Times Reservations']",
                "//span[contains(text(), 'Book A Tee Time')]/parent::a"
            ]
            
            for selector in book_tee_time_selectors:
                try:
                    tee_time_link = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    self.logger.info(f"Found 'Book A Tee Time' link: {tee_time_link.text}")
                    tee_time_link.click()
                    time.sleep(3)
                    
                    # Wait for the booking page to load and check for booking elements
                    try:
                        # Wait for either the date input or time slots to appear
                        self.wait.until(
                            EC.any_of(
                                EC.presence_of_element_located((By.ID, "txtDate")),
                                EC.presence_of_element_located((By.CSS_SELECTOR, "div[id$='AM1_'], div[id$='PM1_']"))
                            )
                        )
                        self.logger.info("Successfully navigated to tee time booking page")
                        return True
                    except TimeoutException:
                        self.logger.warning("Clicked link but booking elements not found, trying next selector...")
                        continue
                        
                except (NoSuchElementException, TimeoutException):
                    continue
            
            # Alternative: Try the main navigation Golf > Tee Times Reservations
            self.logger.info("Trying main navigation Golf menu...")
            try:
                # Look for Golf in main navigation
                golf_nav = self.driver.find_element(By.XPATH, "//li[contains(text(), 'Golf')]")
                golf_nav.click()
                time.sleep(2)
                
                # Then look for Tee Times Reservations
                tee_reservations = self.driver.find_element(
                    By.XPATH, "//a[contains(text(), 'Tee Times Reservations')]"
                )
                tee_reservations.click()
                time.sleep(3)
                
                # Check if we reached the booking page
                try:
                    self.wait.until(
                        EC.presence_of_element_located((By.ID, "txtDate"))
                    )
                    return True
                except TimeoutException:
                    pass
                    
            except NoSuchElementException:
                pass
            
            # Final fallback: direct URL navigation if we know the booking URL
            self.logger.info("Trying direct navigation to booking URL...")
            try:
                booking_url = "https://www.thejeremy.com/Default.aspx?p=dynamicmodule&pageid=397060&tt=booking&ssid=319820&vnf=1"
                self.driver.get(booking_url)
                time.sleep(5)
                
                # Check if we reached the booking page
                try:
                    self.wait.until(
                        EC.presence_of_element_located((By.ID, "txtDate"))
                    )
                    self.logger.info("Successfully navigated via direct URL")
                    return True
                except TimeoutException:
                    pass
                    
            except Exception as e:
                self.logger.error(f"Direct URL navigation failed: {e}")
            
            self.logger.warning("Could not find tee time booking navigation")
            return False
            
        except Exception as e:
            self.logger.error(f"Error navigating to tee times: {e}")
            return False

    def wait_for_page_load(self, timeout=10):
        """Wait for ASP.NET page to fully load"""
        try:
            # Wait for ASP.NET specific indicators
            self.wait.until(
                EC.presence_of_element_located((By.NAME, "__VIEWSTATE"))
            )
            # Additional wait for dynamic content
            time.sleep(2)
            return True
        except TimeoutException:
            self.logger.warning("Page load timeout - continuing anyway")
            return False

    def get_target_date(self, days_advance=7):
        """Calculate the target booking date (7 days from now)"""
        target_date = datetime.now() + timedelta(days=days_advance)
        return target_date

    def debug_current_page(self, step_name=""):
        """Debug helper to log current page info"""
        try:
            current_url = self.driver.current_url
            page_title = self.driver.title
            self.logger.info(f"Debug {step_name} - URL: {current_url}")
            self.logger.info(f"Debug {step_name} - Title: {page_title}")
            
            # Look for common booking elements
            booking_indicators = [
                "//input[@type='date']",
                "//select[contains(@name, 'date')]",
                "//div[contains(@class, 'calendar')]",
                "//div[contains(@class, 'time')]",
                "//button[contains(text(), 'Book')]",
                "//a[contains(text(), 'Available')]"
            ]
            
            found_elements = []
            for selector in booking_indicators:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        found_elements.append(f"{selector}: {len(elements)} found")
                except:
                    pass
            
            if found_elements:
                self.logger.info(f"Debug {step_name} - Booking elements found: {found_elements}")
            else:
                self.logger.info(f"Debug {step_name} - No obvious booking elements found")
                
        except Exception as e:
            self.logger.error(f"Debug error: {e}")

    def save_page_source(self, filename_prefix="page"):
        """Save current page source for analysis"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"/tmp/{filename_prefix}_{timestamp}.html"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            self.logger.info(f"Page source saved to: {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"Failed to save page source: {e}")
            return None
        """Calculate the target booking date (7 days from now)"""
        target_date = datetime.now() + timedelta(days=days_advance)
        return target_date

    def find_available_times(self, target_date):
        """Find available tee times for the target date"""
        try:
            target_date_str = target_date.strftime('%m/%d/%Y')  # MM/DD/YYYY format
            self.logger.info(f"Looking for available times on {target_date_str}")
            
            # Step 1: Set the date in the date picker
            self.logger.info("Setting date in date picker...")
            try:
                date_input = self.wait.until(
                    EC.presence_of_element_located((By.ID, "txtDate"))
                )
                date_input.clear()
                date_input.send_keys(target_date_str)
                
                # Trigger the date update JavaScript function
                self.driver.execute_script("updatePersistDate(document.getElementById('txtDate'))")
                self.logger.info(f"Date set to: {target_date_str}")
                
                # Wait for time slots to reload
                time.sleep(3)
                
            except TimeoutException:
                self.logger.error("Could not find date input field (#txtDate)")
                return []
            
            # Step 2: Wait for time slots to load
            self.logger.info("Waiting for time slots to load...")
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".openTee"))
                )
            except TimeoutException:
                self.logger.warning("No available time slots found (no .openTee elements)")
                # Check if there are any time slots at all
                all_slots = self.driver.find_elements(By.CSS_SELECTOR, "div[id$='AM1_'], div[id$='PM1_']")
                self.logger.info(f"Total time slot containers found: {len(all_slots)}")
                return []
            
            # Step 3: Find all available time slots
            available_slots = self.driver.find_elements(By.CSS_SELECTOR, ".openTee")
            self.logger.info(f"Found {len(available_slots)} available time slots")
            
            time_slots = []
            for slot in available_slots:
                try:
                    # Get the time text from the slot
                    time_text_element = slot.find_element(By.XPATH, 
                        "./ancestor::div[contains(@class, 'tsSection')]//span[@class='timeText']")
                    time_text = time_text_element.text
                    
                    # Get the container ID to identify the specific slot
                    time_container = slot.find_element(By.XPATH, 
                        "./ancestor::div[contains(@id, 'AM1_') or contains(@id, 'PM1_')]")
                    slot_id = time_container.get_attribute('id')
                    
                    time_slots.append({
                        'element': slot,
                        'time': time_text,
                        'slot_id': slot_id,
                        'available': True
                    })
                    
                    self.logger.info(f"Available slot: {time_text} (ID: {slot_id})")
                    
                except Exception as e:
                    self.logger.warning(f"Could not extract time info from slot: {e}")
                    continue
            
            return time_slots
            
        except Exception as e:
            self.logger.error(f"Error finding available times: {e}")
            return []

    def book_tee_time(self, time_slot, preferred_times=None):
        """Book a specific tee time using Jeremy Ranch's ASP.NET system"""
        try:
            self.logger.info(f"Attempting to book tee time: {time_slot['time']} (ID: {time_slot['slot_id']})")
            
            # Click the Reserve button using JavaScript (more reliable for ASP.NET)
            reserve_button = time_slot['element']
            self.driver.execute_script("arguments[0].click();", reserve_button)
            
            self.logger.info("Clicked Reserve button")
            time.sleep(3)
            
            # Wait for the booking form or confirmation to appear
            # This could be a popup, new page, or form update
            try:
                # Look for common booking confirmation elements
                confirmation_selectors = [
                    ".booking-confirmation",
                    "[class*='confirm']",
                    "[class*='success']",
                    "input[value*='Confirm']",
                    "button[onclick*='confirm']",
                    ".notifyjs-corner"  # Notification system
                ]
                
                confirmation_found = False
                for selector in confirmation_selectors:
                    try:
                        confirmation_element = self.wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        self.logger.info(f"Found confirmation element: {selector}")
                        confirmation_found = True
                        break
                    except TimeoutException:
                        continue
                
                if not confirmation_found:
                    # Check if we're still on the same page or redirected
                    current_url = self.driver.current_url
                    self.logger.info(f"Current URL after booking attempt: {current_url}")
                    
                    # Look for any success indicators in the page content
                    page_text = self.driver.page_source.lower()
                    success_indicators = ['booked', 'reserved', 'confirmed', 'success']
                    
                    for indicator in success_indicators:
                        if indicator in page_text:
                            self.logger.info(f"Found success indicator: {indicator}")
                            return True
                
                # If there's a confirmation step, handle it
                if confirmation_found:
                    # Look for final confirmation button
                    final_confirm_selectors = [
                        "input[value*='Confirm']",
                        "button[onclick*='confirm']",
                        ".confirm-button",
                        "input[type='submit']"
                    ]
                    
                    for selector in final_confirm_selectors:
                        try:
                            confirm_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                            if confirm_btn.is_enabled() and confirm_btn.is_displayed():
                                self.logger.info(f"Clicking final confirmation button: {selector}")
                                self.driver.execute_script("arguments[0].click();", confirm_btn)
                                time.sleep(3)
                                break
                        except NoSuchElementException:
                            continue
                
                # Verify booking success
                return self.verify_booking_success()
                
            except Exception as e:
                self.logger.error(f"Error in booking confirmation process: {e}")
                return False
            
        except Exception as e:
            self.logger.error(f"Error booking tee time: {e}")
            return False

    def verify_booking_success(self):
        """Verify that the booking was successful"""
        try:
            # Look for success indicators specific to Jeremy Ranch/ClubEssential
            success_indicators = [
                ".notifyjs-corner",  # Notification system
                "[class*='success']",
                "[class*='confirm']",
                "//div[contains(text(), 'success') or contains(text(), 'confirmed')]",
                "//div[contains(text(), 'booked') or contains(text(), 'reserved')]",
                "//span[contains(text(), 'Thank you')]"
            ]
            
            for indicator in success_indicators:
                try:
                    if indicator.startswith("//"):
                        element = self.driver.find_element(By.XPATH, indicator)
                    else:
                        element = self.driver.find_element(By.CSS_SELECTOR, indicator)
                    
                    if element.is_displayed():
                        success_text = element.text
                        self.logger.info(f"Booking success confirmed: {success_text}")
                        return True
                except NoSuchElementException:
                    continue
            
            # Alternative: check URL change
            current_url = self.driver.current_url
            if any(keyword in current_url.lower() for keyword in ['success', 'confirm', 'booked', 'complete']):
                self.logger.info(f"Booking success detected via URL: {current_url}")
                return True
            
            # Alternative: check page content for success keywords
            page_text = self.driver.page_source.lower()
            success_keywords = [
                'tee time has been booked',
                'reservation confirmed',
                'booking successful',
                'thank you for your reservation'
            ]
            
            for keyword in success_keywords:
                if keyword in page_text:
                    self.logger.info(f"Booking success detected via page content: {keyword}")
                    return True
            
            self.logger.warning("No clear booking success indicators found")
            return False
            
        except Exception as e:
            self.logger.error(f"Error verifying booking: {e}")
            return False

    def run_booking_attempt(self, preferred_times=None):
        """Main method to run the complete booking process"""
        try:
            # Setup driver
            if not self.setup_driver(headless=os.getenv('HEADLESS_BROWSER', 'true').lower() == 'true'):
                return False
            
            # Login
            if not self.login():
                return False
            
            # Navigate to tee times
            if not self.navigate_to_tee_times():
                return False
            
            # Get target date (7 days from now)
            target_date = self.get_target_date(7)
            
            # Find available times
            available_times = self.find_available_times(target_date)
            if not available_times:
                self.logger.warning("No available tee times found")
                return False
            
            # Book preferred time or first available
            if preferred_times:
                for pref_time in preferred_times:
                    for slot in available_times:
                        if pref_time in slot['time']:
                            return self.book_tee_time(slot)
            
            # Book first available time if no preference matched
            return self.book_tee_time(available_times[0])
            
        except Exception as e:
            self.logger.error(f"Booking attempt failed: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()

    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()

# Test function
def test_scraper():
    """Test the scraper with current configuration"""
    scraper = JeremyRanchScraper()
    
    try:
        # Test with visible browser for debugging
        if scraper.setup_driver(headless=False):
            print("✅ Driver setup successful!")
            scraper.debug_current_page("Initial")
            
            if scraper.login():
                print("✅ Login successful!")
                scraper.debug_current_page("After Login")
                scraper.save_page_source("after_login")
                
                # Try to navigate to tee times
                if scraper.navigate_to_tee_times():
                    print("✅ Navigation to tee times successful!")
                    scraper.debug_current_page("Tee Time Booking Page")
                    scraper.save_page_source("tee_time_booking")
                    
                    # Keep browser open for manual inspection
                    print("\n🔍 Browser will stay open for 30 seconds for manual inspection...")
                    print("Check the VNC viewer at http://localhost:7900 (password: secret)")
                    time.sleep(30)
                else:
                    print("❌ Could not find tee time navigation")
                    scraper.debug_current_page("Navigation Failed")
                    scraper.save_page_source("navigation_failed")
            else:
                print("❌ Login failed")
                scraper.debug_current_page("Login Failed")
                scraper.save_page_source("login_failed")
        else:
            print("❌ Driver setup failed")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
    finally:
        scraper.cleanup()

def test_full_booking_flow():
    """Test the complete booking flow"""
    scraper = JeremyRanchScraper()
    
    try:
        # Setup with visible browser for debugging
        if scraper.setup_driver(headless=False):
            print("✅ Driver setup successful!")
            
            if scraper.login():
                print("✅ Login successful!")
                scraper.debug_current_page("After Login")
                
                # Navigate to tee time booking
                if scraper.navigate_to_tee_times():
                    print("✅ Navigation to tee times successful!")
                    scraper.debug_current_page("Tee Time Booking Page")
                    scraper.save_page_source("tee_time_booking")
                    
                    # Test finding available times (7 days from now)
                    target_date = scraper.get_target_date(7)
                    print(f"🎯 Looking for tee times on: {target_date.strftime('%m/%d/%Y')}")
                    
                    available_times = scraper.find_available_times(target_date)
                    if available_times:
                        print(f"✅ Found {len(available_times)} available time slots!")
                        
                        # Show available times
                        for i, slot in enumerate(available_times[:5]):  # Show first 5
                            print(f"   {i+1}. {slot['time']} (ID: {slot['slot_id']})")
                        
                        # Optionally test booking (be careful!)
                        # Uncomment the next line to test actual booking
                        # NOTE: This will make a real reservation!
                        
                        # if input("Test actual booking? (y/N): ").lower() == 'y':
                        #     first_time = available_times[0]
                        #     print(f"🚀 Attempting to book: {first_time['time']}")
                        #     success = scraper.book_tee_time(first_time)
                        #     if success:
                        #         print("✅ Booking successful!")
                        #     else:
                        #         print("❌ Booking failed")
                        
                        print("\n🔍 Browser staying open for manual inspection...")
                        print("Check VNC viewer at http://localhost:7900")
                        time.sleep(60)  # Keep open longer for inspection
                        
                    else:
                        print("❌ No available times found")
                        print("This might be normal if booking is full or not yet open")
                        scraper.debug_current_page("No Available Times")
                        print("\n🔍 Browser staying open for inspection...")
                        time.sleep(30)
                else:
                    print("❌ Could not navigate to tee time booking")
                    scraper.debug_current_page("Navigation Failed")
            else:
                print("❌ Login failed")
        else:
            print("❌ Driver setup failed")
    finally:
        scraper.cleanup()

def test_date_selection_only():
    """Test just the date selection functionality"""
    scraper = JeremyRanchScraper()
    
    try:
        if scraper.setup_driver(headless=False):
            print("✅ Driver setup successful!")
            
            if scraper.login() and scraper.navigate_to_tee_times():
                print("✅ Reached tee time booking page!")
                
                # Test date selection
                target_date = scraper.get_target_date(7)
                print(f"🎯 Testing date selection for: {target_date.strftime('%m/%d/%Y')}")
                
                try:
                    # Try to set the date
                    date_input = scraper.driver.find_element(By.ID, "txtDate")
                    current_date = date_input.get_attribute('value')
                    print(f"Current date value: {current_date}")
                    
                    date_input.clear()
                    target_date_str = target_date.strftime('%m/%d/%Y')
                    date_input.send_keys(target_date_str)
                    print(f"Set date to: {target_date_str}")
                    
                    # Trigger the update
                    scraper.driver.execute_script("updatePersistDate(document.getElementById('txtDate'))")
                    print("✅ Triggered date update script")
                    
                    time.sleep(5)  # Wait for update
                    
                    # Check for time slots
                    time_containers = scraper.driver.find_elements(By.CSS_SELECTOR, "div[id$='AM1_'], div[id$='PM1_']")
                    available_slots = scraper.driver.find_elements(By.CSS_SELECTOR, ".openTee")
                    
                    print(f"Time containers found: {len(time_containers)}")
                    print(f"Available slots found: {len(available_slots)}")
                    
                    print("\n🔍 Browser staying open for inspection...")
                    time.sleep(45)
                    
                except Exception as e:
                    print(f"❌ Date selection test failed: {e}")
                    
    finally:
        scraper.cleanup()

if __name__ == "__main__":
    test_scraper()