# src/debug_time_slots.py
"""
Jeremy Ranch Golf Club - Time Slot Detection Debugger
This script helps identify the correct HTML selectors for time slot booking
"""

import os
import time
import json
import pytz
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging

class JeremyRanchTimeSlotDebugger:
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

    def setup_driver(self, headless=False):
        """Initialize Chrome WebDriver - use headless=False for debugging"""
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
        """Login to Jeremy Ranch website"""
        try:
            self.logger.info("Logging in...")
            self.driver.get(self.login_url)
            time.sleep(2)
            
            # Fill login form
            username_field = self.wait.until(
                EC.presence_of_element_located((By.ID, self.username_field_id))
            )
            username_field.clear()
            username_field.send_keys(self.username)
            
            password_field = self.driver.find_element(By.ID, self.password_field_id)
            password_field.clear()
            password_field.send_keys(self.password)
            
            login_button = self.driver.find_element(By.ID, self.login_button_id)
            login_button.click()
            
            time.sleep(3)
            return "login" not in self.driver.current_url.lower()
            
        except Exception as e:
            self.logger.error(f"Login error: {e}")
            return False

    def navigate_to_tee_times(self):
        """Navigate to tee time booking page"""
        try:
            # Try direct URL first
            booking_url = "https://www.thejeremy.com/Default.aspx?p=dynamicmodule&pageid=397060&tt=booking&ssid=319820&vnf=1"
            self.driver.get(booking_url)
            time.sleep(5)
            
            # Check if we have the date input field
            try:
                date_input = self.driver.find_element(By.ID, "txtDate")
                self.logger.info("Successfully navigated to tee time booking page")
                return True
            except NoSuchElementException:
                self.logger.error("Could not find date input field")
                return False
                
        except Exception as e:
            self.logger.error(f"Navigation error: {e}")
            return False

    def set_target_date(self, days_ahead=7):
        """Set the date to X days from now"""
        try:
            timezone_mtn = pytz.timezone('MST')
            target_date = datetime.now(timezone_mtn) + timedelta(days=days_ahead)
            target_date_str = target_date.strftime('%m/%d/%Y')
            
            self.logger.info(f"Setting date to: {target_date_str}")
            
            date_input = self.driver.find_element(By.ID, "txtDate")
            current_date = date_input.get_attribute('value')
            self.logger.info(f"Current date in field: {current_date}")
            
            date_input.clear()
            date_input.send_keys(target_date_str)
            
            # Trigger the date update
            self.driver.execute_script("updatePersistDate(document.getElementById('txtDate'))")
            self.logger.info("Triggered date update script")
            
            time.sleep(5)  # Wait for time slots to load
            
            # Verify date was set
            new_date = date_input.get_attribute('value')
            self.logger.info(f"Date after update: {new_date}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Date setting error: {e}")
            return False

    def analyze_page_structure(self):
        """Comprehensive analysis of the tee time booking page structure"""
        print("\n" + "="*80)
        print("🔍 JEREMY RANCH TEE TIME PAGE STRUCTURE ANALYSIS")
        print("="*80)
        
        analysis_results = {}
        
        # 1. Basic page info
        print(f"\n📍 Current URL: {self.driver.current_url}")
        print(f"📍 Page Title: {self.driver.title}")
        
        # 2. Look for time-related elements
        print(f"\n⏰ SEARCHING FOR TIME-RELATED ELEMENTS:")
        
        time_related_selectors = [
            ("Elements with 'AM' in ID", "div[id*='AM'], span[id*='AM'], button[id*='AM']"),
            ("Elements with 'PM' in ID", "div[id*='PM'], span[id*='PM'], button[id*='PM']"),
            ("Elements with 'time' in class", "[class*='time']"),
            ("Elements with 'slot' in class", "[class*='slot']"),
            ("Elements with 'available' in class", "[class*='available']"),
            ("Elements with 'open' in class", "[class*='open']"),
            ("Elements with 'book' in class", "[class*='book']"),
            ("All buttons", "button"),
            ("All clickable inputs", "input[type='button'], input[type='submit']"),
            ("All links with onclick", "a[onclick]"),
            ("Divs with onclick", "div[onclick]"),
            ("Table cells", "td"),
        ]
        
        for description, selector in time_related_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                print(f"   {description}: {len(elements)} found")
                analysis_results[description] = len(elements)
                
                # Show first few elements if any found
                if elements and len(elements) > 0:
                    for i, elem in enumerate(elements[:3]):
                        try:
                            text = elem.text.strip()[:50]
                            tag = elem.tag_name
                            elem_id = elem.get_attribute('id')
                            classes = elem.get_attribute('class')
                            onclick = elem.get_attribute('onclick')
                            
                            print(f"      #{i+1}: <{tag}> id='{elem_id}' class='{classes}'")
                            if text:
                                print(f"           Text: '{text}'")
                            if onclick:
                                print(f"           OnClick: '{onclick[:50]}...'")
                        except:
                            print(f"      #{i+1}: <{tag}> (could not extract details)")
                    if len(elements) > 3:
                        print(f"      ... and {len(elements) - 3} more")
                    print()
            except Exception as e:
                print(f"   {description}: Error - {e}")

        # 3. Look for specific time patterns
        print(f"\n🕒 SEARCHING FOR TIME PATTERNS:")
        
        # Search for text that looks like times
        page_source = self.driver.page_source
        import re
        
        time_patterns = [
            (r'\b\d{1,2}:\d{2}\s*AM\b', "Format: 9:00 AM"),
            (r'\b\d{1,2}:\d{2}\s*PM\b', "Format: 9:00 PM"),
            (r'\b\d{1,2}:\d{2}\b', "Format: 9:00"),
            (r'\b\d{1,2}\s*AM\b', "Format: 9 AM"),
            (r'\b\d{1,2}\s*PM\b', "Format: 9 PM"),
        ]
        
        for pattern, description in time_patterns:
            matches = re.findall(pattern, page_source, re.IGNORECASE)
            unique_matches = list(set(matches))[:10]  # First 10 unique matches
            print(f"   {description}: {len(matches)} total, {len(set(matches))} unique")
            if unique_matches:
                print(f"      Examples: {', '.join(unique_matches)}")

        # 4. JavaScript function analysis
        print(f"\n🔧 JAVASCRIPT FUNCTIONS ANALYSIS:")
        
        js_functions = [
            "updatePersistDate",
            "bookTeeTime", 
            "selectTime",
            "reserveTime",
            "__doPostBack"
        ]
        
        for func in js_functions:
            try:
                result = self.driver.execute_script(f"return typeof {func}")
                print(f"   {func}: {result}")
                if result == "function":
                    # Try to get function source
                    try:
                        source = self.driver.execute_script(f"return {func}.toString()")
                        print(f"      Source: {source[:100]}...")
                    except:
                        pass
            except:
                print(f"   {func}: not found")

        return analysis_results

    def extract_sample_html(self):
        """Extract sample HTML of potential time slot elements"""
        print(f"\n📝 EXTRACTING SAMPLE HTML:")
        
        # Get elements that might be time slots
        potential_selectors = [
            "div[id*='AM']",
            "div[id*='PM']", 
            "button[onclick]",
            "input[type='button']",
            "[class*='time']",
            "[class*='slot']",
            "[class*='available']",
            "td"
        ]
        
        samples = {}
        
        for selector in potential_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    # Get HTML of first few elements
                    sample_html = []
                    for i, elem in enumerate(elements[:3]):
                        try:
                            html = elem.get_attribute('outerHTML')
                            sample_html.append(html)
                        except:
                            continue
                    
                    if sample_html:
                        samples[selector] = sample_html
                        print(f"\n   📋 Sample HTML for '{selector}':")
                        for i, html in enumerate(sample_html):
                            print(f"      Sample #{i+1}:")
                            print(f"      {html[:200]}...")
                            
            except Exception as e:
                continue
        
        return samples

    def test_clicking_elements(self):
        """Test clicking on potential time slot elements (safe mode - no actual booking)"""
        print(f"\n🖱️  TESTING CLICKABLE ELEMENTS:")
        
        # Find all potentially clickable elements
        clickable_selectors = [
            "button",
            "input[type='button']",
            "a[onclick]",
            "div[onclick]",
            "[class*='book']",
            "[class*='available']"
        ]
        
        for selector in clickable_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                print(f"\n   Testing {selector}: {len(elements)} elements found")
                
                for i, elem in enumerate(elements[:2]):  # Test first 2 only
                    try:
                        if elem.is_displayed() and elem.is_enabled():
                            text = elem.text.strip()[:30]
                            elem_id = elem.get_attribute('id')
                            onclick = elem.get_attribute('onclick')
                            
                            print(f"      Element #{i+1}: id='{elem_id}' text='{text}'")
                            if onclick:
                                print(f"         OnClick: {onclick[:50]}...")
                            
                            # DON'T ACTUALLY CLICK - just report that it's clickable
                            print(f"         Status: Clickable ✓")
                            
                    except Exception as e:
                        print(f"      Element #{i+1}: Error testing - {e}")
                        
            except Exception as e:
                print(f"   Error testing {selector}: {e}")

    def save_debug_results(self, analysis_results, samples):
        """Save debug results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save page source
        try:
            with open(f"/tmp/jeremy_ranch_page_{timestamp}.html", 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print(f"\n💾 Page source saved to: /tmp/jeremy_ranch_page_{timestamp}.html")
        except Exception as e:
            print(f"Error saving page source: {e}")
        
        # Save analysis results
        try:
            with open(f"/tmp/jeremy_ranch_analysis_{timestamp}.json", 'w') as f:
                json.dump({
                    'analysis_results': analysis_results,
                    'url': self.driver.current_url,
                    'title': self.driver.title,
                    'timestamp': timestamp
                }, f, indent=2)
            print(f"💾 Analysis results saved to: /tmp/jeremy_ranch_analysis_{timestamp}.json")
        except Exception as e:
            print(f"Error saving analysis: {e}")
        
        # Save HTML samples
        try:
            with open(f"/tmp/jeremy_ranch_samples_{timestamp}.json", 'w') as f:
                json.dump(samples, f, indent=2)
            print(f"💾 HTML samples saved to: /tmp/jeremy_ranch_samples_{timestamp}.json")
        except Exception as e:
            print(f"Error saving samples: {e}")

    def run_full_debug(self, days_ahead=7):
        """Run complete debugging analysis"""
        try:
            print("🚀 Starting Jeremy Ranch Time Slot Debug Session")
            print(f"Target date: {days_ahead} days from now")
            
            # Setup browser (visible for debugging)
            if not self.setup_driver(headless=False):
                return False
            
            # Login
            if not self.login():
                print("❌ Login failed")
                return False
            print("✅ Login successful")
            
            # Navigate to booking page
            if not self.navigate_to_tee_times():
                print("❌ Navigation failed")
                return False
            print("✅ Navigation successful")
            
            # Set target date
            if not self.set_target_date(days_ahead):
                print("❌ Date setting failed")
                return False
            print("✅ Date setting successful")
            
            # Run analysis
            print(f"\n🔍 Analyzing page structure...")
            analysis_results = self.analyze_page_structure()
            
            print(f"\n📝 Extracting HTML samples...")
            samples = self.extract_sample_html()
            
            print(f"\n🖱️  Testing clickable elements...")
            self.test_clicking_elements()
            
            # Save results
            self.save_debug_results(analysis_results, samples)
            
            print(f"\n✅ Debug session completed!")
            print(f"🔍 Browser will stay open for 60 seconds for manual inspection")
            print(f"    Check VNC viewer at http://localhost:7900 (password: secret)")
            
            time.sleep(60)  # Keep browser open for manual inspection
            
            return True
            
        except Exception as e:
            print(f"❌ Debug session failed: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()

# Helper functions for running specific debug tests

def debug_time_slots():
    """Quick debug of time slot detection"""
    debugger = JeremyRanchTimeSlotDebugger()
    return debugger.run_full_debug(days_ahead=7)

def debug_specific_date(days_ahead):
    """Debug with a specific number of days ahead"""
    debugger = JeremyRanchTimeSlotDebugger()
    return debugger.run_full_debug(days_ahead=days_ahead)

def quick_element_check():
    """Quick check of page elements without full analysis"""
    debugger = JeremyRanchTimeSlotDebugger()
    
    try:
        if (debugger.setup_driver(headless=False) and 
            debugger.login() and 
            debugger.navigate_to_tee_times() and
            debugger.set_target_date(7)):
            
            print("\n🔍 QUICK ELEMENT CHECK:")
            
            # Just check key selectors
            key_selectors = [
                ".openTee",
                "div[id*='AM']", 
                "div[id*='PM']",
                "button[onclick]",
                "[class*='available']"
            ]
            
            for selector in key_selectors:
                elements = debugger.driver.find_elements(By.CSS_SELECTOR, selector)
                print(f"   {selector}: {len(elements)} elements")
                
                if elements:
                    first_elem = elements[0]
                    print(f"      First element: {first_elem.tag_name}")
                    print(f"      Text: '{first_elem.text.strip()[:50]}'")
                    print(f"      HTML: {first_elem.get_attribute('outerHTML')[:100]}...")
            
            time.sleep(30)  # Keep open for inspection
            
    finally:
        if debugger.driver:
            debugger.driver.quit()

if __name__ == "__main__":
    # Run full debug by default
    debug_time_slots()