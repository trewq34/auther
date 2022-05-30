import configparser
import requests
import auther.providers.helpers.azuread as helper

from auther.providers.BaseProvider import BaseProvider

class AzureadProvider(BaseProvider):
    def __init__(self, options):
        self.login_url = 'https://login.microsoftonline.com'
        for option, value in options.items():
            setattr(self, option, value)

    # login to Azure AD, overwrite value of self.password and del it once used
    def login(self):
        url = helper.create_login_url(self.app_id, self.tenant_id)
        roles = helper.do_login(url, username=self.username, password=self.password)

        # destroy password
        self.password = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
        del self.password
        return roles

    @staticmethod
    def prefix():
        return 'azuread-'

    @staticmethod
    def provider_options():
        return [
            {
                "function": "tenant_id",
                "long": "tenant-id",
                'help': 'Your Azure AD Tenant ID',
                "type": str,
                "required": True
            },
            {
                "function": "app_id",
                "long": "app-id",
                'help': 'Your Azure AD Application ID',
                "type": str,
                "required": True
            },
            {
                "function": "username",
                "long": "username",
                'help': 'The username you use to sign in',
                "type": str,
                "required": True
            }
        ]