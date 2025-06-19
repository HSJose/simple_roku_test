from appium import webdriver
from selenium.common.exceptions import WebDriverException
from appium.options.common import AppiumOptions
from appium.webdriver.common.appiumby import AppiumBy

from dotenv import load_dotenv
from rich import print
from os import getenv
from time import sleep


# Load environment variables
load_dotenv()
api_key = getenv('HEADSPIN_API_TOKEN')
app_id = getenv('APP_ID')
udid = getenv('UDID')
driver = None

print(app_id)
print(udid)

# Appium Load Balancer Endpoint
alb_wd = f'https://appium-dev.headspin.io:443/v0/{api_key}/wd/hub'

# Set desired capabilities
capabilities = {
    'platformName': 'roku',
    'appium:automationName': 'roku',
    'appium:deviceName': 'roku',
    'headspin:app.id': app_id,
    'appium:udid': udid,
}

# convert capabilities to AppiumOptions
appium_options = AppiumOptions().load_capabilities(capabilities)
appium_options.set_capability('appium:newCommandTimeout', 300)
appium_options.set_capability('headspin:controlLock', True)
appium_options.set_capability('headspin:retryNewSessionFailure', False)

def start_appium_session() -> object:
    '''
    Start an appium session with the desired capabilities
    '''
    driver = None
    try:
        driver = webdriver.Remote(
            command_executor=alb_wd,
            options=appium_options,
        )

        driver.implicitly_wait(30)

        session_id = driver.session_id
        print(f"Appium session started with session id: {session_id}")
    except Exception as e:
        print(f"Error starting appium session: {e}")
    
    return driver


def press_key(driver, key: str) -> bool:
    '''
    Press a key on the Roku device
    '''

    ALLOWED_KEYS = (
        "Home",
        "Rev",
        "Fwd",
        "Play",
        "Select",
        "Left",
        "Right",
        "Down",
        "Up",
        "Back",
        "InstantReplay",
        "Info",
        "Backspace",
        "Search",
        "Enter",
    )

    normalized_key = key[0].upper() + key[1:]
    if normalized_key not in ALLOWED_KEYS:
        raise ValueError(f"Invalid key: '{normalized_key}'. Must be one of: {', '.join(ALLOWED_KEYS)}")
    
    try:
        driver.execute_script('roku: pressKey', {'key': normalized_key})
        print(f"Pressed key: {normalized_key}")
        sleep(1)
        return True
    except Exception as e:
        print(f"Error pressing key '{normalized_key}': {e}")
        return False

def current_focus(driver) -> str:
    '''
    Get the current focus element on the Roku device
    '''
    try:
        focused_element = driver.find_element(AppiumBy.XPATH, "//*[@focused='true']")
        print(f"Attributes: {focused_element.get_attribute('text') if focused_element.get_attribute('text') else focused_element.get_attribute('name')}")
        return focused_element
    except Exception as e:
        print(f"Error getting current focus: {e}")
        return None

