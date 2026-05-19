"""
截图模块
负责截取 SillyTavern 消息区域的截图及全页截图
截图保存在项目根目录下的 screenshot/ 文件夹中
"""
import os
import time

from .config import SCREENSHOT_DIR
from .browser import get_page, dismiss_toasts


def _make_filename(prefix: str) -> str:
    """生成带时间戳的文件名"""
    ts = time.strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}.png"


async def capture_screenshot(output_dir: str = None) -> str | None:
    """
    截取最后一条消息容器的截图
    支持长消息自动调整视口以完整截取溢出内容
    返回截图文件路径或 None
    """
    page = get_page()
    if output_dir is None:
        output_dir = SCREENSHOT_DIR
    os.makedirs(output_dir, exist_ok=True)

    filename = _make_filename("msg")
    output_path = os.path.join(output_dir, filename)

    await dismiss_toasts()

    # 优先截取完整消息容器 .mes
    try:
        el = page.locator(".mes").last
        await el.wait_for(state="visible", timeout=5000)

        box = await el.bounding_box()
        if box:
            viewport = page.viewport_size
            original_height = viewport["height"]
            original_width = viewport["width"]

            needed_height = int(box["height"] + 200)
            if needed_height > original_height:
                try:
                    await page.set_viewport_size(
                        {"width": original_width, "height": needed_height}
                    )
                    await page.wait_for_timeout(300)
                except Exception:
                    pass

            try:
                await el.scroll_into_view_if_needed()
                await page.wait_for_timeout(200)
            except Exception:
                pass

            await el.screenshot(path=output_path, type="png")
            print(f"[screenshot] 消息截图已保存: {output_path} (高度={box['height']})")

            try:
                await page.set_viewport_size(
                    {"width": original_width, "height": original_height}
                )
            except Exception:
                pass

            return output_path
        else:
            await el.screenshot(path=output_path, type="png")
            print(f"[screenshot] 消息截图已保存: {output_path}")
            return output_path

    except Exception as e:
        print(f"[screenshot] .mes截图失败({e})，回退到.mes_text")

    # 回退到 .mes_text
    try:
        el = page.locator(".mes_text").last
        await el.wait_for(state="visible", timeout=5000)

        box = await el.bounding_box()
        if box:
            viewport = page.viewport_size
            original_height = viewport["height"]
            original_width = viewport["width"]
            needed_height = int(box["height"] + 200)
            if needed_height > original_height:
                await page.set_viewport_size(
                    {"width": original_width, "height": needed_height}
                )
                await page.wait_for_timeout(300)
            await el.scroll_into_view_if_needed()
            await page.wait_for_timeout(200)

        await el.screenshot(path=output_path, type="png")
        print(f"[screenshot] 消息文本截图已保存: {output_path}")

        try:
            viewport = page.viewport_size
            await page.set_viewport_size({"width": viewport["width"], "height": 800})
        except Exception:
            pass

        return output_path
    except Exception as e2:
        print(f"[screenshot] .mes_text截图也失败({e2})，回退到全页截图")

    # 最终回退：全页截图
    try:
        await page.screenshot(path=output_path, full_page=True)
        print(f"[screenshot] 全页截图已保存: {output_path}")
        return output_path
    except Exception as e2:
        print(f"[screenshot] 截图完全失败: {e2}")
        return None


async def capture_full_screenshot(output_dir: str = None) -> str | None:
    """截取整个 ST 页面的完整截图，返回路径或 None"""
    page = get_page()
    if output_dir is None:
        output_dir = SCREENSHOT_DIR
    os.makedirs(output_dir, exist_ok=True)

    filename = _make_filename("full")
    output_path = os.path.join(output_dir, filename)

    await dismiss_toasts()

    try:
        await page.screenshot(path=output_path, full_page=True)
        print(f"[screenshot] 全页截图已保存: {output_path}")
        return output_path
    except Exception as e:
        print(f"[screenshot] 全页截图失败: {e}")
        return None
