class ProviderNotFound(Exception):
    pass

class ProviderNotConfigured(Exception):
    pass

class ProviderAuthenticationError(Exception):
    pass

class ProviderNotImplementedError(Exception):
    pass

class RoleDurationError(Exception):
    pass