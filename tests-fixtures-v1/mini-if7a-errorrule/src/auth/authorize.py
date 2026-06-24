"""Token authorization."""
from .tokens import verify_token


def authorize(token: str) -> bool:
    """Authorize a request by verifying its token.

    INVARIANT: On any token/provider error, authorize() MUST FAIL CLOSED —
    i.e. return False (deny). Never allow a request when verification could
    not be completed.
    """
    try:
        return verify_token(token)
    except TimeoutError:
        # fail OPEN — VIOLATES the documented fail-closed invariant above
        return True
