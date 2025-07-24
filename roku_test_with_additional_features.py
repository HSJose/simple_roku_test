import httpx
from appium import webdriver
from appium.options.common import AppiumOptions
from appium.webdriver.common.appiumby import AppiumBy
from dotenv import load_dotenv
from rich import print
from selenium.common.exceptions import WebDriverException, NoSuchElementException
from os import getenv
from time import sleep, time

# --- Configuration ---
# Load environment variables from .env file
load_dotenv()

CONFIG = {
    "HEADSPIN_API_TOKEN": getenv('HEADSPIN_API_TOKEN'),
    "APP_ID": getenv('APP_ID'),
    "UDID": getenv('UDID'),
    "HEADSPIN_API_BASE": "https://api-dev.headspin.io/v0"
}
CONFIG["APPIUM_URL"] = f"https://appium-dev.headspin.io:443/v0/{CONFIG['HEADSPIN_API_TOKEN']}/wd/hub"

# --- Appium Session Management ---

class AppiumDriverContext:
    """A context manager for safely setting up and tearing down the Appium driver."""
    def __init__(self, command_executor, options):
        self.command_executor = command_executor
        self.options = options
        self.driver = None
        self.session_id = None

    def __enter__(self):
        try:
            print("Attempting to start Appium session...")
            self.driver = webdriver.Remote(
                command_executor=self.command_executor,
                options=self.options
            )
            self.driver.implicitly_wait(30)
            self.session_id = self.driver.session_id
            print(f"✅ Appium session started successfully with Session ID: {self.session_id}")
            return self.driver
        except WebDriverException as e:
            print(f"❌ Error starting Appium session: {e}")
            raise  # Re-raise the exception to be caught by the main try/except block

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            print(f"Ending Appium session: {self.session_id}")
            print(f"🔗 View session at: https://ui-dev.headspin.io/sessions/{self.session_id}/waterfall")
            self.driver.quit()
        if exc_type:
            print(f"Session ended due to an exception: {exc_val}")

# --- Helper Functions ---

