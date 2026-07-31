from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session
from backend.app.db.database import get_session
from backend.app.models.user import User
from backend.app.core.jwt_handler import decode_token

# This tells FastAPI "this API uses Bearer token authentication"
# It's what makes the Authorize button appear in /docs
bearer_scheme = HTTPBearer()

# This function extracts and verifies the logged-in user from the request's token.
# Any protected endpoint can use this to know "who is making this request".
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: Session = Depends(get_session)
) -> User:
    token = credentials.credentials  # this is just the token, without "Bearer "

    try:
        # Decode the token to get the user's info stored inside it
        payload = decode_token(token)
        # Make sure this is an access token, not a refresh token
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except Exception:
        # If the token is invalid or expired, decode_token will fail here
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Look up the actual user in the database using the ID stored in the token
    user = session.get(User, int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


# This function creates a "role checker" for a specific list of allowed roles.
# Example: require_role(["admin"]) only allows admins through.
def require_role(allowed_roles: list[str]):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Requires one of these roles: {allowed_roles}"
            )
        return current_user
    return role_checker