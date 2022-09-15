from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import ElementNotVisibleException, ElementNotSelectableException, NoSuchElementException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from seleniumwire import webdriver  
import uuid
import base64
import zlib
from datetime import datetime
import urllib
import time
import getpass
import xml.etree.ElementTree
import os

class AzureAdUnknownResponse(Exception):
    pass

class AzureAdCredentialError(Exception):
    pass

def create_login_url(app_id, tenant_id):
    guid = uuid.uuid4()

    saml_request = f'''
<samlp:AuthnRequest xmlns="urn:oasis:names:tc:SAML:2.0:metadata" ID="id{guid}" Version="2.0" IssueInstant="{datetime.now().isoformat()}Z" IsPassive="false" AssertionConsumerServiceURL="https://signin.aws.amazon.com/saml" xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol">
    <Issuer xmlns="urn:oasis:names:tc:SAML:2.0:assertion">{app_id}</Issuer>
    <samlp:NameIDPolicy Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"></samlp:NameIDPolicy>
</samlp:AuthnRequest>
    '''

    compress = zlib.compressobj(zlib.Z_DEFAULT_COMPRESSION, zlib.DEFLATED, -15, memLevel=8, strategy=zlib.Z_DEFAULT_STRATEGY)

    data = compress.compress(saml_request.encode())
    data += compress.flush()

    encoded = base64.b64encode(data).decode('utf-8')

    return f'https://login.microsoftonline.com/{tenant_id}/saml2?SAMLRequest={urllib.parse.quote(encoded)}'

def _req_interceptor(request):
    if request.url == 'https://signin.aws.amazon.com/saml':
        global roles
        roles = _get_roles(request.body)

def _load_login(url):
    options = Options()
    options.headless = bool(int(os.environ.get('AUTHER_HEADLESS', 1)))
    options.add_argument('--auth-server-whitelist="_"')
    options.add_argument('--auth-negotiate-delegate-whitelist="_"')

    chromium_exe = os.environ.get('AUTHER_CHROME_BIN', ChromeDriverManager().install())

    service = Service(executable_path=chromium_exe)
    driver = webdriver.Chrome(service=service, options=options)
    driver.scopes = [
        '.*signin.aws.amazon.com.*',
    ]
    driver.request_interceptor = _req_interceptor

    wait = WebDriverWait(driver, timeout=3, poll_frequency=0.25, ignored_exceptions=[ElementNotVisibleException, ElementNotSelectableException, NoSuchElementException, TimeoutException])

    driver.get(url)

    return driver, wait

def _input_username(driver, wait, username):
    while True:
        input_selector = driver.find_element(by=By.NAME, value='loginfmt')
        submit_selector = driver.find_element(by=By.CSS_SELECTOR, value='input[type="submit"][value="Next"]')

        while username in [None, ""]:
            username = input("Username: ")

        input_selector.clear()
        input_selector.send_keys(username)
        submit_selector.click()

        while True:
            try:
                if wait.until(EC.presence_of_element_located((By.ID, "usernameError"))):
                    username = None
                    print("Unknown username, try again")
                    break
            except:
                pass
            
            try:
                if wait.until(EC.none_of(EC.visibility_of_element_located((By.NAME, "loginfmt")))):
                    return
            except:
                pass

            # wait for one of the above to appear
            time.sleep(0.25)


def _input_password(driver, wait, password):
    while True:
        input_selector = driver.find_element(by=By.NAME, value='passwd') or driver.find_element(by=By.NAME, value='Password')
        submit_selector = driver.find_element(by=By.CSS_SELECTOR, value='input[type="submit"][value="Sign in"]') or driver.find_element(by=By.CSS_SELECTOR, value='span[class=submit]')

        while password in [None, ""]:
            password = getpass.getpass("Password: ")

        input_selector.clear()
        input_selector.send_keys(password)
        submit_selector.click()

        while True:
            try:
                if wait.until(EC.presence_of_element_located((By.ID, "passwordError"))):
                    password = None
                    print("Incorrect password, try again")
                    break
            except:
                pass

            try:
                if wait.until(EC.none_of(EC.visibility_of_element_located((By.NAME, "passwd")), EC.visibility_of_element_located((By.NAME, "Password")))):
                    return
            except:
                pass

            # wait for one of the above to appear
            time.sleep(0.25)