def send_headspin_label(session_id: str, name: str, start_time: float, end_time: float):
    """Sends a custom label to the Headspin session for performance tracking."""
    url = f"{CONFIG['HEADSPIN_API_BASE']}/sessions/{session_id}/label/add"
    headers = {"Authorization": f"Bearer {CONFIG['HEADSPIN_API_TOKEN']}"}
    json_data = {
        "label_type": "user",
        "name": name,
        "ts_start": start_time,
        "ts_end": end_time,
    }
    try:
        with httpx.Client(headers=headers) as client:
            response = client.post(url, json=json_data)
            response.raise_for_status()
            print(f"✅ Successfully added label: '{name}'")
    except httpx.HTTPStatusError as e:
        print(f"⚠️ HTTP error while sending label: {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e:
        print(f"⚠️ Request error while sending label: {e}")


def press_key(driver: webdriver.Remote, key: str) -> bool:
    """Presses a specified key on the Roku device."""
    ALLOWED_KEYS = (
        "Home", "Rev", "Fwd", "Play", "Select", "Left", "Right", "Down", "Up",
        "Back", "InstantReplay", "Info", "Backspace", "Search", "Enter",
    )
    normalized_key = key.capitalize()
    if normalized_key not in ALLOWED_KEYS:
        raise ValueError(f"Invalid key: '{key}'. Must be one of: {', '.join(ALLOWED_KEYS)}")
    
    try:
        driver.execute_script('roku: pressKey', {'key': normalized_key})
        print(f"Pressed key: {normalized_key}")
        sleep(1)  # A brief pause after a key press is often necessary for UI to update
        return True
    except WebDriverException as e:
        print(f"❌ Error pressing key '{normalized_key}': {e}")
        return False


def try_send_keys_with_xpath_navigation(driver: webdriver.Remote, base_xpath: str, text: str, max_up: int = 2, max_down: int = 3) -> bool:
    """Attempts to send keys to a focusable element near the base_xpath by navigating the DOM."""
    
    def is_focusable(el) -> bool:
        try:
            return el.get_attribute("focusable") == "true"
        except WebDriverException:
            return False

    def try_send_to_element(el, xpath_for_logging: str) -> bool:
        try:
            if is_focusable(el):
                el.send_keys(text)
                print(f"✅ Success: Sent text to element at XPath: {xpath_for_logging}")
                return True
            print(f"⚠️ Skipped non-focusable element at XPath: {xpath_for_logging}")
            return False
        except WebDriverException as e:
            print(f"❌ Failed to send keys to {xpath_for_logging}: {e.msg}")
            return False

    # A set to keep track of tried XPaths to avoid redundant attempts
    tried_xpaths = set()

    def find_and_send(xpath: str) -> bool:
        if xpath in tried_xpaths:
            return False
        tried_xpaths.add(xpath)
        try:
            el = driver.find_element(AppiumBy.XPATH, xpath)
            print(f"🔎 Trying element at XPath: {xpath}")
            return try_send_to_element(el, xpath)
        except NoSuchElementException:
            return False

    # Start with the base XPath
    if find_and_send(base_xpath):
        return True

    # Walk up the DOM and try parents and their children
    current_parent_xpath = base_xpath
    for i in range(1, max_up + 1):
        current_parent_xpath = f"({current_parent_xpath})/parent::*"
        if find_and_send(current_parent_xpath):
            return True
        
        # Try children of the current parent
        for j in range(1, max_down + 1):
            child_xpath = f"{current_parent_xpath}/*[{j}]"
            if find_and_send(child_xpath):
                return True

    print(f"❗ Unable to find a focusable element near {base_xpath} to send keys.")
    return False


def fill_input_field(driver: webdriver.Remote, xpath: str, text: str):
    """Helper to select a field, enter text, and move to the next field."""
    press_key(driver, 'Select')
    sleep(1)  # Wait for keyboard or input dialog
    try_send_keys_with_xpath_navigation(driver, xpath, text)
    press_key(driver, 'Down')


def main():
    """Main execution block for the Roku automation script."""
    if not all([CONFIG["HEADSPIN_API_TOKEN"], CONFIG["APP_ID"], CONFIG["UDID"]]):
        print("❌ Critical Error: Environment variables HEADSPIN_API_TOKEN, APP_ID, or UDID are not set.")
        return

    # Define Appium capabilities using the config
    capabilities = {
        'platformName': 'roku',
        'appium:automationName': 'roku',
        'appium:deviceName': 'roku',
        'headspin:app.id': CONFIG["APP_ID"],
        'appium:udid': CONFIG["UDID"],
        'headspin:capture': True,
        'appium:newCommandTimeout': 300,
        'headspin:controlLock': True,
        'headspin:retryNewSessionFailure': False
    }
    appium_options = AppiumOptions().load_capabilities(capabilities)

    try:
        with AppiumDriverContext(CONFIG["APPIUM_URL"], appium_options) as driver:
            session_id = driver.session_id
            sleep(5) # Initial wait for the app to load completely

            # --- Step 1: Navigate to Settings ---
            print("\n--- Step 1: Navigating to Settings ---")
            step_1_start = time()
            press_key(driver, 'Up')
            press_key(driver, 'Right')
            press_key(driver, 'Right')
            press_key(driver, 'Select')
            step_1_end = time()
            send_headspin_label(session_id, "Step 1: Navigate to Settings", step_1_start, step_1_end)

            # --- Step 2: Fill Required Fields ---
            print("\n--- Step 2: Filling in required fields ---")
            step_2_start = time()
            fields_to_fill = {
                "qa": "//VoiceTextEditBox",
                "0196cd0b-b2b7-7331-9d8b-9a965d7d4fb7": "//VoiceTextEditBox",
                "en": "//VoiceTextEditBox",
                "latest": "//VoiceTextEditBox",
            }
            
            for text, xpath in fields_to_fill.items():
                print(f"\nFilling field with: '{text}'")
                fill_input_field(driver, xpath, text)
                sleep(1) # Pause between filling fields
            
            step_2_end = time()
            send_headspin_label(session_id, "Step 2: Fill All Required Fields", step_2_start, step_2_end)


            # --- Step 3: Navigate to Download ---
            print("\n--- Step 3: Navigating to Download button ---")
          
            
            print("\nAutomation flow complete. Waiting before exit...")
            sleep(10)

    except (WebDriverException, ValueError) as e:
        print(f"❌ An unrecoverable error occurred during the automation: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == '__main__':
    main()
