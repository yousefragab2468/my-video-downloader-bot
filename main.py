import os
from threading import Thread
from flask import Flask
import telebot
import yt_dlp

# --- السيرفر الوهمي ---
app = Flask("")

@app.route("/")
def home():
    return "البوت شغال بنجاح!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# -------------------------

TOKEN = "8719355025:AAEeFz-f36CdPDbeCFuQjTowq75X9dOR8Js"
bot = telebot.TeleBot(TOKEN)

# ✅ Progress Hook
def create_progress_hook(chat_id, message_id):
    def hook(d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0%').strip()
            try:
                bot.edit_message_text(
                    f"جاري التحميل... {percent}",
                    chat_id=chat_id,
                    message_id=message_id
                )
            except:
                pass

        elif d['status'] == 'finished':
            try:
                bot.edit_message_text(
                    "تم التحميل... جاري الإرسال 📤",
                    chat_id=chat_id,
                    message_id=message_id
                )
            except:
                pass

    return hook


# ✅ start
@bot.message_handler(commands=["start"])
def send_welcome(message):
    username = message.from_user.username
    if username:
        username = "@" + username
    else:
        username = message.from_user.first_name

    text = f"""مرحباً ({username})
هذا البوت مخصص للتحميل من مواقع التواصل الاجتماعي

- YouTube
- pinterest
- TikTok
- Twitter
"""
    bot.reply_to(message, text)


# ✅ استقبال الرابط
@bot.message_handler(content_types=['text'])
def handle_url_message(message):
    url = message.text

    bot.reply_to(message, "جاري تحليل الرابط...")

    try:
        ydl_opts = {
            'quiet': True,
            'simulate': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'video')

        keyboard = telebot.types.InlineKeyboardMarkup()

        keyboard.add(
            telebot.types.InlineKeyboardButton(
                "🎬 Video",
                callback_data=f"type|video|{url}"
            ),
            telebot.types.InlineKeyboardButton(
                "🎧 Audio",
                callback_data=f"type|audio|{url}"
            )
        )

        bot.send_message(
            message.chat.id,
            f"اختار الصيغة:\n{title}",
            reply_markup=keyboard
        )

    except Exception as e:
        bot.send_message(message.chat.id, f"خطأ: {e}")


# ✅ الأزرار
@bot.callback_query_handler(func=lambda call: True)
def download(call):
    bot.answer_callback_query(call.id)

    data = call.data.split("|")

    # اختيار النوع
    if data[0] == "type":
        choice = data[1]
        url = data[2]

        # 🎬 Video
        if choice == "video":
            try:
                ydl_opts = {
                    'quiet': True,
                    'simulate': True
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    formats = info.get('formats', [])
                    title = info.get('title', 'video')

                keyboard = telebot.types.InlineKeyboardMarkup()
                added = set()

                for f in formats:
                    if f.get('ext') == 'mp4' and f.get('height'):
                        h = f.get('height')
                        if h not in added:
                            keyboard.add(
                                telebot.types.InlineKeyboardButton(
                                    text=f"{h}p",
                                    callback_data=f"video|{url}|{h}"
                                )
                            )
                            added.add(h)

                bot.send_message(
                    call.message.chat.id,
                    f"اختر الجودة:\n{title}",
                    reply_markup=keyboard
                )

            except Exception as e:
                bot.send_message(call.message.chat.id, f"خطأ: {e}")

        # 🎧 Audio
        elif choice == "audio":
            try:
                msg = bot.send_message(call.message.chat.id, "جاري التحميل... 0%")

                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': 'audio.%(ext)s',
                    'quiet': True,
                    'progress_hooks': [create_progress_hook(call.message.chat.id, msg.message_id)]
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    file = ydl.prepare_filename(info)

                mp3_file = file.rsplit(".", 1)[0] + ".mp3"
                os.rename(file, mp3_file)

                with open(mp3_file, 'rb') as f:
                    bot.send_audio(call.message.chat.id, f)

                os.remove(mp3_file)

                bot.edit_message_text(
                    "تم التحميل بنجاح 🎧",
                    chat_id=msg.chat.id,
                    message_id=msg.message_id
                )

            except Exception as e:
                bot.send_message(call.message.chat.id, f"فشل التحميل: {e}")

    # 🎬 تحميل الفيديو
    elif data[0] == "video":
        url = data[1]
        quality = data[2]

        msg = bot.send_message(call.message.chat.id, "جاري التحميل... 0%")

        ydl_opts = {
            'format': f'bestvideo[height<={quality}]+bestaudio/best',
            'outtmpl': 'video.%(ext)s',
            'quiet': True,
            'progress_hooks': [create_progress_hook(call.message.chat.id, msg.message_id)]
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file = ydl.prepare_filename(info)

            with open(file, 'rb') as f:
                bot.send_video(call.message.chat.id, f)

            os.remove(file)

            bot.edit_message_text(
                "تم التحميل بنجاح ✅",
                chat_id=msg.chat.id,
                message_id=msg.message_id
            )

        except Exception as e:
            bot.send_message(call.message.chat.id, f"فشل التحميل: {e}")


if __name__ == "__main__":
    keep_alive()
    print("البوت بدأ العمل...")
    bot.infinity_polling()
