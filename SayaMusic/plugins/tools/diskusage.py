# Saya Music
import os

from pyrogram import filters
from pyrogram.types import Message

from config import BANNED_USERS
from SayaMusic import app
from SayaMusic.core.dir import CACHE_DIR, DOWNLOAD_DIR
from SayaMusic.misc import SUDOERS


def _human(size: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _folder_report(path: str):
    if not os.path.isdir(path):
        return 0, []
    entries = []
    total = 0
    for name in os.listdir(path):
        fp = os.path.join(path, name)
        if os.path.isfile(fp):
            size = os.path.getsize(fp)
            total += size
            entries.append((name, size))
    entries.sort(key=lambda x: x[1], reverse=True)
    return total, entries


# فقط برای ادمین‌های اصلی بات (SUDOERS)
@app.on_message(filters.command(["diskusage", "downloads"]) & ~BANNED_USERS)
async def disk_usage(client, message: Message):
    if message.from_user.id not in SUDOERS:
        return await message.reply_text("این دستور فقط برای ادمین‌های بات است.")

    dl_total, dl_files = _folder_report(DOWNLOAD_DIR)
    cache_total, cache_files = _folder_report(CACHE_DIR)

    text = (
        f"📁 پوشه‌ی downloads: {_human(dl_total)} ({len(dl_files)} فایل)\n"
        f"📁 پوشه‌ی cache: {_human(cache_total)} ({len(cache_files)} فایل)\n"
        f"📦 مجموع: {_human(dl_total + cache_total)}\n"
    )

    top = dl_files[:10]
    if top:
        text += "\nبزرگ‌ترین فایل‌های downloads:\n"
        for name, size in top:
            text += f"• {name} — {_human(size)}\n"

    await message.reply_text(text)


# پاک کردن دستی همه‌ی فایل‌های فولدر downloads
# هشدار: اگه هم‌زمان در گروهی موزیک در حال پخشه، ممکنه فایل همون ترک هم پاک شه
# و پخش قطع شه؛ بهتره این دستور رو وقتی هیچ گروهی در حال پخش نیست بزنی.
@app.on_message(filters.command(["cleardownloads"]) & ~BANNED_USERS)
async def clear_downloads(client, message: Message):
    if message.from_user.id not in SUDOERS:
        return await message.reply_text("این دستور فقط برای ادمین‌های بات است.")

    removed, freed = 0, 0
    if os.path.isdir(DOWNLOAD_DIR):
        for name in os.listdir(DOWNLOAD_DIR):
            fp = os.path.join(DOWNLOAD_DIR, name)
            if os.path.isfile(fp):
                try:
                    freed += os.path.getsize(fp)
                    os.remove(fp)
                    removed += 1
                except Exception:
                    pass

    await message.reply_text(
        f"{removed} فایل حذف شد، {_human(freed)} فضا آزاد شد.\n"
        "توجه: اگه هم‌زمان جایی موزیک پخش می‌شد، ممکنه لازم باشه دوباره /play بزنن."
    )
