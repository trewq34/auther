class AdfsProvider():
    def __init___(self):
        pass

    @staticmethod
    def prefix():
        return 'adfs-'

    @staticmethod
    def provider_options():
        return [
            {
                "short": "i",
                "long": "idp-url",
                'help': 'Your ADFS AWS sign in URL',
                "type": str,
                "required": True
            },
            {
                "short": "u",
                "long": "username",
                'help': 'The username you use to sign in',
                "type": str,
                "required": True
            },
            {
                "short": "p",
                "long": "password",
                'help': 'Your password',
                "type": str,
                "required": True,
                'hide_input': True,
                # 'prompt': True
            }
        ]