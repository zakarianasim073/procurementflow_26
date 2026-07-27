import pytest
from fastapi import HTTPException

from app.api.v2 import sso


@pytest.mark.asyncio
async def test_oidc_callback_does_not_issue_token_without_verification():
    with pytest.raises(HTTPException) as exc:
        await sso.oidc_callback(
            sso.OIDCCallbackRequest(code="arbitrary", state="unvalidated"),
            tenant_id="configured-tenant",
            db=object(),
        )

    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_saml_callback_does_not_issue_token_without_verification():
    with pytest.raises(HTTPException) as exc:
        await sso.saml_acs(
            sso.SAMLCallbackRequest(saml_response="unverified"),
            tenant_id="configured-tenant",
            db=object(),
        )

    assert exc.value.status_code == 503
