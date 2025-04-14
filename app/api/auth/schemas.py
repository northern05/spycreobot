from pydantic import ConfigDict, BaseModel


class AuthResponse(BaseModel):
    """
    Schema to response on auth
    """
    model_config = ConfigDict(from_attributes=True)
    access_token: str
    refresh_token: str
