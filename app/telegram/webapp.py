from typing import Any

from app.config import settings

_DASHBOARD_BUTTON_TEXT = "Open Dashboard"
_MENU_BUTTON_TEXT = "Dashboard"
_MINIAPP_PATH = "/miniapp"


def dashboard_webapp_url() -> str | None:
    if not settings.public_url:
        return None
    return f"{settings.public_url}{_MINIAPP_PATH}"


def dashboard_inline_keyboard() -> dict[str, Any] | None:
    url = dashboard_webapp_url()
    if not url:
        return None
    return {
        "inline_keyboard": [
            [
                {
                    "text": _DASHBOARD_BUTTON_TEXT,
                    "web_app": {"url": url},
                }
            ]
        ]
    }


def dashboard_menu_button() -> dict[str, Any] | None:
    url = dashboard_webapp_url()
    if not url:
        return None
    return {
        "type": "web_app",
        "text": _MENU_BUTTON_TEXT,
        "web_app": {"url": url},
    }
