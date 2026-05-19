"""
Sillytavern-Session-Manager 核心模块
从 NC-Relay2ST 提取的 SillyTavern 无头浏览器交互核心，平台无关
"""

from .config import ST_URL, HEADLESS_MODE, VIEWPORT_WIDTH, SCREENSHOT_DIR
from .browser import (
    init_browser,
    close_browser,
    refresh_page,
    dismiss_toasts,
    get_page,
)
from .interaction import (
    inject_message,
    wait_for_response,
    send_message,
    swipe_left,
    swipe_right,
    regenerate,
    cancel_processing,
)
from .screenshot import (
    capture_screenshot,
    capture_full_screenshot,
)
from .api import (
    fetch_characters,
    fetch_recent_chats,
    fetch_character_chats,
    open_chat,
    delete_messages,
    delete_chat,
)