def _input_code(driver, wait, code):
    while True:
        input_selector = driver.find_element(by=By.NAME, value='otc')
        submit_selector = driver.find_element(by=By.CSS_SELECTOR, value='input[type="submit"][value="Verify"]')

        while code is None:
            code = input("One-time code: ")

        input_selector.clear()
        input_selector.send_keys(code)
        submit_selector.click()

        while True:
            try:
                if wait.until(EC.presence_of_element_located((By.ID, "idSpan_SAOTCC_Error_OTC"))):
                    code = None
                    print("Incorrect code, try again")
                    break
            except:
                pass

            try:
                if wait.until(EC.none_of(EC.visibility_of_element_located((By.NAME, "otc")))):
                    return
            except:
                pass
            
            # wait for one of the above to appear
            time.sleep(0.25)

def _input_stay_signed_in(driver, stay_signed_in=False):
    if stay_signed_in:
        DontShowAgain = driver.find_element(by=By.CSS_SELECTOR, value='input[type="checkbox"][name="DontShowAgain"]')
        submit = driver.find_element(by=By.CSS_SELECTOR, value='input[type="submit"][value="Yes"]')
        DontShowAgain.click()
        submit.click()
        return
    else:
        submit = driver.find_element(by=By.CSS_SELECTOR, value='input[type="button"][value="No"]')
        submit.click()
        return

def _get_roles(encoded_xml):
    saml_roles = []

    assertion_encoded = urllib.parse.unquote(encoded_xml).split('=', 1)[1]

    assertion = base64.b64decode(assertion_encoded).decode('UTF-8')

    assertion_xml = xml.etree.ElementTree.fromstring(assertion)
    for saml2attribute in assertion_xml.iter(
        "{urn:oasis:names:tc:SAML:2.0:assertion}Attribute"
    ):
        if saml2attribute.get("Name") == "https://aws.amazon.com/SAML/Attributes/Role":
            for saml2attributevalue in saml2attribute.iter(
                "{urn:oasis:names:tc:SAML:2.0:assertion}AttributeValue"
            ):
                role = saml2attributevalue.text
                role_parts = role.split(",")
                if "saml-provider" in role_parts[0]:
                    principal_arn = role_parts[0]
                    role_arn = role_parts[1]
                else:
                    role_arn = role_parts[0]
                    principal_arn = role_parts[1]
                saml_roles.append((assertion_encoded, role_arn, principal_arn))
    return saml_roles

def _auth(url, username=None, password=None, stay_signed_in=False):
    driver, wait =  _load_login(url)

    global roles
    roles = []

    before = datetime.now()
    during = datetime.now()

    found = []

    while not roles:
        time_diff = (during-before).seconds
        if (time_diff >= 60):
            raise Exception('hit timeout')

        try:
            try:
                if 'loginfmt' not in found and wait.until(EC.visibility_of_element_located((By.NAME, "loginfmt"))):
                    _input_username(driver, wait, username)
                    found.append('loginfmt')
            except:
                pass

            try:
                if 'passwd' not in found and wait.until(EC.any_of(EC.visibility_of_element_located((By.NAME, "passwd")), EC.visibility_of_element_located((By.NAME, "Password")))):
                    _input_password(driver, wait, password)
                    found.append('passwd')
            except:
                pass

            try:
                if 'notify' not in found and 'otc' not in found and wait.until(EC.visibility_of_element_located((By.ID, "idDiv_SAOTCAS_Title"))):
                    print('MFA notification sent, approve on your device.')
                    found.append('notify')
            except:
                pass

            try:
                if 'otc' not in found and 'notify' not in found and wait.until(EC.visibility_of_element_located((By.NAME, "otc"))):
                    _input_code(driver, wait, None)
                    found.append('otc')
            except:
                pass

            try:
                if 'DontShowAgain' not in found and wait.until(EC.visibility_of_element_located((By.NAME, "DontShowAgain"))):
                    _input_stay_signed_in(driver, stay_signed_in)
                    found.append('DontShowAgain')
            except:
                pass

            try:
                if wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'div[data-bind="text: unsafe_exceptionMessage"]'))):
                    print(
                        'Something went wrong - set "headless=False" in the do_login method and try again to debug.'
                    )
                    driver.quit()
                    break

                during = datetime.now()
            except:
                pass
        except KeyboardInterrupt:
            driver.quit()
            break
        except:
            print('in except, found nothing')
            during = datetime.now()

    if roles:
        return roles
    else:
        raise AzureAdUnknownResponse('No roles found')

def do_login(
    url,
    username=None,
    password=None,
    stay_signed_in=False):
    return _auth(
        url,
        username=username,
        password=password,
        stay_signed_in=stay_signed_in,
    )