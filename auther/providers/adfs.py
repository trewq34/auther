import configparser
import requests

from auther.exceptions import ProviderNotImplementedError
from auther.providers.BaseProvider import BaseProvider

class AdfsProvider(BaseProvider):
    def __init__(self, idp_url):
        self.idp_url = f'https://{idp_url}/adfs/ls/IdpInitiatedSignOn.aspx?loginToRp=urn:amazon:webservices'

        raise ProviderNotImplementedError('The provider adfs is not currently implemented')

    def login(self, username, password):
        pass

    def _authenticate(self):
        pass

    def _get_roles(self):
        pass

    def assume_role(self, role):
        pass

    @staticmethod
    def prefix():
        return 'adfs-'