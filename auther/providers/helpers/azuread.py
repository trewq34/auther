"""
Original code from David Poirier's aws_azuread_login project (https://github.com/david-poirier/aws_azuread_login) and licensed under Apache-2.0

Modified to work with one or many IAM roles
"""

import uuid
import zlib
import base64
import urllib
import pyppeteer
import asyncio
import getpass
import os
import xml.etree.ElementTree
from datetime import datetime

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

async def _load_login(url):
    launch_options = {"headless": bool(int(os.environ.get('AUTHER_HEADLESS', 1)))}

    chromium_exe = os.environ.get('AUTHER_CHROME_BIN', '')

    browser = await pyppeteer.launch(executablePath=chromium_exe , options=launch_options, args=[
                '--no-sandbox',
                '--single-process',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--no-zygote',
                '--auth-server-whitelist="_"',
                '--auth-negotiate-delegate-whitelist="_"'
            ])
    page = await browser.newPage()
    response = await page.goto(
        url,
        options={
            "waitUntil": ["load", "domcontentloaded", "networkidle0", "networkidle2"]
        },
    )
    if response.status != 200:
        raise AzureAdUnknownResponse(
            f"Invalid status code: {response.status} - check app id and tenant id and try again"
        )
    return browser, page

def samlHandler(request):
    if request.url == 'https://signin.aws.amazon.com/saml':
        global roles
        roles = _get_roles(request.postData)

async def _check_for_visible_element(page, selector):
    try:
        element = await page.J(selector)
        return element and await element.isIntersectingViewport()
    except pyppeteer.errors.NetworkError:
        return False

async def _input_username(page, username):
    input_selector = 'input[type="email"][name="loginfmt"]'
    submit_selector = 'input[type="submit"][value="Next"]'
    error_selector = "#usernameError"

    while True:
        while username in [None, ""]:
            username = input("Username: ")

        await page.type(input_selector, username)
        await page.click(submit_selector)

        while True:
            if not await _check_for_visible_element(page, input_selector):
                return
            elif await _check_for_visible_element(page, error_selector):
                username = None
                await page.evaluate(
                    f"() => document.querySelector('{input_selector}').value = ''"
                )
                print("Unknown username, try again")
                break
            # wait for one of the above to appear
            await asyncio.sleep(0.25)


async def _input_password(page, password):
    input_selector = 'input[type="password"][name="passwd"],input[type="password"][name="Password"]'
    submit_selector = 'input[type="submit"][value="Sign in"],span[class=submit]'
    error_selector = "#passwordError"

    while True:
        while password in [None, ""]:
            password = getpass.getpass("Password: ")

        await page.focus(input_selector)
        await page.keyboard.type(password)
        await page.click(submit_selector)
        await asyncio.sleep(1)

        while True:
            if not await _check_for_visible_element(page, input_selector):
                return
            elif await _check_for_visible_element(page, error_selector):
                password = None
                await page.evaluate(
                    f"() => document.querySelector('{input_selector}').value = ''"
                )
                print("Incorrect password, try again")
                break
            # wait for one of the above to appear
            await asyncio.sleep(0.25)

async def _input_code(page, code):
    input_selector = 'input[name="otc"]'
    submit_selector = 'input[type="submit"][value="Verify"]'
    error_selector = "#idSpan_SAOTCC_Error_OTC"

    while True:
        while code is None:
            code = input("One-time code: ")

        await page.type(input_selector, code)
        await page.click(submit_selector)

        while True:
            if not await _check_for_visible_element(page, input_selector):
                return
            elif await _check_for_visible_element(page, error_selector):
                code = None
                await page.evaluate(
                    f"() => document.querySelector('{input_selector}').value = ''"
                )
                print("Incorrect code, try again")
                break
            # wait for one of the above to appear
            await asyncio.sleep(0.25)

async def _input_stay_signed_in(page, stay_signed_in):
    if stay_signed_in:
        await page.click('input[type="checkbox"][name="DontShowAgain"]')
        await page.click('input[type="submit"][value="Yes"]')
    else:
        await page.click('input[type="button"][value="No"]')

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

async def _auth(url, username=None, password=None, stay_signed_in=False):
    browser, page = await _load_login(url)

    global roles
    roles = []

    before = datetime.now()
    during = datetime.now()

    while not roles:
        time_diff = (during-before).seconds
        if (time_diff >= 60):
            try:
                await page.screenshot({'path': '/root/.aws/timeout.png'})
            except:
                await page.screenshot({'path': 'timeout.png'})
            raise Exception('hit timeout')

        page.on("request", samlHandler)

        if await _check_for_visible_element(
            page, 'input[type="email"][name="loginfmt"]'
        ):
            await _input_username(page, username)
        elif await _check_for_visible_element(
            page, 'input[type="password"][name="passwd"]'
        ):
            await _input_password(page, password)
        elif await _check_for_visible_element(
            page, 'input[type="password"][name="Password"]'
        ):
            await _input_password(page, password)
        elif await _check_for_visible_element(page, 'input[name="otc"]'):
            await _input_code(page, None)
        elif await _check_for_visible_element(
            page, 'input[type="checkbox"][name="DontShowAgain"]'
        ):
            await _input_stay_signed_in(page, stay_signed_in)
        elif await _check_for_visible_element(
            page, 'div[data-bind="text: unsafe_exceptionMessage"]'
        ):
            try:
                await page.screenshot({'path': '/root/.aws/failure.png'})
            except:
                await page.screenshot({'path': 'failure.png'})
            print(
                'Something went wrong - set env var "AUTHER_HEADLESS" to 1 and try again to debug.'
            )
            await browser.close()
            break
        else:
            # wait for a known option to appear
            await asyncio.sleep(0.25)
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
    return asyncio.get_event_loop().run_until_complete(
        _auth(
            url,
            username=username,
            password=password,
            stay_signed_in=stay_signed_in,
        )
    )