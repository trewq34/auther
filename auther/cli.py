import typer

from auther.exceptions import *
from auther.providers import *

from pathlib import Path

app = typer.Typer(no_args_is_help=True)

@app.command(help='Configure a chosen identiy provider for use')
def configure(
    aws_config: str = typer.Option(f'{Path.home()}/.aws/config', help='The path to your AWS config file'),
    profile: str = typer.Option('default', help='The name of the AWS profile'),
    region: str = typer.Option('eu-west-1', help='Your prefered AWS region'),
    output: str = typer.Option('json', help='Your prefered AWS CLI output format'),
    provider: str = typer.Option('azuread', help='The federated provider')
):
    try:
        provider_options = getattr(globals()[provider], f'{provider.replace("_", "").title()}Provider').provider_options()
        prefix = getattr(globals()[provider], f'{provider.replace("_", "").title()}Provider').prefix()
    except AttributeError:
        raise ProviderNotFound(f"The provider {provider} doesn't have the correct module structure.")
    except (NameError, KeyError):
        raise ProviderNotFound(f"The provider {provider} doesn't exist")

    options = {}
    for opt in provider_options:
        option = opt['long']
        text = opt['help']

        # delete the attributes which aren't relevant for a prompt() call
        del opt['help']
        del opt['function']
        del opt['long']
        del opt['required']

        if option != 'password':
            options[prefix + option] = typer.prompt(text, **opt)

    options['output'] = output
    options['region'] = region

    getattr(globals()[provider], f'{provider.replace("_", "").title()}Provider').write_config(options, profile, aws_config)

@app.command(help='Authenticate using a specified identity provider')
def login(
    provider: str = typer.Option('azuread', help='The federated provider'),
    profile: str = typer.Option('default', help='The name of the AWS profile'),
    aws_config: str = typer.Option(f'{Path.home()}/.aws/config', help='The path to your AWS config file'),
    aws_creds: str = typer.Option(f'{Path.home()}/.aws/credentials', help='The path to your AWS credentials file'),
):
    try:
        opt_list = getattr(globals()[provider], f'{provider.replace("_", "").title()}Provider').list_options()
        provider_options = getattr(globals()[provider], f'{provider.replace("_", "").title()}Provider').provider_options()
        config = getattr(globals()[provider], f'{provider.replace("_", "").title()}Provider').get_config(aws_config, profile, provider, opt_list)
    except AttributeError:
        raise ProviderNotFound(f"The provider {provider} doesn't have the correct module structure.")
    except (NameError, KeyError):
        raise ProviderNotFound(f"The provider {provider} doesn't exist")

    opts = {
        'profile': profile,
        'aws_config': aws_config,
        'aws_creds': aws_creds
    }
    
    for option in provider_options:
        opts[option.get('function')] = config.get(f"{provider}_{option.get('function')}")

    opts['password'] = typer.prompt(f'Enter the password for {opts.get("username")}', type=str, hide_input=True)

    auth_provider = getattr(globals()[provider], f'{provider.replace("_", "").title()}Provider')(opts)

    # destroy password
    opts['password'] = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    del opts['password']

    roles = auth_provider.login()
    if not roles:
        raise ProviderAuthenticationError(f'Provider {provider} returned no available roles')

    if len(roles) > 1:
        for index, role in enumerate(roles):
            print(f'[{index}] - {role[1]}')
        chosen_role = typer.prompt('Enter the index of your chosen role', type=int)
    else:
        chosen_role = 0

    duration = typer.prompt('Enter session duration in hours', type=int, default=1)

    auth_provider.assume_role(provider, profile, roles[chosen_role], duration * 60 * 60)
    

if __name__ == '__main__':
    app()