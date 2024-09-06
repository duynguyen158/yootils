from collections.abc import Mapping
from datetime import datetime

from google.auth.transport._aiohttp_requests import Request as AsyncRequest
from google.auth.transport.requests import Request
from google.oauth2._service_account_async import (
    IDTokenCredentials as AsyncIDTokenCredentials,
)
from google.oauth2.service_account import IDTokenCredentials


def get_service_account_oidc_jwt(
    credentials_info: Mapping[str, str],
    target_audience: str,
    *,
    additional_claims: Mapping[str, str] | None = None,
    quota_project_id: str | None = None,
    universe_domain: str | None = None,
) -> tuple[str, datetime]:
    """Generates an OpenID Connect (OIDC) JSON Web Token (JWT) for a Google service account with respect to a target audience.
    This is primarily used for authenticating the service account to a third-party service such as an Cloud Run Service-run API.

    (For more information about this function's arguments, see: https://github.com/googleapis/google-auth-library-python/blob/c6d99030b8d972105913006bd052cf762b94a976/google/oauth2/service_account.py#L556.)

    Args:
        credentials_info (Mapping[str, str]): Credentials info for the service account. Normally, this is the JSON content of the service account key file.
        target_audience (str): Target audience for the JWT.
        additional_claims (Mapping[str, str] | None, optional): Additional claims to include in the JWT. Defaults to None.
        quota_project_id (str | None, optional): Quota project ID. Defaults to None.
        universe_domain (str | None, optional): Universe domain. Defaults to None.

    Returns:
        tuple[str, datetime]: A tuple containing the JWT and its expiration time.
    """
    # TODO: Remove type: ignore when https://github.com/googleapis/google-auth-library-python/issues/1567 is resolved
    credentials = IDTokenCredentials.from_service_account_info(  # type: ignore[no-untyped-call]
        credentials_info,
        target_audience=target_audience,
        additional_claims=additional_claims,
        quota_project_id=quota_project_id,
        universe_domain=universe_domain,
    )
    credentials.refresh(Request())  # type: ignore[no-untyped-call]
    return str(credentials.token), credentials.expiry


async def get_service_account_oidc_jwt_async(
    credentials_info: Mapping[str, str],
    target_audience: str,
    *,
    additional_claims: Mapping[str, str] | None = None,
    quota_project_id: str | None = None,
    universe_domain: str | None = None,
) -> tuple[str, datetime]:
    """Generates an OpenID Connect (OIDC) JSON Web Token (JWT) for a Google service account with respect to a target audience.
    This is primarily used for authenticating the service account to a third-party service such as an Cloud Run Service-run API.

    Args:
        credentials_info (Mapping[str, str]): Credentials info for the service account. Normally, this is the JSON content of the service account key file.
        target_audience (str): Target audience for the JWT.
        additional_claims (Mapping[str, str] | None, optional): Additional claims to include in the JWT. Defaults to None.
        quota_project_id (str | None, optional): Quota project ID. Defaults to None.
        universe_domain (str | None, optional): Universe domain. Defaults to None.

    Returns:
        tuple[str, datetime]: A tuple containing the JWT and its expiration time.
    """
    # TODO: Remove type: ignore when https://github.com/googleapis/google-auth-library-python/issues/1567 is resolved
    credentials = AsyncIDTokenCredentials.from_service_account_info(  # type: ignore[no-untyped-call]
        credentials_info,
        target_audience=target_audience,
        additional_claims=additional_claims,
        quota_project_id=quota_project_id,
        universe_domain=universe_domain,
    )
    await credentials.refresh(AsyncRequest())  # type: ignore[no-untyped-call]
    return str(credentials.token), credentials.expiry
