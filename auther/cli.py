import click

from auther.exceptions import *
from auther.providers import *

from pathlib import Path

@click.group()
@click.version_option()
def main():
    pass

@main.command('configure')
@click.option('--aws-config', default=f'{Path.home()}/.aws/credentials', help='The path to your AWS credentials file', required=False)
@click.option('--profile', default='default', help='The name of the AWS profile', required=False)
@click.option('--provider', default='azuread', help='The federated provider', required=False)
def configure(*args, **kwargs):
    provider = kwargs['provider']

    try:
        provider_options = getattr(globals()[provider], f'{provider.replace("_", " ").title().replace(" ", "")}Provider').provider_options()
        prefix = getattr(globals()[provider], f'{provider.replace("_", " ").title().replace(" ", "")}Provider').prefix()
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
        del opt['short']
        del opt['long']
        del opt['required']

        options[prefix + option] = click.prompt(text, **opt)

    pass

if __name__ == '__main__':
    main()