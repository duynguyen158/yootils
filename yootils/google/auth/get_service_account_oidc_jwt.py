from collections.abc import Mapping
from datetime import datetime
from typing import TypedDict

from google.auth.transport._aiohttp_requests import Request as AsyncRequest
from google.auth.transport.requests import Request
from google.oauth2._service_account_async import (
    IDTokenCredentials as AsyncIDTokenCredentials,
)
from google.oauth2.service_account import IDTokenCredentials


class JwtClaims(TypedDict):
    # Issued at time (seconds since epoch)
    iat: int
    # Expiration time (seconds since epoch, default will be 1 hour from iat but can be set to a maximum of 12 hours)
    exp: int
    # Issuer (service account email, same as the email address in `credentials_info`)
    iss: str
    # Target audience (same as `target_audience`)
    target_audience: str


def get_service_account_oidc_jwt(
    credentials_info: Mapping[str, str],
    target_audience: str,
    *,
    additional_claims: JwtClaims | None = None,
    quota_project_id: str | None = None,
    universe_domain: str | None = None,
) -> tuple[str, datetime]:
    """
    Generates an OpenID Connect (OIDC) JSON Web Token (JWT) for a Google service account with respect to a target audience.
    This is primarily used for authenticating the service account to a third-party service such as an Cloud Run Service-run API.

    (For more information about this function's arguments, see: https://github.com/googleapis/google-auth-library-python/blob/c6d99030b8d972105913006bd052cf762b94a976/google/oauth2/service_account.py#L556.)

    Args:
        credentials_info (Mapping[str, str]): Credentials info for the service account. Normally, this is the JSON content of the service account key file.
        target_audience (str): Target audience for the JWT.
        additional_claims (Mapping[str, str] | None, optional): Additional claims to include in the JWT. Defaults to None. (For example, if you want to extend the JWT's lifetime, specify a higher value for the `exp` key -- maximum is 12 hours from `iat`.)
        quota_project_id (str | None, optional): Quota project ID. Defaults to None.
        universe_domain (str | None, optional): Universe domain. Defaults to None.

    Returns:
        tuple[str, datetime]: A tuple containing the JWT and its expiration time.
    """
    credentials = IDTokenCredentials.from_service_account_info(
        credentials_info,
        target_audience=target_audience,
        additional_claims=additional_claims,
        quota_project_id=quota_project_id,
        universe_domain=universe_domain,
    )
    credentials.refresh(Request())
    return str(credentials.token), credentials.expiry


async def get_service_account_oidc_jwt_async(
    credentials_info: Mapping[str, str],
    target_audience: str,
    *,
    additional_claims: JwtClaims | None = None,
    quota_project_id: str | None = None,
    universe_domain: str | None = None,
) -> tuple[str, datetime]:
    """
    Generates an OpenID Connect (OIDC) JSON Web Token (JWT) for a Google service account with respect to a target audience.
    This is primarily used for authenticating the service account to a third-party service such as an Cloud Run Service-run API.

    Args:
        credentials_info (Mapping[str, str]): Credentials info for the service account. Normally, this is the JSON content of the service account key file.
        target_audience (str): Target audience for the JWT.
        additional_claims (Mapping[str, str] | None, optional): Additional claims to include in the JWT. Defaults to None. (For example, if you want to extend the JWT's lifetime, specify a higher value for the `exp` key -- maximum is 12 hours from `iat`.)
        quota_project_id (str | None, optional): Quota project ID. Defaults to None.
        universe_domain (str | None, optional): Universe domain. Defaults to None.

    Returns:
        tuple[str, datetime]: A tuple containing the JWT and its expiration time.
    """
    credentials = AsyncIDTokenCredentials.from_service_account_info(
        credentials_info,
        target_audience=target_audience,
        additional_claims=additional_claims,
        quota_project_id=quota_project_id,
        universe_domain=universe_domain,
    )
    await credentials.refresh(AsyncRequest())
    return str(credentials.token), credentials.expiry
