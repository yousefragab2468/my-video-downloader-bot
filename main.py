import os
from threading import Thread
from flask import Flask
import telebot
import yt_dlp

# --- جزء السيرفر الوهمي ---
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

TOKEN = "8719355025:AAEeFz-f36CdPDbeCFuQjTowq75X9dOR8Js"  # حط التوكن الجديد هنا
bot = telebot.TeleBot(TOKEN)

# ✅ رسالة start الجديدة
@bot.message_handler(commands=["start"])
def send_welcome(message):
    username = message.from_user.username
    if username:
        username = "@" + username
    else:
        username = message.from_user.first_name

    text = f"""مرحباً ({username})
هذا البوت مخصص للتحميل من مواقع التواصل الاجتماعي

هذه هي المواقع التي يدعمها البوت حالياً:

- Snapchat
- Instagram
- YouTube
- TikTok
- Twitter
- Pinterest
"""
    bot.reply_to(message, text)


# ✅ استقبال الروابط فقط
@bot.message_handler(content_types=['text'])
def handle_url_message(message):
    url = message.text

    bot.reply_to(message, "جاري تحليل الرابط...")

    try:
        ydl_opts = {
            'quiet': True,
            'simulate': True,
            'format': 'bestvideo+bestaudio/best'
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
                            callback_data=f"{url}|{h}"
                        )
                    )
                    added.add(h)

        if not keyboard.keyboard:
            bot.send_message(message.chat.id, "مفيش جودات متاحة.")
        else:
            bot.send_message(
                message.chat.id,
                f"اختر الجودة:\n{title}",
                reply_markup=keyboard
            )

    except Exception as e:
        bot.send_message(message.chat.id, f"خطأ: {e}")


# ✅ تحميل الفيديو
@bot.callback_query_handler(func=lambda call: True)
def download(call):
    bot.answer_callback_query(call.id)

    url, quality = call.data.split("|")

    ydl_opts = {
        'format': f'bestvideo[height<={quality}]+bestaudio/best',
        'outtmpl': 'video.%(ext)s',
        'quiet': True
    }

    try:
        bot.send_message(call.message.chat.id, "جاري التحميل...")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file = ydl.prepare_filename(info)

        with open(file, 'rb') as f:
            bot.send_video(call.message.chat.id, f)

        os.remove(file)

    except Exception as e:
        bot.send_message(call.message.chat.id, f"فشل التحميل: {e}")


if __name__ == "__main__":
    keep_alive()
    print("البوت بدأ العمل...")
    bot.infinity_polling()