def try_send_keys_with_xpath_navigation(driver, base_xpath, text, max_up=2, max_down=2):
    """
    Attempts to send keys to a focusable node near base_xpath using parent/child navigation.

    :param driver: The Appium driver
    :param base_xpath: The XPath to the initially targeted element
    :param text: The text to send
    :param max_up: Max levels to walk up the DOM tree
    :param max_down: Max number of children to try per parent
    :return: True if successful, False otherwise
    """

    def is_focusable(el):
        try:
            return el.get_attribute("focusable") == "true"
        except Exception:
            return False

    def try_send_keys(el, xpath):
        try:
            if is_focusable(el):
                el.send_keys(text)
                print(f"✅ Success: Sent text to element at XPath: {xpath}")
                return True
            else:
                print(f"⚠️ Skipped non-focusable element at XPath: {xpath}")
                return False
        except WebDriverException as e:
            print(f"❌ Failed to send keys to {xpath}: {e.msg}")
            return False

    # Try original XPath
    try:
        el = driver.find_element(AppiumBy.XPATH, base_xpath)
        if try_send_keys(el, base_xpath):
            return True
    except WebDriverException as e:
        print(f"❌ Failed to find original element at {base_xpath}: {e.msg}")

    # Walk up the DOM and try each parent
    parent_xpath = base_xpath
    for i in range(1, max_up + 1):
        parent_xpath += "/parent::node()"
        try:
            el = driver.find_element(AppiumBy.XPATH, parent_xpath)
            print(f"🔼 Trying parent level {i}: {parent_xpath}")
            if try_send_keys(el, parent_xpath):
                return True
        except WebDriverException as e:
            print(f"❌ Failed to get parent at level {i}: {e.msg}")
            break

    # Try children of each parent
    current_parent_xpath = base_xpath
    for i in range(1, max_up + 1):
        current_parent_xpath += "/parent::node()"
        for j in range(1, max_down + 1):
            child_xpath = f"{current_parent_xpath}/*[{j}]"
            try:
                el = driver.find_element(AppiumBy.XPATH, child_xpath)
                print(f"🔽 Trying child {j} of parent level {i}: {child_xpath}")
                if try_send_keys(el, child_xpath):
                    return True
            except WebDriverException as e:
                print(f"❌ Could not access child {j} of parent level {i}: {e.msg}")
                continue

    print("❗ Unable to find focusable element to send keys.")
    return False

def main():
    driver = None
    try:
        driver = start_appium_session()

        sleep(5)
    
        '''
        -- start appium session
        -- define the flow of automation:
        -- find the settings
        0196cd0b-b2b7-7331-9d8b-9a965d7d4fb7
        -- enter the settings
        -- interact CDN location
        the cdn value may need to have us enter the input dialog screen

        

        --- need to check app got "missing nmandatory fields error"
        -- interact domain id
        -- interact language
        -- interact download
        -- new elemnet will show verify element
        -- validate additional elements
        -- there are 4 pages that require simlar validation
        ---- construct for first page 'banner element allow all'
        -- this will trigger an external check

        -- add video capture
        -- add any other run modes or telemetry
        '''
        
        # step 1: naviagte to settings
        press_key(driver, 'Up')
        press_key(driver, 'Right')
        press_key(driver, 'Right')
        press_key(driver, 'Select')

        # step 2: navigate to the 4 required fields enter required data
        '''
        CDN : qa
        Domain ID: 0196cd0b-b2b7-7331-9d8b-9a965d7d4fb7
        Language: en
        SDK Version: latest
        '''
        
        press_key(driver, 'Select')
        sleep(1)
        text_box = "//VoiceTextEditBox"
        

        try_send_keys_with_xpath_navigation(
            driver,
            text_box,
            text="qa",
            max_up=2,
            max_down=3
        )
        
        press_key(driver, 'Down')
        press_key(driver, 'Select')

        try_send_keys_with_xpath_navigation(
            driver,
            text_box,
            text="0196cd0b-b2b7-7331-9d8b-9a965d7d4fb7",
            max_up=2,
            max_down=3
        )

        press_key(driver, 'Down')
        press_key(driver, 'Select')

        try_send_keys_with_xpath_navigation(
            driver,
            text_box,
            text="en",
            max_up=2,
            max_down=3
        )

        press_key(driver, 'Down')
        press_key(driver, 'Select')

        try_send_keys_with_xpath_navigation(
            driver,
            text_box,
            text="latest",
            max_up=2,
            max_down=3
        )

        # step 3: navigate to the download button


        sleep(30)

    except ValueError as VE:
        print(f"ValueError: {VE}")
        print("Please be sure to consult with the roku driver documention for valid remote key values")

    except Exception as E:
        print(f"error: {E}")

    finally:
        if driver:
            driver.quit()


if __name__ == '__main__':
    main()

