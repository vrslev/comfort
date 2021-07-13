"""
This type stub file was generated by pyright.
"""

from . import queries
from ...api import API

class Purchases(API):
    def __init__(self, token) -> None: ...
    def history(self, take=..., skip=...):  # -> Any:
        """
        Get purchase history.

        Parameters are for pagination.
        If you want to see all your purchases set 'take' to 10000
        """
        ...
    def order_info(self, order_number, email=...):  # -> Any:
        """
        Get order information: status and costs.

        :params order_number: ID of your purchase
        :params email: Your email. If set, there's no need to get token — just pass None
        """
        ...
