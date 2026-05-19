"""
无头浏览器管理模块
负责 Playwright Chromium 的启动、关闭、刷新及页面状态管理
"""
import asyncio
import atexit

from playwright.async_api import async_playwright
from .config import ST_URL, HEADLESS_MODE, VIEWPORT_WIDTH, REFRESH_DELAY

_playwright = None
_browser = None
_page = None


def get_page():
    """获取当前页面实例，供其他模块使用"""
    return _page


async def init_browser():
    """启动无头浏览器并导航到 SillyTavern，等待页面就绪"""
    global _playwright, _browser, _page
    _playwright = await async_playwright().start()
    _browser = await _playwright.chromium.launch(headless=HEADLESS_MODE)
    context = await _browser.new_context(
        viewport={"width": VIEWPORT_WIDTH + 80, "height": 800}
    )
    _page = await context.new_page()
    await _page.goto(ST_URL, wait_until="domcontentloaded")
    await _page.wait_for_function(
        "() => window.SillyTavern && window.SillyTavern.getContext",
        timeout=30000,
    )
    print(f"[browser] 浏览器已启动, ST已就绪, viewport={VIEWPORT_WIDTH + 80}x800")


async def close_browser():
    """关闭浏览器和 Playwright 实例"""
    global _browser, _playwright, _page
    if _page:
        try:
            await _page.close()
        except Exception:
            pass
        _page = None
    if _browser:
        try:
            await _browser.close()
        except Exception:
            pass
        _browser = None
    if _playwright:
        try:
            await _playwright.stop()
        except Exception:
            pass
        _playwright = None
    print("[browser] 浏览器已关闭")


def _cleanup():
    """atexit 兜底清理"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(close_browser())
        else:
            loop.run_until_complete(close_browser())
    except Exception:
        pass


atexit.register(_cleanup)


async def refresh_page() -> bool:
    """刷新 ST 页面并等待就绪"""
    try:
        await _page.reload(wait_until="domcontentloaded")
        await _page.wait_for_function(
            "() => window.SillyTavern && window.SillyTavern.getContext",
            timeout=30000,
        )
        await _page.wait_for_timeout(REFRESH_DELAY * 1000)
        print("[browser] 页面已刷新, ST已就绪")
        return True
    except Exception as e:
        print(f"[browser] 页面刷新失败: {e}")
        return False


async def dismiss_toasts():
    """清除 ST 页面上所有 toastr 通知，避免遮挡截图"""
    try:
        await _page.evaluate(
            "() => { if (typeof toastr !== 'undefined') toastr.clear(); }"
        )
    except Exception:
        pass
