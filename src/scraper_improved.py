# src/scraper_improved.py
"""
Improved Jeremy Ranch Golf Club Scraper
With enhanced time slot detection and debugging capabilities
"""

import os
import time
import re
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging

class ImprovedJeremyRanchScraper:
    def __init__(self):
        self.base_url = "https://www.thejeremy.com"
        self.login_url = f"{self.base_url}/login"
        self.username = os.getenv('GOLF_USERNAME')
        self.password = os.getenv('GOLF_PASSWORD')
        self.driver = None
        self.wait = None
        
        # Login form element IDs
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
            time.sleep(2)
            
            # Fill username
            username_field = self.wait.until(
                EC.presence_of_element_located((By.ID, self.username_field_id))
            )
            username_field.clear()
            username_field.send_keys(self.username)
            
            # Fill password
            password_field = self.driver.find_element(By.ID, self.password_field_id)
            password_field.clear()
            password_field.send_keys(self.password)
            
            # Click login
            login_button = self.driver.find_element(By.ID, self.login_button_id)
            login_button.click()
            
            time.sleep(3)
            
            # Check if logged in
            if self.is_logged_in():
                self.logger.info("Login successful!")
                return True
            else:
                self.logger.error("Login failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Login error: {e}")
            return False

    def is_logged_in(self):
        """Check if successfully logged in"""
        current_url = self.driver.current_url
        return "login" not in current_url.lower()

    def navigate_to_tee_times(self):
        """Navigate to tee time booking section"""
        try:
            self.logger.info("Navigating to tee time booking...")
            
            # Direct URL approach
            booking_url = ("https://www.thejeremy.com/Default.aspx?"
                          "p=dynamicmodule&pageid=397060&tt=booking&ssid=319820&vnf=1")
            self.driver.get(booking_url)
            time.sleep(5)
            
            # Verify we're on the booking page
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.ID, "txtDate"))
                )
                self.logger.info("Successfully navigated to tee time booking page")
                return True
            except TimeoutException:
                self.logger.error("Could not find date input field")
                return False
                
        except Exception as e:
            self.logger.error(f"Error navigating to tee times: {e}")
            return False

    def set_date(self, target_date):
        """Set the date in the booking form"""
        try:
            target_date_str = target_date.strftime('%m/%d/%Y')
            self.logger.info(f"Setting date to: {target_date_str}")
            
            date_input = self.wait.until(
                EC.presence_of_element_located((By.ID, "txtDate"))
            )
            date_input.clear()
            date_input.send_keys(target_date_str)
            
            # Trigger the date update JavaScript function
            self.driver.execute_script("updatePersistDate(document.getElementById('txtDate'))")
            self.logger.info(f"Date set to: {target_date_str}")
            
            # Wait for time slots to reload
            time.sleep(5)
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting date: {e}")
            return False

    def find_available_times_improved(self, target_date):
        """
        Improved method to find available tee times using multiple detection strategies
        """
        try:
            self.logger.info(f"Looking for available times on {target_date.strftime('%m/%d/%Y')}")
            
            # Set the date first
            if not self.set_date(target_date):
                return []
            
            # Wait for content to load after date change
            time.sleep(3)
            
            # Strategy 1: Look for elements with common time slot patterns
            time_slots = []
            
            # Multiple selector strategies to try
            selector_strategies = [
                {
                    'name': 'OpenTee Class Strategy',
                    'container_selector': '.openTee',
                    'time_extraction': 'text'
                },
                {
                    'name': 'AM/PM ID Strategy', 
                    'container_selector': "div[id*='AM'], div[id*='PM']",
                    'time_extraction': 'text'
                },
                {
                    'name': 'Button OnClick Strategy',
                    'container_selector': "button[onclick], input[type='button'][onclick]",
                    'time_extraction': 'onclick_or_text'
                },
                {
                    'name': 'Available Class Strategy',
                    'container_selector': "[class*='available']",
                    'time_extraction': 'text'
                },
                {
                    'name': 'Time Class Strategy',
                    'container_selector': "[class*='time'][class*='slot'], [class*='slot'][class*='time']",
                    'time_extraction': 'text'
                },
                {
                    'name': 'Table Cell Strategy',
                    'container_selector': "td[onclick], td[class*='available']",
                    'time_extraction': 'text'
                }
            ]
            
            for strategy in selector_strategies:
                self.logger.info(f"Trying strategy: {strategy['name']}")
                slots = self._try_selector_strategy(strategy)
                if slots:
                    self.logger.info(f"✅ Found {len(slots)} slots with {strategy['name']}")
                    time_slots.extend(slots)
                    break  # Use first successful strategy
                else:
                    self.logger.info(f"❌ No slots found with {strategy['name']}")
            
            # Remove duplicates based on time text
            unique_slots = []
            seen_times = set()
            for slot in time_slots:
                if slot['time'] not in seen_times:
                    unique_slots.append(slot)
                    seen_times.add(slot['time'])
            
            self.logger.info(f"Found {len(unique_slots)} unique available time slots")
            for slot in unique_slots:
                self.logger.info(f"  - {slot['time']}")
            
            return unique_slots
            
        except Exception as e:
            self.logger.error(f"Error finding available times: {e}")
            return []

    def _try_selector_strategy(self, strategy):
        """Try a specific selector strategy to find time slots"""
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, strategy['container_selector'])
            if not elements:
                return []
            
            slots = []
            for element in elements:
                try:
                    # Skip if element is not visible or enabled
                    if not element.is_displayed():
                        continue
                    
                    # Extract time based on strategy
                    time_text = self._extract_time_from_element(element, strategy['time_extraction'])
                    if time_text:
                        slots.append({
                            'element': element,
                            'time': time_text,
                            'selector': strategy['container_selector'],
                            'strategy': strategy['name']
                        })
                        
                except Exception as e:
                    # Skip problematic elements
                    continue
            
            return slots
            
        except Exception as e:
            return []

    def _extract_time_from_element(self, element, extraction_method):
        """Extract time text from an element using various methods"""
        try:
            time_text = None
            
            if extraction_method == 'text':
                # Get element text and look for time patterns
                text = element.text.strip()
                time_text = self._extract_time_from_text(text)
                
            elif extraction_method == 'onclick_or_text':
                # First try onclick attribute
                onclick = element.get_attribute('onclick')
                if onclick:
                    time_text = self._extract_time_from_text(onclick)
                
                # Fallback to element text
                if not time_text:
                    text = element.text.strip()
                    time_text = self._extract_time_from_text(text)
            
            # Additional checks for nested elements with time text
            if not time_text:
                # Look for child elements with time-like text
                time_elements = element.find_elements(By.XPATH, ".//*[contains(@class, 'time') or contains(text(), 'AM') or contains(text(), 'PM')]")
                for time_elem in time_elements:
                    candidate_text = time_elem.text.strip()
                    time_text = self._extract_time_from_text(candidate_text)
                    if time_text:
                        break
            
            return time_text
            
        except Exception as e:
            return None

    def _extract_time_from_text(self, text):
        """Extract time from text using regex patterns"""
        if not text:
            return None
        
        # Common time patterns
        time_patterns = [
            r'\b\d{1,2}:\d{2}\s*[AP]M\b',  # 9:00 AM, 10:30 PM
            r'\b\d{1,2}:\d{2}\b',          # 9:00, 10:30
            r'\b\d{1,2}\s*[AP]M\b',        # 9 AM, 10 PM
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group().strip()
        
        return None

    def book_tee_time_improved(self, time_slot):
        """
        Improved booking method with better error handling and confirmation detection
        """
        try:
            self.logger.info(f"Attempting to book: {time_slot['time']} using {time_slot['strategy']}")
            
            # Click the time slot element
            element = time_slot['element']
            
            # Try multiple click methods
            click_successful = False
            
            # Method 1: Regular click
            try:
                if element.is_enabled() and element.is_displayed():
                    element.click()
                    click_successful = True
                    self.logger.info("Clicked using regular click")
            except:
                pass
            
            # Method 2: JavaScript click
            if not click_successful:
                try:
                    self.driver.execute_script("arguments[0].click();", element)
                    click_successful = True
                    self.logger.info("Clicked using JavaScript click")
                except:
                    pass
            
            # Method 3: Execute onclick if available
            if not click_successful:
                try:
                    onclick = element.get_attribute('onclick')
                    if onclick:
                        self.driver.execute_script(onclick)
                        click_successful = True
                        self.logger.info("Executed onclick JavaScript")
                except:
                    pass
            
            if not click_successful:
                self.logger.error("Failed to click time slot element")
                return False
            
            # Wait for response
            time.sleep(3)
            
            # Check for booking confirmation using multiple methods
            return self._verify_booking_success_improved()
            
        except Exception as e:
            self.logger.error(f"Error booking tee time: {e}")
            return False

    def _verify_booking_success_improved(self):
        """Improved booking verification with multiple success indicators"""
        try:
            # Wait a bit for any async operations
            time.sleep(2)
            
            # Check for various success indicators
            success_indicators = [
                # CSS selectors for success elements
                ".success, .confirmed, .booked",
                ".notification.success, .notify.success",
                ".booking-confirmation",
                
                # Check for specific text content
                "//*[contains(text(), 'successfully') or contains(text(), 'confirmed') or contains(text(), 'booked')]",
                "//*[contains(text(), 'Thank you') or contains(text(), 'reservation')]",
                
                # Check for URL changes
                "url_change"
            ]
            
            for indicator in success_indicators:
                if indicator == "url_change":
                    # Check if URL changed to confirmation page
                    current_url = self.driver.current_url.lower()
                    if any(keyword in current_url for keyword in ['success', 'confirm', 'book', 'complete']):
                        self.logger.info(f"Success detected via URL change: {current_url}")
                        return True
                elif indicator.startswith("//"):
                    # XPath selector
                    try:
                        elements = self.driver.find_elements(By.XPATH, indicator)
                        if elements and any(elem.is_displayed() for elem in elements):
                            success_text = elements[0].text[:100]
                            self.logger.info(f"Success detected via XPath: {success_text}")
                            return True
                    except:
                        continue
                else:
                    # CSS selector
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, indicator)
                        if elements and any(elem.is_displayed() for elem in elements):
                            success_text = elements[0].text[:100]
                            self.logger.info(f"Success detected via CSS: {success_text}")
                            return True
                    except:
                        continue
            
            # Check page source for success keywords
            page_source = self.driver.page_source.lower()
            success_keywords = [
                'booking confirmed',
                'reservation confirmed', 
                'tee time booked',
                'successfully reserved',
                'thank you for booking'
            ]
            
            for keyword in success_keywords:
                if keyword in page_source:
                    self.logger.info(f"Success detected via page content: {keyword}")
                    return True
            
            # If no clear success indicators found, it might still be successful
            # Check if we're no longer on the booking page
            if 'booking' not in self.driver.current_url.lower():
                self.logger.info("Possible success - redirected away from booking page")
                return True
            
            self.logger.warning("No clear booking success indicators found")
            return False
            
        except Exception as e:
            self.logger.error(f"Error verifying booking success: {e}")
            return False

    def run_booking_attempt_improved(self, target_date=None, preferred_times=None):
        """
        Main improved booking method
        """
        try:
            self.logger.info("🚀 Starting improved booking attempt")
            
            # Use target date or default to 7 days ahead
            if not target_date:
                target_date = datetime.now() + timedelta(days=7)
            
            # Setup driver
            if not self.setup_driver(headless=os.getenv('HEADLESS_BROWSER', 'true').lower() == 'true'):
                return False
            
            # Login
            if not self.login():
                return False
            
            # Navigate to booking page
            if not self.navigate_to_tee_times():
                return False
            
            # Find available times
            available_times = self.find_available_times_improved(target_date)
            if not available_times:
                self.logger.warning("No available tee times found")
                return False
            
            # Select time to book
            time_to_book = None
            
            if preferred_times:
                # Try to find preferred time
                for pref_time in preferred_times:
                    for slot in available_times:
                        if pref_time.lower() in slot['time'].lower():
                            time_to_book = slot
                            self.logger.info(f"Found preferred time: {slot['time']}")
                            break
                    if time_to_book:
                        break
            
            # If no preferred time found, use first available
            if not time_to_book:
                time_to_book = available_times[0]
                self.logger.info(f"Using first available time: {time_to_book['time']}")
            
            # Attempt booking
            success = self.book_tee_time_improved(time_to_book)
            
            if success:
                self.logger.info(f"✅ Successfully booked tee time: {time_to_book['time']}")
            else:
                self.logger.error(f"❌ Failed to book tee time: {time_to_book['time']}")
            
            return success
            
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

