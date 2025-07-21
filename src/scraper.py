# simplified_scraper.py
# Cleaned up Jeremy Ranch Golf Club Scraper

import os
import time
import pytz
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
import re

class JeremyRanchScraper:
    def __init__(self):
        self.base_url = "https://www.thejeremy.com"
        self.login_url = f"{self.base_url}/login"
        self.username = os.getenv('GOLF_USERNAME')
        self.password = os.getenv('GOLF_PASSWORD')
        self.driver = None
        self.wait = None
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    def setup_driver(self, headless=True):
        """Initialize Chrome WebDriver"""
        options = Options()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        selenium_url = os.getenv('SELENIUM_HUB_URL', 'http://selenium-chrome:4444')
        
        try:
            self.driver = webdriver.Remote(command_executor=selenium_url, options=options)
            self.wait = WebDriverWait(self.driver, 10)
            self.logger.info("✅ WebDriver initialized")
            return True
        except Exception as e:
            self.logger.error(f"❌ WebDriver failed: {e}")
            return False

    def login(self):
        """Login to the website"""
        try:
            self.logger.info("🔑 Logging in...")
            self.driver.get(self.login_url)
            time.sleep(2)
            
            # Enter credentials
            username_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "masterPageUC_MPCA396908_ctl00_ctl01_txtUsername"))
            )
            username_field.send_keys(self.username)
            
            password_field = self.driver.find_element(By.ID, "masterPageUC_MPCA396908_ctl00_ctl01_txtPassword")
            password_field.send_keys(self.password)
            
            login_button = self.driver.find_element(By.ID, "btnSecureLogin")
            login_button.click()
            
            time.sleep(3)
            
            # Check if login worked (not on login page anymore)
            if "login" not in self.driver.current_url.lower():
                self.logger.info("✅ Login successful")
                return True
            else:
                self.logger.error("❌ Login failed")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Login error: {e}")
            return False

    def navigate_to_booking(self):
        """Navigate to the tee time booking page"""
        try:
            self.logger.info("🧭 Navigating to booking page...")
            
            # Direct URL approach (most reliable)
            booking_url = "https://www.thejeremy.com/Default.aspx?p=dynamicmodule&pageid=397060&tt=booking&ssid=319820&vnf=1"
            self.driver.get(booking_url)
            time.sleep(5)
            
            # Check if we have the date input field
            try:
                self.wait.until(EC.presence_of_element_located((By.ID, "txtDate")))
                self.logger.info("✅ Reached booking page")
                return True
            except TimeoutException:
                self.logger.error("❌ Booking page not loaded properly")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Navigation error: {e}")
            return False

    def set_date_and_refresh(self, target_date):
        """Set the date and refresh the time slots"""
        try:
            date_str = target_date.strftime('%m/%d/%Y')
            self.logger.info(f"📅 Setting date to {date_str}")
            
            # Set date
            date_input = self.driver.find_element(By.ID, "txtDate")
            date_input.clear()
            date_input.send_keys(date_str)
            
            # Refresh times
            try:
                refresh_button = self.driver.find_element(By.XPATH, "//a[@onclick='RefreshTimes();']")
                self.driver.execute_script("arguments[0].click();", refresh_button)
            except:
                self.driver.execute_script("RefreshTimes();")
            
            time.sleep(5)  # Wait for refresh
            self.logger.info("✅ Date set and times refreshed")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Date setting error: {e}")
            return False

    def get_available_times(self):
        """Get all available time slots"""
        try:
            self.logger.info("🔍 Finding available times...")
            
            time_slots = []
            slot_containers = self.driver.find_elements(By.CSS_SELECTOR, "div[id$='_'].tsSection")
            
            for container in slot_containers:
                try:
                    # Get time text
                    time_element = container.find_element(By.CSS_SELECTOR, ".timeText")
                    time_text = time_element.text.strip().split('\n')[0]
                    
                    # Check if available (not reserved)
                    if self._is_slot_available(container):
                        # Find reserve button
                        reserve_button = self._find_reserve_button(container)
                        if reserve_button:
                            time_slots.append({
                                'time': time_text,
                                'element': reserve_button,
                                'container': container
                            })
                            self.logger.info(f"   ✅ {time_text}")
                        else:
                            self.logger.info(f"   ⚠️ {time_text} (no reserve button)")
                    else:
                        self.logger.info(f"   ❌ {time_text} (booked)")
                        
                except Exception as e:
                    continue
            
            self.logger.info(f"📊 Found {len(time_slots)} available slots")
            return time_slots
            
        except Exception as e:
            self.logger.error(f"❌ Error finding times: {e}")
            return []

    def _is_slot_available(self, container):
        """Check if a slot is available"""
        html = container.get_attribute('innerHTML').lower()
        booked_indicators = ['nc_reserved', 'reservedtext', 'reserved']
        return not any(indicator in html for indicator in booked_indicators)

    def _find_reserve_button(self, container):
        """Find the clickable reserve button in a container"""
        try:
            # Look for onclick with LaunchReserver
            clickable = container.find_element(By.XPATH, ".//div[contains(@onclick, 'LaunchReserver')]")
            return clickable
        except:
            try:
                # Alternative: find span with "Reserve" text and get parent
                reserve_span = container.find_element(By.XPATH, ".//span[contains(text(), 'Reserve')]")
                parent = reserve_span.find_element(By.XPATH, "./..")
                if 'LaunchReserver' in parent.get_attribute('onclick') or '':
                    return parent
            except:
                pass
        return None

    def convert_time_to_minutes(self, time_str):
        """Convert time string like '2:45 PM' to minutes since midnight"""
        try:
            # Parse time like "2:45 PM" or "14:45"
            if ':' not in time_str:
                return None
                
            # Handle 24-hour format
            if 'AM' not in time_str.upper() and 'PM' not in time_str.upper():
                # Assume 24-hour format
                hour, minute = map(int, time_str.split(':'))
                return hour * 60 + minute
            
            # Handle 12-hour format
            time_match = re.search(r'(\d{1,2}):(\d{2})\s*([AP]M)', time_str.upper())
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                am_pm = time_match.group(3)
                
                # Convert to 24-hour
                if am_pm == 'PM' and hour != 12:
                    hour += 12
                elif am_pm == 'AM' and hour == 12:
                    hour = 0
                
                return hour * 60 + minute
                
        except Exception as e:
            self.logger.warning(f"Could not parse time '{time_str}': {e}")
        return None

    def find_best_time(self, available_slots, preferred_time):
        """Find the closest available time to preference"""
        if not available_slots:
            return None
            
        # Convert preferred time to minutes
        preferred_minutes = self.convert_time_to_minutes(preferred_time)
        if preferred_minutes is None:
            self.logger.warning(f"Could not parse preferred time: {preferred_time}")
            return available_slots[0]  # Return first available
        
        best_slot = None
        smallest_diff = float('inf')
        
        for slot in available_slots:
            slot_minutes = self.convert_time_to_minutes(slot['time'])
            if slot_minutes is not None:
                diff = abs(slot_minutes - preferred_minutes)
                if diff < smallest_diff:
                    smallest_diff = diff
                    best_slot = slot
                    
                self.logger.info(f"   {slot['time']}: {diff} minutes from target")
        
        if best_slot:
            self.logger.info(f"🎯 Best match: {best_slot['time']} ({smallest_diff} min from {preferred_time})")
        
        return best_slot or available_slots[0]

    def attempt_booking(self, time_slot, test_mode=True):
        """Attempt to book a time slot"""
        try:
            self.logger.info(f"🚀 {'Testing' if test_mode else 'Booking'} {time_slot['time']}...")
            
            # Click reserve button
            reserve_button = time_slot['element']
            self.driver.execute_script("arguments[0].click();", reserve_button)
            time.sleep(5)  # Wait for popup to load
            
            # Go directly to iframe 2 where we know the Make Tee Time button is
            self.logger.info("🎯 Looking for Make Tee Time button in iframe 2...")
            
            try:
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                self.logger.info(f"Found {len(iframes)} iframes")
                
                if len(iframes) >= 2:
                    # Switch to iframe 2 (index 1)
                    self.driver.switch_to.frame(iframes[1])
                    self.logger.info("✅ Switched to iframe 2")
                    
                    # Look for the Make Tee Time button
                    make_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "ctl00_ctrl_MakeTeeTime_lbBook"))
                    )
                    
                    if make_button:
                        self.logger.info("✅ Found Make Tee Time button!")
                        
                        if test_mode:
                            self.logger.info("✅ TEST SUCCESS: Found Make Tee Time button and ready to book!")
                            self.logger.info("✅ Ready for real booking (set test_mode=False)")
                            self.driver.switch_to.default_content()
                            return True
                        else:
                            self.logger.info("🏌️ Clicking Make Tee Time button...")
                            self.driver.execute_script("arguments[0].click();", make_button)
                            time.sleep(5)
                            
                            # Switch back to main content to check results
                            self.driver.switch_to.default_content()
                            return self._verify_booking_success()
                    else:
                        self.logger.error("❌ Make Tee Time button not found in iframe 2")
                        self.driver.switch_to.default_content()
                        return False
                else:
                    self.logger.error("❌ Not enough iframes found")
                    return False
                    
            except TimeoutException:
                self.logger.error("❌ Timeout waiting for Make Tee Time button")
                self.driver.switch_to.default_content()
                return False
            except Exception as iframe_error:
                self.logger.error(f"❌ Error accessing iframe: {iframe_error}")
                self.driver.switch_to.default_content()
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Booking error: {e}")
            self.driver.switch_to.default_content()
            return False

    def _verify_booking_success(self):
        """Verify booking was successful"""
        try:
            # Look for success indicators
            success_keywords = ['success', 'confirmed', 'booked', 'thank you']
            page_text = self.driver.page_source.lower()
            
            for keyword in success_keywords:
                if keyword in page_text:
                    self.logger.info(f"✅ Booking success detected: '{keyword}' found in page")
                    return True
            
            self.logger.warning("❌ No success indicators found")
            return False
        except Exception as e:
            self.logger.error(f"Error verifying booking: {e}")
            return False

    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()

    def book_tee_time(self, target_date, preferred_time, test_mode=True):
        """Main booking method"""
        try:
            self.logger.info(f"🎯 Starting booking for {target_date.strftime('%Y-%m-%d')} at {preferred_time}")
            
            # Setup and login
            if not self.setup_driver(headless=os.getenv('HEADLESS_BROWSER', 'true').lower() == 'true'):
                return False
            
            if not self.login():
                return False
            
            if not self.navigate_to_booking():
                return False
            
            if not self.set_date_and_refresh(target_date):
                return False
            
            # Find available times
            available_times = self.get_available_times()
            if not available_times:
                self.logger.warning("❌ No available times found")
                return False
            
            # Find best time and attempt booking
            best_slot = self.find_best_time(available_times, preferred_time)
            if best_slot:
                return self.attempt_booking(best_slot, test_mode)
            else:
                self.logger.error("❌ No suitable time slot found")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Booking failed: {e}")
            return False
        finally:
            self.cleanup()


def test_booking(date_str="2025-07-22", preferred_time="14:45"):
    """Test the booking process"""
    print(f"🧪 Testing booking for {date_str} at {preferred_time}")
    
    scraper = JeremyRanchScraper()
    target_date = datetime.strptime(date_str, '%Y-%m-%d')
    
    # Test in non-headless mode for debugging
    os.environ['HEADLESS_BROWSER'] = 'false'
    
    success = scraper.book_tee_time(target_date, preferred_time, test_mode=True)
    
    if success:
        print("🎉 TEST PASSED: Ready for real booking!")
    else:
        print("❌ TEST FAILED: Check logs for issues")
    
    return success


if __name__ == "__main__":
    test_booking("2025-07-22", "14:45")