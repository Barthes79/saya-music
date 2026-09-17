# Saya Music
import os

from pyrogram import filters
from pyrogram.errors import FloodWait
from pyrogram.types import CallbackQuery, Message

import config
from config import BANNED_USERS, SONG_DOWNLOAD_DURATION_LIMIT
from SayaMusic import YouTube, app
from SayaMusic.misc import db
from SayaMusic.utils.decorators.language import language, languageCB
from SayaMusic.utils.formatters import seconds_to_min, time_to_seconds
from SayaMusic.utils.thumbnails import get_thumb


def _too_long(duration_min: str) -> bool:
    if not duration_min:
        return False
    try:
        return time_to_seconds(duration_min) > SONG_DOWNLOAD_DURATION_LIMIT
    except Exception:
        return False


async def _send_track(chat_id: int, mystic: Message, link: str, vidid: str, title: str, video: bool):
    path, _ = await YouTube.download(link, mystic, video=video, videoid=vidid)
    if not path or not os.path.exists(path):
        return await mystic.edit_text("دانلود این ترک ممکن نشد، دوباره تلاش کن.")

    thumb = None
    try:
        thumb = await get_thumb(vidid)
        if thumb and not os.path.exists(thumb):
            thumb = None
    except Exception:
        thumb = None

    try:
        if video:
            await app.send_video(
                chat_id, path, caption=title, thumb=thumb, supports_streaming=True
            )
        else:
            await app.send_audio(chat_id, path, caption=title, thumb=thumb, title=title)
    except FloodWait as e:
        import asyncio
        await asyncio.sleep(e.value)
        if video:
            await app.send_video(chat_id, path, caption=title, thumb=thumb, supports_streaming=True)
        else:
            await app.send_audio(chat_id, path, caption=title, thumb=thumb, title=title)
    except Exception as e:
        return await mystic.edit_text(f"آپلود فایل با خطا مواجه شد: {e}")

    await mystic.delete()


# /song <query یا لینک>   |   /vsong برای نسخه ویدیویی
@app.on_message(filters.command(["song", "vsong"]) & ~BANNED_USERS)
@language
async def song_download(client, message: Message, _):
    video = message.command[0] == "vsong"

    query = None
    if len(message.command) > 1:
        query = message.text.split(None, 1)[1].strip()
    elif message.reply_to_message and message.reply_to_message.text:
        query = message.reply_to_message.text.strip()

    if not query:
        return await message.reply_text(
            "بعد از دستور، اسم آهنگ یا لینک یوتیوب رو بنویس.\nمثال: `/song Shadmehr Aghili Ghadim`"
        )

    mystic = await message.reply_text("در حال جست‌وجو و دانلود ترک، چند لحظه صبر کن...")

    try:
        details, vidid = await YouTube.track(query)
    except Exception as e:
        return await mystic.edit_text(f"چیزی پیدا نشد: {e}")

    if _too_long(details.get("duration_min")):
        return await mystic.edit_text(
            f"این ترک طولانی‌تر از حد مجاز برای دانلود ({SONG_DOWNLOAD_DURATION_LIMIT // 60} دقیقه) هست."
        )

    await _send_track(
        message.chat.id, mystic, details.get("link") or query, vidid, details.get("title") or "Track", video
    )


# دکمه‌های «دانلود MP3» و «دانلود MP4» روی پنل پخش زنده
# callback_data به این شکل ساخته می‌شه: "get_song {chat_id}|a"  یا  "get_song {chat_id}|v"
@app.on_callback_query(filters.regex("^get_song") & ~BANNED_USERS)
@languageCB
async def get_song_callback(client, callback: CallbackQuery, _):
    payload = callback.data.split(None, 1)[1]
    chat_id_str, _, mode = payload.partition("|")
    chat_id = int(chat_id_str)
    video = mode == "v"

    queue = db.get(chat_id)
    if not queue:
        return await callback.answer("در حال حاضر چیزی پخش نمی‌شه.", show_alert=True)

    current = queue[0]
    vidid = current.get("vidid")
    if not vidid or "live_" in str(current.get("file", "")):
        return await callback.answer("این مورد قابل دانلود نیست (پخش زنده / فایل تلگرامی).", show_alert=True)

    title = current.get("title") or "Track"
    label = "MP4" if video else "MP3"
    await callback.answer(f"در حال آماده‌سازی {label}، فایل رو برات می‌فرستم...", show_alert=False)

    mystic = await callback.message.reply_text(f"در حال دانلود «{title}» ({label})...")
    await _send_track(callback.message.chat.id, mystic, vidid, vidid, title, video=video)
