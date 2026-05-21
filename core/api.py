"""
SillyTavern API 交互模块
通过浏览器 JS 上下文调用 ST 内部 API，管理角色卡、聊天列表、聊天内容等
"""
from .browser import get_page, dismiss_toasts
from .config import CHAT_SWITCH_DELAY


async def fetch_characters() -> list:
    """获取所有角色卡列表"""
    page = get_page()
    try:
        data = await page.evaluate(
            """async () => {
                const ctx = window.SillyTavern.getContext();
                const headers = ctx.getRequestHeaders();
                const resp = await fetch('/api/characters/all', {
                    method: 'POST', headers: headers, body: JSON.stringify({}),
                });
                if (!resp.ok) return [];
                return await resp.json();
            }"""
        )
        print(f"[api] 获取到 {len(data)} 个角色卡")
        return data
    except Exception as e:
        print(f"[api] 获取角色卡列表失败: {e}")
        return []


async def fetch_recent_chats() -> list:
    """获取最近聊天列表"""
    page = get_page()
    try:
        data = await page.evaluate(
            """async () => {
                const ctx = window.SillyTavern.getContext();
                const headers = ctx.getRequestHeaders();
                const resp = await fetch('/api/chats/recent', {
                    method: 'POST', headers: headers, body: JSON.stringify({}),
                });
                if (!resp.ok) return [];
                return await resp.json();
            }"""
        )
        print(f"[api] 获取到 {len(data)} 条最近聊天")
        return data
    except Exception as e:
        print(f"[api] 获取最近聊天失败: {e}")
        return []


async def fetch_character_chats(avatar_url: str) -> list:
    """获取指定角色的所有聊天记录"""
    page = get_page()
    try:
        data = await page.evaluate(
            """async (avatar_url) => {
                const ctx = window.SillyTavern.getContext();
                const headers = ctx.getRequestHeaders();
                const resp = await fetch('/api/characters/chats', {
                    method: 'POST', headers: headers,
                    body: JSON.stringify({avatar_url: avatar_url}),
                });
                if (!resp.ok) return [];
                return await resp.json();
            }""",
            avatar_url,
        )
        print(f"[api] 获取到角色({avatar_url})的 {len(data)} 条聊天记录")
        return data
    except Exception as e:
        print(f"[api] 获取角色聊天记录失败: {e}")
        return []


async def open_chat(file_name: str) -> bool:
    """通过 JS API 打开指定聊天（先选角色再打开聊天）"""
    page = get_page()
    try:
        clean_file = file_name.replace(".jsonl", "")

        await page.evaluate(
            """async (file_name) => {
                const ctx = window.SillyTavern.getContext();
                await ctx.getCharacters();

                const cleanName = file_name.replace('.jsonl', '');
                const dashIdx = cleanName.lastIndexOf(' - ');
                let chId = -1;

                if (dashIdx > 0) {
                    const charName = cleanName.substring(0, dashIdx);
                    for (let i = 0; i < ctx.characters.length; i++) {
                        if (ctx.characters[i] && ctx.characters[i].chat === cleanName) {
                            chId = i; break;
                        }
                    }
                    if (chId === -1) {
                        for (let i = 0; i < ctx.characters.length; i++) {
                            if (ctx.characters[i] && ctx.characters[i].name === charName) {
                                chId = i; break;
                            }
                        }
                    }
                }

                if (chId === -1) throw new Error('找不到对应角色: ' + file_name);

                await ctx.selectCharacterById(chId, {switchMenu: true});
                await ctx.openCharacterChat(cleanName);
                return true;
            }""",
            clean_file,
        )

        await page.wait_for_timeout(CHAT_SWITCH_DELAY * 1000)
        await dismiss_toasts()
        print(f"[api] 已打开聊天: {file_name}")
        return True
    except Exception as e:
        print(f"[api] 打开聊天失败: {e}")
        return False


async def delete_messages(n: int = 1) -> bool:
    """通过 STscript 删除当前聊天最后 N 条消息（仅支持 1 或 2）"""
    if n not in (1, 2):
        n = 1
    page = get_page()
    try:
        await page.evaluate(
            """async (n) => {
                const ctx = window.SillyTavern.getContext();
                await ctx.executeSlashCommands(`/del ${n}`);
            }""",
            n,
        )
        await page.wait_for_timeout(500)
        print(f"[api] 已删除最后 {n} 条消息")
        return True
    except Exception as e:
        print(f"[api] 删除消息失败: {e}")
        return False


async def fetch_personas() -> list:
    """获取所有用户设定(personalist)"""
    page = get_page()
    try:
        data = await page.evaluate(
            """() => {
                const containers = document.querySelectorAll('#user_avatar_block .avatar-container');
                if (!containers.length) return [];
                const result = [];
                containers.forEach(c => {
                    const nameEl = c.querySelector('.ch_name');
                    const descEl = c.querySelector('.ch_description');
                    result.push({
                        avatar_id: c.getAttribute('data-avatar-id') || '',
                        name: nameEl ? nameEl.textContent.trim() : '',
                        description: descEl ? descEl.textContent.trim().substring(0, 200) : '',
                    });
                });
                return result;
            }"""
        )
        print(f"[api] 获取到 {len(data)} 个用户设定")
        return data
    except Exception as e:
        print(f"[api] 获取用户设定列表失败: {e}")
        return []


async def select_persona(avatar_id: str) -> bool:
    """通过 avatar_id 选择用户设定"""
    page = get_page()
    try:
        result = await page.evaluate(
            """(avatar_id) => {
                const container = document.querySelector(`#user_avatar_block .avatar-container[data-avatar-id="${avatar_id}"]`);
                if (!container) return false;
                container.click();
                return true;
            }""",
            avatar_id,
        )
        if result:
            print(f"[api] 已选择用户设定: {avatar_id}")
        else:
            print(f"[api] 未找到用户设定: {avatar_id}")
        return bool(result)
    except Exception as e:
        print(f"[api] 选择用户设定失败: {e}")
        return False


async def get_current_persona() -> str:
    """获取当前激活的用户设定名称"""
    page = get_page()
    try:
        name = await page.evaluate(
            "() => window.SillyTavern.getContext().name1 || ''"
        )
        return name
    except Exception as e:
        print(f"[api] 获取当前用户设定失败: {e}")
        return ""


async def delete_chat(file_name: str) -> bool:
    """通过 API 删除指定聊天文件"""
    page = get_page()
    try:
        clean_file = file_name.replace(".jsonl", "")

        await page.evaluate(
            """async (file_name) => {
                const ctx = window.SillyTavern.getContext();
                const headers = ctx.getRequestHeaders();

                const dashIdx = file_name.lastIndexOf(' - ');
                if (dashIdx < 0) throw new Error('Invalid file name');
                const charName = file_name.substring(0, dashIdx);

                let avatar = '';
                for (let i = 0; i < ctx.characters.length; i++) {
                    if (ctx.characters[i] && ctx.characters[i].name === charName) {
                        avatar = ctx.characters[i].avatar;
                        break;
                    }
                }

                const resp = await fetch('/api/chats/delete', {
                    method: 'POST', headers: headers,
                    body: JSON.stringify({
                        ch_name: charName, file_name: file_name, avatar_url: avatar,
                    }),
                });
                if (!resp.ok) throw new Error('Delete failed: ' + resp.status);
                return true;
            }""",
            clean_file,
        )

        await page.wait_for_timeout(500)
        print(f"[api] 已删除聊天: {clean_file}")
        return True
    except Exception as e:
        print(f"[api] 删除聊天失败: {e}")
        return False
