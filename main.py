import os
from threading import Thread
from flask import Flask
import telebot
import yt_dlp

# --- جزء السيرفر الوهمي عشان ريندر ---
app = Flask("")

@app.route("/")
def home():
    return "البوت شغال بنجاح!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host=\'0.0.0.0\', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()
# -----------------------------------

TOKEN = "7882255866:AAHsH7Wn86uYmS56y96-v4pY4oYy6z2z4u0"
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك! أرسل رابط الفيديو (YouTube, TikTok, Facebook, Instagram) لتحميله.")

@bot.message_handler(func=lambda message: True)
def handle_url_message(message):
    url = message.text
    bot.reply_to(message, "جاري تحليل الرابط والبحث عن الجودات المتاحة، يرجى الانتظار...")

    try:
        ydl_opts = {
            'quiet': True,
            'simulate': True, # Simulate download to get info without actually downloading
            'format': 'bestvideo+bestaudio/best'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            title = info.get('title', 'video')

        keyboard = telebot.types.InlineKeyboardMarkup()
        available_formats = set()

        # Add video formats
        for f in formats:
            if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('ext') == 'mp4':
                height = f.get('height')
                if height and height not in available_formats:
                    keyboard.add(telebot.types.InlineKeyboardButton(text=f"فيديو MP4 - {height}p", callback_data=f"download_video_{url}_{height}p_mp4"))
                    available_formats.add(height)
            elif f.get('vcodec') != 'none' and f.get('ext') == 'mp4': # For formats without audio initially
                height = f.get('height')
                if height and height not in available_formats:
                    keyboard.add(telebot.types.InlineKeyboardButton(text=f"فيديو MP4 - {height}p (بدون صوت)", callback_data=f"download_video_{url}_{height}p_mp4_noaudio"))
                    available_formats.add(height)

        # Add audio format
        if any(f.get('acodec') != 'none' for f in formats):
            keyboard.add(telebot.types.InlineKeyboardButton(text="صوت MP3 فقط", callback_data=f"download_audio_{url}_mp3"))

        if not keyboard.keyboard: # If no formats found
            bot.send_message(message.chat.id, "لم يتم العثور على جودات أو صيغ متاحة لهذا الرابط.")
        else:
            bot.send_message(message.chat.id, f"تم العثور على الفيديو: **{title}**\nالرجاء اختيار الجودة والصيغة المطلوبة:", reply_markup=keyboard, parse_mode='Markdown')

    except Exception as e:
        bot.send_message(message.chat.id, f"حدث خطأ أثناء تحليل الرابط: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('download_'))
def callback_query(call):
    bot.answer_callback_query(call.id, "جاري تجهيز التحميل...")
    
    parts = call.data.split('_')
    action_type = parts[1] # video or audio
    url = parts[2]
    quality_format = parts[3] # e.g., 720p or mp3
    file_ext = parts[4] # e.g., mp4 or mp3

    ydl_opts = {
        'quiet': True,
        'outtmpl': f'{call.from_user.id}_%(title)s.%(ext)s',
        'noplaylist': True,
        'postprocessors': [],
    }

    if action_type == 'video':
        if 'noaudio' in parts:
            ydl_opts['format'] = f'bestvideo[height<={quality_format[:-1]}][ext={file_ext}]'
        else:
            ydl_opts['format'] = f'bestvideo[height<={quality_format[:-1]}][ext={file_ext}]+bestaudio/best[height<={quality_format[:-1]}][ext={file_ext}]'
    elif action_type == 'audio':
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'].append({
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        })
        ydl_opts['outtmpl'] = f'{call.from_user.id}_%(title)s.mp3'

    try:
        bot.edit_message_text("جاري التحميل، قد يستغرق الأمر بعض الوقت...", call.message.chat.id, call.message.message_id)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
        # Check file size before sending
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > 50: # Telegram bot API limit for direct upload is 50MB for bots, 2GB for users
            bot.edit_message_text(f"الملف كبير جداً ({file_size_mb:.2f}MB) ولا يمكن رفعه مباشرة عبر البوت. يرجى استخدام رابط تحميل مباشر إذا كان متاحاً أو محاولة جودة أقل.", call.message.chat.id, call.message.message_id)
            os.remove(file_path) # Clean up large file
            return

        with open(file_path, 'rb') as f:
            if action_type == 'video':
                bot.send_video(call.message.chat.id, f, caption=f"تم تحميل: {info.get('title')}")
            elif action_type == 'audio':
                bot.send_audio(call.message.chat.id, f, caption=f"تم تحميل: {info.get('title')}")
        
        os.remove(file_path)
        bot.edit_message_text("تم التحميل بنجاح!", call.message.chat.id, call.message.message_id)

    except Exception as e:
        bot.edit_message_text(f"حدث خطأ أثناء التحميل: {e}", call.message.chat.id, call.message.message_id)


if __name__ == "__main__":
    keep_alive()
    print("البوت بدأ العمل...")
    bot.polling(none_stop=True)
