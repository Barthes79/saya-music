# Saya Music
import asyncio
import os

from pyrogram import filters
from pyrogram.errors import FloodWait
from pyrogram.types import CallbackQuery, Message
from yt_dlp import YoutubeDL

from config import BANNED_USERS, SONG_DOWNLOAD_DURATION_LIMIT
from SayaMusic import YouTube, app
from SayaMusic.core.dir import DOWNLOAD_DIR
from SayaMusic.misc import db
from SayaMusic.utils.cookie_handler import COOKIE_PATH
from SayaMusic.utils.decorators.language import language, languageCB
from SayaMusic.utils.formatters import time_to_seconds
from SayaMusic.utils.thumbnails import get_thumb


def _cookiefile():
    try:
        if COOKIE_PATH and os.path.exists(COOKIE_PATH) and os.path.getsize(COOKIE_PATH) > 0:
            return str(COOKIE_PATH)
    except Exception:
        pass
    return None


# روی هر کانتینر لینوکسی (Railway هم همین‌طوره) مسیر /dev/shm یک فضای در حافظه‌ی
# RAM هست، نه دیسک واقعی. اگه در دسترس و قابل نوشتن باشه، فایل موقت دانلود رو
# همون‌جا می‌سازیم تا هیچ‌وقت واقعاً روی Storage کانتینر ننشینه؛ در غیر این
# صورت (مثلاً روی هاست‌هایی که /dev/shm ندارن) به همون فولدر معمولی برمی‌گردیم.
def _pick_tmp_dir() -> str:
    shm = "/dev/shm/saya_dl"
    try:
        os.makedirs(shm, exist_ok=True)
        test_file = os.path.join(shm, ".write_test")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        return shm
    except Exception:
        return DOWNLOAD_DIR


TMP_DIR = _pick_tmp_dir()


def _too_long(duration_min: str) -> bool:
    if not duration_min:
        return False
    try:
        return time_to_seconds(duration_min) > SONG_DOWNLOAD_DURATION_LIMIT
    except Exception:
        return False


# فایل‌های دانلودشده با پیشوند dl_ و پسوند audio/video ذخیره می‌شن؛ این عمداً
# جدا از کش پخش‌زنده‌ی خود بات (که فقط بر اساس id.ext هست و نوع فایل رو تشخیص
# نمی‌ده) نگه داشته می‌شه، تا درخواست MP3 هیچ‌وقت یک فایل ویدیویی کش‌شده رو
# برنگردونه و برعکس.
def _cached_path(vidid: str, video: bool):
    suffix = "video" if video else "audio"
    ext = "mp4" if video else "mp3"
    path = f"{TMP_DIR}/dl_{vidid}_{suffix}.{ext}"
    return path if os.path.exists(path) else None


def _download_sync(link: str, vidid: str, video: bool) -> "str | None":
    suffix = "video" if video else "audio"
    outtmpl = f"{TMP_DIR}/dl_%(id)s_{suffix}.%(ext)s"

    if video:
        opts = {
            "outtmpl": outtmpl,
            "format": "bv*[ext=mp4][height<=?720]+ba[ext=m4a]/b[ext=mp4]/best",
            "merge_output_format": "mp4",
        }
    else:
        opts = {
            "outtmpl": outtmpl,
            "format": "bestaudio/best",
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
            ],
        }

    opts.update(
        {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "overwrites": False,
            "retries": 2,
        }
    )
    if cookiefile := _cookiefile():
        opts["cookiefile"] = cookiefile

    try:
        with YoutubeDL(opts) as ydl:
            ydl.extract_info(link, download=True)
    except Exception:
        return None

    ext = "mp4" if video else "mp3"
    path = f"{TMP_DIR}/dl_{vidid}_{suffix}.{ext}"
    return path if os.path.exists(path) else None


async def _get_file(vidid: str, video: bool) -> "str | None":
    if cached := _cached_path(vidid, video):
        return cached
    link = f"https://www.youtube.com/watch?v={vidid}"
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _download_sync, link, vidid, video)


async def _send_track(chat_id: int, mystic: Message, vidid: str, title: str, video: bool):
    path = await _get_file(vidid, video)
    if not path:
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
            await app.send_video(chat_id, path, caption=title, thumb=thumb, supports_streaming=True)
        else:
            await app.send_audio(chat_id, path, caption=title, thumb=thumb, title=title)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        if video:
            await app.send_video(chat_id, path, caption=title, thumb=thumb, supports_streaming=True)
        else:
            await app.send_audio(chat_id, path, caption=title, thumb=thumb, title=title)
    except Exception as e:
        return await mystic.edit_text(f"آپلود فایل با خطا مواجه شد: {e}")
    finally:
        # فایل روی هارد سرور دیگه لازم نیست؛ تلگرام از همین به بعد خودش نسخه رو نگه می‌داره.
        # اگه این خط رو حذف کنی، فایل‌ها برای همیشه روی دیسک سرور جمع می‌شن.
        try:
            os.remove(path)
        except Exception:
            pass

    await mystic.delete()


# /song <query یا لینک>   -> MP3
# /vsong <query یا لینک>  -> MP4
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

    await _send_track(message.chat.id, mystic, vidid, details.get("title") or "Track", video)


# دکمه‌های «دانلود MP3» و «دانلود MP4» روی پنل پخش زنده
# callback_data به این شکل ساخته می‌شه: "get_song {chat_id}|a"  یا  "get_song {chat_id}|v"
@app.on_callback_query(filters.regex("^get_song") & ~BANNED_USERS)
@languageCB
async def get_song_callback(client, callback: CallbackQuery, _):
    payload = callback.data.split(None, 1)[1]
    chat_id_str, _sep, mode = payload.partition("|")
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
    await _send_track(callback.message.chat.id, mystic, vidid, title, video)
