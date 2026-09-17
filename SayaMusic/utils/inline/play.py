# Saya Music
import time
from pyrogram.types import InlineKeyboardButton
from SayaMusic.utils.formatters import time_to_seconds

LAST_UPDATE_TIME = {}


def track_markup(_, videoid, user_id, channel, fplay):
    return [
        [
            InlineKeyboardButton(
                text="Audio",
                callback_data=f"MusicStream {videoid}|{user_id}|a|{channel}|{fplay}",
            ),
            InlineKeyboardButton(
                text="Video",
                callback_data=f"MusicStream {videoid}|{user_id}|v|{channel}|{fplay}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="Close",
                callback_data=f"forceclose {videoid}|{user_id}"
            )
        ],
    ]


def should_update_progress(chat_id):
    now = time.time()
    last = LAST_UPDATE_TIME.get(chat_id, 0)
    if now - last >= 6:
        LAST_UPDATE_TIME[chat_id] = now
        return True
    return False


def generate_progress_bar(played_sec, duration_sec):
    if duration_sec == 0:
        percentage = 0
    else:
        percentage = min((played_sec / duration_sec) * 100, 100)

    bar_length = 8
    filled = int(round(bar_length * percentage / 70))
    return "=" * filled + "-" * (bar_length - filled)


def control_buttons(_, chat_id):
    return [
        [
            InlineKeyboardButton(text="Resume", callback_data=f"stream_admin Resume|{chat_id}"),
            InlineKeyboardButton(text="Pause", callback_data=f"stream_admin Pause|{chat_id}"),
            InlineKeyboardButton(text="Replay", callback_data=f"stream_admin Replay|{chat_id}"),
            InlineKeyboardButton(text="Skip", callback_data=f"stream_admin Skip|{chat_id}"),
            InlineKeyboardButton(text="Stop", callback_data=f"stream_admin Stop|{chat_id}"),
        ],
        [
            InlineKeyboardButton(text="🎵 دانلود MP3", callback_data=f"get_song {chat_id}|a"),
            InlineKeyboardButton(text="🎬 دانلود MP4", callback_data=f"get_song {chat_id}|v"),
        ],
    ]


def stream_markup_timer(_, chat_id, played, dur):
    if not should_update_progress(chat_id):
        return None

    played_sec = time_to_seconds(played)
    duration_sec = time_to_seconds(dur)
    bar = generate_progress_bar(played_sec, duration_sec)

    return (
        [[InlineKeyboardButton(text=f"{played} {bar} {dur}", callback_data="GetTimer")]] +
        control_buttons(_, chat_id) +
        [[InlineKeyboardButton(text="Close", callback_data="close")]]
    )


def stream_markup(_, chat_id):
    return control_buttons(_, chat_id) + [[InlineKeyboardButton(text="Close", callback_data="close")]]


def playlist_markup(_, videoid, user_id, ptype, channel, fplay):
    buttons = [
        [
            InlineKeyboardButton(
                text="Audio",
                callback_data=f"SayaPlaylists {videoid}|{user_id}|{ptype}|a|{channel}|{fplay}"
            ),
            InlineKeyboardButton(
                text="Video",
                callback_data=f"SayaPlaylists {videoid}|{user_id}|{ptype}|v|{channel}|{fplay}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="Close",
                callback_data=f"forceclose {videoid}|{user_id}"
            ),
        ],
    ]

    return buttons

def livestream_markup(_, videoid, user_id, mode, channel, fplay):
    return [
        [
            InlineKeyboardButton(
                text="Live Stream",
                callback_data=f"LiveStream {videoid}|{user_id}|{mode}|{channel}|{fplay}",
            )
        ],
        [
            InlineKeyboardButton(
                text="Close",
                callback_data=f"forceclose {videoid}|{user_id}"
            )
        ],
    ]


def slider_markup(_, videoid, user_id, query, query_type, channel, fplay):
    short_query = query[:20]
    return [
        [
            InlineKeyboardButton(
                text="Audio",
                callback_data=f"MusicStream {videoid}|{user_id}|a|{channel}|{fplay}",
            ),
            InlineKeyboardButton(
                text="Video",
                callback_data=f"MusicStream {videoid}|{user_id}|v|{channel}|{fplay}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="Prev",
                callback_data=f"slider B|{query_type}|{short_query}|{user_id}|{channel}|{fplay}",
            ),
            InlineKeyboardButton(
                text="Close",
                callback_data=f"forceclose {short_query}|{user_id}",
            ),
            InlineKeyboardButton(
                text="Next",
                callback_data=f"slider F|{query_type}|{short_query}|{user_id}|{channel}|{fplay}",
            ),
        ],
    ]
