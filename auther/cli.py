import click

from auther.exceptions import *
from auther.providers import *

from pathlib import Path

@click.group()
@click.version_option()
def main():
    pass

@main.command('configure')
@click.option('--aws-config', default=f'{Path.home()}/.aws/config', help='The path to your AWS config file', required=False)
@click.option('--profile', default='default', help='The name of the AWS profile', required=False)
@click.option('--region', default='eu-west-1', help='Your prefered AWS region', required=False)
@click.option('--output', default='json', help='Your prefered output format', required=False)
@click.option('--provider', default='azuread', help='The federated provider', required=False)
def configure(*args, **kwargs):
    provider = kwargs['provider']

    try:
        provider_options = getattr(globals()[provider], f'{provider.replace("_", "").title()}Provider').provider_options()
        prefix = getattr(globals()[provider], f'{provider.replace("_", "").title()}Provider').prefix()
    except AttributeError:
        raise ProviderNotFound(f"The provider {provider} doesn't have the correct module structure.")
    except NameError:
        raise ProviderNotFound(f"The provider {provider} doesn't exist")

    options = {}
    for opt in provider_options:
        option = opt['long']
        text = opt['help']

        # delete the options which aren't relevant for a prompt() call
        del opt['help']
        del opt['function']
        del opt['long']
        del opt['required']

        if option != 'password':
            options[prefix + option] = click.prompt(text, **opt)

    options['output'] = kwargs['output']
    options['region'] = kwargs['region']

    getattr(globals()[provider], f'{provider.replace("_", "").title()}Provider').write_config(options, kwargs['profile'], kwargs['aws_config'])

@main.command()
@click.option('--provider', default='azuread', help='The federated provider', required=False)
@click.option('--profile', default='default', help='The name of the AWS profile', required=False)
@click.option('--aws-config', default=f'{Path.home()}/.aws/config', help='The path to your AWS config file', required=False)
@click.option('--aws-creds', default=f'{Path.home()}/.aws/credentials', help='The path to your AWS credentials file', required=False)
def login(*args, **kwargs):
    provider = kwargs['provider']

    try:
        opt_list = getattr(globals()[provider], f'{provider.replace("_", "").title()}Provider').list_options()
        provider_options = getattr(globals()[provider], f'{provider.replace("_", "").title()}Provider').provider_options()
        config = getattr(globals()[provider], f'{provider.replace("_", "").title()}Provider').get_config(kwargs['aws_config'], kwargs['profile'], provider, opt_list)
    except AttributeError:
        raise ProviderNotFound(f"The provider {provider} doesn't have the correct module structure.")
    except NameError:
        raise ProviderNotFound(f"The provider {provider} doesn't exist")

    username = next(config.get(f"{provider}_{option.get('function')}") for option in provider_options if option.get('function') == 'username')
    idp_url = next(config.get(f"{provider}_{option.get('function')}") for option in provider_options if option.get('function') == 'idp_url')

    if not username:
        raise ProviderNotConfigured(f"The provider {provider} doesn't have the correct option structure")

    # password = click.prompt(f'Enter the password for {username}', type=str, hide_input=True)

    auth_provider = getattr(globals()[provider], f'{provider.replace("_", "").title()}Provider')(idp_url)
    print(auth_provider.__dict__)
    # roles = auth_provider.login(username, '123')

if __name__ == '__main__':
    main()