"""
This type stub file was generated by pyright.
"""

def get_guest_token():  # -> Any:
    """Token expires in 30 days"""
    ...

def get_authorized_token(username, password):  # -> Any:
    """
    OAuth2 authorization
    Token expires in 24 hours
    """
    ...

class Auth:
    """
    OAuth2 authorization
    Token expires in 24 hours
    """

    def __init__(self, username, password) -> None: ...
