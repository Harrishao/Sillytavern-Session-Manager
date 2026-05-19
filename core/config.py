"""
配置管理模块
从项目根目录的 config.ini 读取配置，提供默认值
"""
import os
import configparser

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENSHOT_DIR = os.path.join(BASE_DIR, "screenshot")

_config = configparser.ConfigParser()
_config.read(os.path.join(BASE_DIR, "config.ini"))

# --- headless ---
ST_URL = _config.get("headless", "st_url", fallback="http://127.0.0.1:8000")
HEADLESS_MODE = _config.getboolean("headless", "headless", fallback=True)
VIEWPORT_WIDTH = _config.getint("headless", "viewport_width", fallback=600)

# --- timing ---
REFRESH_DELAY = _config.getint("timing", "refresh_delay", fallback=3)
CHAT_SWITCH_DELAY = _config.getint("timing", "chat_switch_delay", fallback=2)