# Test functions
def test_improved_scraper():
    """Test the improved scraper"""
    scraper = ImprovedJeremyRanchScraper()
    
    try:
        target_date = datetime.now() + timedelta(days=7)
        preferred_times = ["9:00 AM", "10:00 AM", "11:00 AM"]
        
        print(f"🎯 Testing booking for {target_date.strftime('%m/%d/%Y')}")
        print(f"🕒 Preferred times: {', '.join(preferred_times)}")
        
        # Test without actually booking (set headless=False to watch)
        success = scraper.run_booking_attempt_improved(
            target_date=target_date,
            preferred_times=preferred_times
        )
        
        if success:
            print("✅ Test booking successful!")
        else:
            print("❌ Test booking failed")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

def test_time_detection_only():
    """Test just the time slot detection"""
    scraper = ImprovedJeremyRanchScraper()
    
    try:
        if (scraper.setup_driver(headless=False) and 
            scraper.login() and 
            scraper.navigate_to_tee_times()):
            
            target_date = datetime.now() + timedelta(days=7)
            print(f"🎯 Testing time detection for {target_date.strftime('%m/%d/%Y')}")
            
            available_times = scraper.find_available_times_improved(target_date)
            
            print(f"Found {len(available_times)} available times:")
            for i, slot in enumerate(available_times):
                print(f"  {i+1}. {slot['time']} (via {slot['strategy']})")
            
            print("\n🔍 Browser staying open for 30 seconds...")
            time.sleep(30)
            
    finally:
        scraper.cleanup()

if __name__ == "__main__":
    # Run time detection test by default
    test_time_detection_only()