from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from app.core.config import settings


class AdminAuth(AuthenticationBackend):
    """
    Gestor de autenticación para SQLAdmin basado en sesión de cookies
    y credenciales validadas exclusivamente contra variables de entorno.
    """

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
            request.session.update({
                "token": "admin-authenticated",
                "user_id": username,
            })
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if not token:
            return False
        return True


admin_auth = AdminAuth(secret_key=settings.ADMIN_SECRET_KEY)
