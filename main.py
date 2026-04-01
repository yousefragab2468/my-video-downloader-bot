import os
import asyncio
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# إعداد السجلات (Logging)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = '8719355025:AAHeHgMihbLTZ4QSopLek_MXJznsrjwsltk'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً بك في بوت تحميل الفيديوهات السريع! 🚀🎥\n\n"
        "أرسل لي رابط الفيديو من:\n"
        "Snapchat, Instagram, YouTube, TikTok, Twitter, Pinterest\n\n"
        "سأقوم بالتحميل بأفضل جودة متاحة."
    )

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith('http'):
        return

    status_message = await update.message.reply_text("جاري فحص الرابط والتحميل... ⏳")
    
    # إعدادات yt-dlp محسنة
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', # محاولة الحصول على MP4 لضمان التشغيل
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'socket_timeout': 30, # مهلة زمنية للاتصال
    }

    try:
        if not os.path.exists('downloads'):
            os.makedirs('downloads')

        # استخدام thread لتجنب تجميد البوت أثناء التحميل
        def extract_and_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info), info

        filename, info = await asyncio.to_thread(extract_and_download)
        
        await status_message.edit_text("جاري رفع الفيديو إلى تليجرام... 📤")
        
        # التأكد من حجم الملف (تليجرام يسمح حتى 50MB للبوتات العادية)
        file_size = os.path.getsize(filename) / (1024 * 1024)
        if file_size > 50:
            await status_message.edit_text(f"عذراً، حجم الفيديو كبير جداً ({file_size:.1f}MB). تليجرام يسمح بـ 50MB فقط.")
        else:
            with open(filename, 'rb') as video_file:
                await update.message.reply_video(
                    video=video_file, 
                    caption=f"✅ تم التحميل بنجاح!\n\n📌 {info.get('title', 'بدون عنوان')}",
                    supports_streaming=True
                )
            await status_message.delete()
        
        # تنظيف الملفات
        if os.path.exists(filename):
            os.remove(filename)

    except Exception as e:
        logging.error(f"Error: {e}")
        error_msg = str(e)
        if "Timed out" in error_msg:
            await status_message.edit_text("حدث تأخير في الاستجابة من الموقع. حاول مرة أخرى لاحقاً. ⏳")
        else:
            await status_message.edit_text("عذراً، حدث خطأ أثناء التحميل. تأكد من أن الرابط صحيح. ❌")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), download_video))
    
    print("البوت يعمل الآن بأداء محسن...")
    application.run_polling()
