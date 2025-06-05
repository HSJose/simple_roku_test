from appium import webdriver
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


def press_key(driver, key: str):
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
    except Exception as e:
        print(f"Error pressing key '{normalized_key}': {e}")



def main():
    driver = None
    try:
      driver = start_appium_session()

      sleep(10)



      press_key(driver, 'Up')
      press_key(driver, 'Right')
      press_key(driver, 'Right')
      press_key(driver, 'Select')

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
