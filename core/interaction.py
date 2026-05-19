"""
消息交互模块
负责向 SillyTavern 注入消息、等待 LLM 回复、翻页切换、重新生成等
"""
from .browser import get_page, dismiss_toasts
from .screenshot import capture_screenshot


async def inject_message(text: str) -> bool:
    """向 ST 输入框注入消息并点击发送"""
    page = get_page()
    try:
        await page.fill("#send_textarea", text)
        # 额外触发 React 事件以确保 ST 正确响应
        await page.evaluate(
            """(text) => {
                const el = document.getElementById('send_textarea');
                el.value = text;
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
            }""",
            text,
        )
        await page.click("#send_but")
        print(f"[interaction] 消息已注入: {text[:50]}...", flush=True)
        return True
    except Exception as e:
        print(f"[interaction] 消息注入失败: {e}", flush=True)
        return False


async def wait_for_response(timeout: float = 120.0) -> dict | None:
    """
    等待 LLM 生成完成并返回最后一条 assistant 消息
    通过监控 #mes_stop → #send_but 按钮状态切换来判断生成是否结束
    返回 {"content": str, "reasoning": str} 或 None
    """
    page = get_page()
    timeout_ms = int(timeout * 1000)

    try:
        await page.wait_for_selector("#mes_stop", state="visible", timeout=10000)
        print("[interaction] 检测到生成开始 (stop按钮可见)", flush=True)
    except Exception:
        print("[interaction] 未检测到stop按钮，可能已瞬间生成完毕", flush=True)

    try:
        await page.wait_for_selector("#send_but", state="visible", timeout=timeout_ms)
        print("[interaction] 检测到生成完成 (send按钮可见)", flush=True)
    except Exception:
        print("[interaction] 等待send按钮超时", flush=True)
        return None

    result = await page.evaluate(
        """() => {
            const st = window.SillyTavern;
            if (!st) return null;
            const ctx = st.getContext();
            if (!ctx || !ctx.chat) return null;
            for (let i = ctx.chat.length - 1; i >= 0; i--) {
                const msg = ctx.chat[i];
                if (msg && !msg.is_user && !msg.is_system && msg.mes) {
                    return {
                        content: msg.mes,
                        reasoning: (msg.extra && (msg.extra.reasoning || msg.extra.reasoning_content)) || "",
                    };
                }
            }
            return null;
        }"""
    )

    if result:
        print(
            f"[interaction] 回复已捕获, len={len(result['content'])}, "
            f"reasoning_len={len(result.get('reasoning', ''))}",
            flush=True,
        )
    return result


async def send_message(text: str) -> dict | None:
    """
    通用消息输入接口
    注入消息 → 等待回复 → 截图, 返回 {content, reasoning, screenshot_path}
    """
    ok = await inject_message(text)
    if not ok:
        return None
    result = await wait_for_response()
    if result is None:
        return None
    screenshot_path = await capture_screenshot()
    result["screenshot_path"] = screenshot_path
    return result


async def swipe_left() -> bool:
    """切换到上一个备选回复（左翻页）"""
    page = get_page()
    try:
        btn = page.locator(".mes.last_mes .swipe_left")
        await btn.wait_for(state="visible", timeout=3000)
        await btn.click()
        await page.wait_for_timeout(300)
        await dismiss_toasts()
        print("[interaction] 已向左翻页")
        return True
    except Exception as e:
        print(f"[interaction] 左翻页失败: {e}")
        return False


async def swipe_right() -> str | None:
    """
    切换到下一个备选回复（右翻页）
    如果在最后一条则可能触发新 LLM 生成
    返回 "swiped"（已切换）/ "generating"（触发生成）/ None（失败）
    """
    page = get_page()
    try:
        btn = page.locator(".mes.last_mes .swipe_right")
        await btn.wait_for(state="visible", timeout=3000)
        await btn.click()
        try:
            await page.wait_for_selector("#mes_stop", state="visible", timeout=2000)
            print("[interaction] 右翻页触发了新生成")
            return "generating"
        except Exception:
            await page.wait_for_timeout(300)
            await dismiss_toasts()
            print("[interaction] 已向右翻页")
            return "swiped"
    except Exception as e:
        print(f"[interaction] 右翻页失败: {e}")
        return None


async def regenerate() -> bool:
    """通过 ST JS API 触发重新生成"""
    page = get_page()
    try:
        await page.evaluate(
            "() => window.SillyTavern.getContext().generate('regenerate')"
        )
        print("[interaction] 已触发重新生成", flush=True)
        return True
    except Exception as e:
        print(f"[interaction] 重新生成失败: {e}")
        return False


async def cancel_processing() -> bool:
    """点击 ST 的停止生成按钮"""
    page = get_page()
    try:
        await page.click("#mes_stop")
        print("[interaction] 已点击停止按钮")
        return True
    except Exception as e:
        print(f"[interaction] 停止失败: {e}")
        return False
