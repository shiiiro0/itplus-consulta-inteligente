"""Microsoft Entra ID (Azure AD) token validation."""

from __future__ import annotations

import logging
import time

import jwt
from jwt import PyJWKClient

logger = logging.getLogger(__name__)


class AzureAuthError(Exception):
    """Azure AD validation error."""


_jwks_clients: dict[str, PyJWKClient] = {}
_jwks_created: dict[str, float] = {}
_JWKS_TTL_S = 3600


def is_azure_configured() -> bool:
    from itplus.app.core.config import get_settings

    settings = get_settings()
    return bool(settings.azure_tenant_id.strip() and settings.azure_client_id.strip())


def _get_jwks_client(tenant_id: str) -> PyJWKClient:
    now = time.time()
    cached = _jwks_clients.get(tenant_id)
    if cached is not None and (now - _jwks_created.get(tenant_id, 0)) < _JWKS_TTL_S:
        return cached
    uri = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
    client = PyJWKClient(uri)
    _jwks_clients[tenant_id] = client
    _jwks_created[tenant_id] = now
    return client


def _extract_email(claims: dict) -> str:
    for key in ("preferred_username", "email", "upn", "unique_name"):
        val = claims.get(key)
        if val and "@" in str(val):
            return str(val).strip()
    return ""


def validar_token_azure(token: str) -> dict:
    from itplus.app.core.config import get_settings

    settings = get_settings()
    tenant_id = settings.azure_tenant_id.strip()
    client_id = settings.azure_client_id.strip()
    if not tenant_id or not client_id:
        raise AzureAuthError(
            "Azure AD no está configurado. Define AZURE_TENANT_ID y AZURE_CLIENT_ID."
        )

    issuers = (
        f"https://login.microsoftonline.com/{tenant_id}/v2.0",
        f"https://sts.windows.net/{tenant_id}/",
    )

    try:
        signing_key = _get_jwks_client(tenant_id).get_signing_key_from_jwt(token)
    except Exception as exc:
        logger.warning("No se pudo obtener la llave JWKS de Azure: %s", exc)
        raise AzureAuthError("No se pudo verificar la firma del token de Microsoft.") from exc

    last_err: Exception | None = None
    for issuer in issuers:
        try:
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=client_id,
                issuer=issuer,
                options={"require": ["exp", "iss", "aud"]},
            )
            email = _extract_email(claims)
            if not email:
                raise AzureAuthError("El token de Microsoft no contiene un correo válido.")
            return {
                "email": email,
                "name": str(claims.get("name") or email),
                "oid": claims.get("oid"),
            }
        except jwt.ExpiredSignatureError as exc:
            raise AzureAuthError(
                "La sesión de Microsoft expiró. Inicia sesión nuevamente."
            ) from exc
        except jwt.InvalidIssuerError as exc:
            last_err = exc
            continue
        except jwt.InvalidAudienceError as exc:
            raise AzureAuthError(
                "El token no corresponde a esta aplicación (audiencia inválida)."
            ) from exc
        except AzureAuthError:
            raise
        except Exception as exc:
            last_err = exc
            continue

    logger.warning("Token de Azure inválido: %s", last_err)
    raise AzureAuthError("Token de Microsoft inválido.")
