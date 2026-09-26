class FetchCancelled(Exception):
    """The user cancelled a long-running lookup."""


class FetchError(Exception):
    """A remote service failed in a way worth showing to the user."""
