import configparser
import re
import boto3
from datetime import datetime

from auther.exceptions import *
from botocore.exceptions import ClientError

class BaseProvider:
    @staticmethod
    def provider_options():
        return [
            {
                "function": "idp_url",
                "long": "idp-url",
                'help': 'Your ADFS AWS sign in URL',
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

    @classmethod
    def list_options(cls):
        return [opt.get('long') for opt in cls.provider_options()]

    @classmethod
    def write_config(cls, options, profile, aws_config):
        config = configparser.ConfigParser()
        config.read(aws_config)

        if not cls._has_profile(config, profile):
            if profile == 'default':
                config.add_section(profile)
            else:
                config.add_section(f'profile {profile}')

        for key, value in options.items():
            if profile != 'default':
                config.set(f'profile {profile}', key.replace('-', '_'), value)
            else:
                config.set(profile, key.replace('-', '_'), value)

        with open(aws_config, 'w') as config_file:
            config.write(config_file)

    @classmethod
    def write_credentials(cls, creds, profile, aws_creds_file):
        config = configparser.ConfigParser()
        config.read(aws_creds_file)

        if not cls._has_profile(config, profile):
            config.add_section(profile)

        for key, value in creds.items():
            config.set(profile, key, value)

        with open(aws_creds_file, 'w') as config_file:
            config.write(config_file)

    @staticmethod
    def _has_profile(config, profile, credentials=False):
        if profile != 'default' and not credentials:
            if not config.has_section(f'profile {profile}'):
                return False
        else:
            if not config.has_section(profile):
                return False

        return True

    @classmethod
    def get_config(cls, config_file, profile, provider, option_list):
        config = configparser.ConfigParser()
        config.read(config_file)

        if not cls._has_profile(config, profile) or not cls._is_profile_configured(config, profile, provider, option_list):
            raise ProviderNotConfigured(f'The AWS profile {profile} has not been configured to work with auther provider {provider}. Run "auther configure" first!')

        if profile != 'default':
            return dict(config.items(f'profile {profile}'))
        else:
            return dict(config.items(profile))

    @staticmethod
    def _is_profile_configured(config, profile, provider, option_list):
        if profile != 'default':
            for opt in option_list:
                if f'{provider}_{opt}'.replace('-', '_') not in config.options(f'profile {profile}'):
                    return False
        else:
            for opt in option_list:
                if f'{provider}_{opt}'.replace('-', '_') not in config.options(profile):
                    return False

        return True

    def assume_role(self, provider, profile, role, duration):
        client = boto3.client('sts')

        print(f'Assuming role {role[1]}')

        try:
            result = client.assume_role_with_saml(
                RoleArn=role[1],
                PrincipalArn=role[2],
                SAMLAssertion=role[0],
                DurationSeconds=duration,
            )
        except ClientError as ex:
            if 'The requested DurationSeconds exceeds the MaxSessionDuration set for this role' in str(ex):
                raise RoleDurationError(f'{int(duration / 60 / 60)} hour(s) is too high for this role. Try a lower value.')
            raise ex

        creds = {
            'aws_access_key_id': result["Credentials"]["AccessKeyId"],
            'aws_secret_access_key': result["Credentials"]["SecretAccessKey"],
            'aws_session_token': result["Credentials"]["SessionToken"],
            'aws_expiration': result["Credentials"]["Expiration"].isoformat(timespec='microseconds').replace('+00:00', 'Z'),
            'auther_provider': provider
        }

        self.write_credentials(creds, profile, self.aws_creds)