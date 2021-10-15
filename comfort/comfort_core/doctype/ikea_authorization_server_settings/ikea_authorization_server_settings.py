from comfort import TypedDocument


class IkeaAuthorizationServerSettings(TypedDocument):
    endpoint: str
    secret_key: str
