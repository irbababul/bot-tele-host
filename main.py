import os
import asyncio
import io
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai
from PIL import Image
import img2pdf
from docx import Document
from PyPDF2 import PdfReader
from pdf2docx import Converter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import yt_dlp
import nest_asyncio

nest_asyncio.apply()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

model = None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash-exp")

async def mulai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Halo, selamat datang di Bot Salas! 🤖\n\nGunakan /fitur untuk melihat semua kemampuan bot.")

async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Berikut link portfolio saya: https://irbababul.github.io/irbabulsalass/")

async def biodata(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("""
Berikut biodata saya:

Nama : Muhammad Irbabul Salas
Umur : 215 bulan
NPM  : 25083010055
""")

async def fitur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("""
🤖 Berikut Fitur-Fitur Bot Salas:

1. 💬 Tanya apapun dijawab dengan AI
2. 🎭 Ubah Foto menjadi Stiker - kirim foto dengan caption ".s"
3. 📄 Word to PDF - kirim file .docx
4. 📝 PDF to Word - kirim file .pdf dengan caption "toword"
5. 🖼️ JPG to PDF - kirim gambar dengan caption "topdf"
6. 🎬 Download video TikTok - kirim link TikTok
7. 📹 Download video Instagram - kirim link Instagram

Kirim pesan untuk mulai menggunakan bot!
""")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.photo:
        return
        
    try:
        photo = update.message.photo[-1]
        caption = update.message.caption or ""
        
        if caption.lower() == ".s":
            await update.message.reply_text("Sedang membuat stiker...")
            
            file = await photo.get_file()
            photo_bytes = await file.download_as_bytearray()
            
            img = Image.open(io.BytesIO(photo_bytes))
            
            max_size = 512
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            sticker_io = io.BytesIO()
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            img.save(sticker_io, format='WEBP')
            sticker_io.seek(0)
            
            await update.message.reply_sticker(sticker=sticker_io)
            
        elif caption.lower() == "topdf":
            await update.message.reply_text("Mengonversi gambar ke PDF...")
            
            file = await photo.get_file()
            photo_bytes = await file.download_as_bytearray()
            
            pdf_bytes = img2pdf.convert(bytes(photo_bytes))
            pdf_io = io.BytesIO(pdf_bytes)
            
            await update.message.reply_document(
                document=pdf_io,
                filename="gambar.pdf"
            )
        else:
            await update.message.reply_text("Kirim foto dengan caption:\n- '.s' untuk stiker\n- 'topdf' untuk konversi ke PDF")
            
    except Exception as e:
        if update.message:
            await update.message.reply_text(f"Terjadi kesalahan: {str(e)}")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.document:
        return
        
    try:
        document = update.message.document
        caption = update.message.caption or ""
        file_name = document.file_name or ""
        
        if file_name.endswith('.docx'):
            await update.message.reply_text("Mengonversi Word ke PDF...")
            
            file = await document.get_file()
            docx_bytes = await file.download_as_bytearray()
            
            docx_io = io.BytesIO(docx_bytes)
            doc = Document(docx_io)
            
            pdf_io = io.BytesIO()
            c = canvas.Canvas(pdf_io, pagesize=letter)
            width, height = letter
            y_position = height - 50
            
            for paragraph in doc.paragraphs:
                if y_position < 50:
                    c.showPage()
                    y_position = height - 50
                
                text = paragraph.text[:100]
                c.drawString(50, y_position, text)
                y_position -= 20
            
            c.save()
            pdf_io.seek(0)
            
            await update.message.reply_document(
                document=pdf_io,
                filename="dokumen.pdf"
            )
            
        elif file_name.endswith('.pdf') and caption.lower() == "toword":
            await update.message.reply_text("Mengonversi PDF ke Word...")
            
            file = await document.get_file()
            pdf_bytes = await file.download_as_bytearray()
            
            with open("temp.pdf", "wb") as f:
                f.write(pdf_bytes)
            
            cv = Converter("temp.pdf")
            cv.convert("temp.docx")
            cv.close()
            
            with open("temp.docx", "rb") as f:
                await update.message.reply_document(
                    document=f,
                    filename="dokumen.docx"
                )
            
            if os.path.exists("temp.pdf"):
                os.remove("temp.pdf")
            if os.path.exists("temp.docx"):
                os.remove("temp.docx")
            
        else:
            await update.message.reply_text(
                "Kirim file:\n"
                "- .docx untuk konversi ke PDF\n"
                "- .pdf dengan caption 'toword' untuk konversi ke Word"
            )
            
    except Exception as e:
        if update.message:
            await update.message.reply_text(f"Terjadi kesalahan: {str(e)}")

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return False
        
    url = update.message.text
    
    if "tiktok.com" in url or "instagram.com" in url or "reel" in url:
        try:
            await update.message.reply_text("Mengunduh video... Mohon tunggu.")
            
            ydl_opts = {
                'format': 'best',
                'outtmpl': 'downloads/%(title)s.%(ext)s',
                'quiet': True,
                'no_warnings': True,
            }
            
            os.makedirs("downloads", exist_ok=True)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
            
            if os.path.exists(filename):
                with open(filename, 'rb') as video:
                    await update.message.reply_video(
                        video=video,
                        caption="✅ Video berhasil diunduh!"
                    )
                
                os.remove(filename)
            else:
                await update.message.reply_text("Gagal mengunduh video. Coba lagi.")
                
        except Exception as e:
            if update.message:
                await update.message.reply_text(f"Terjadi kesalahan saat mengunduh: {str(e)}")
        
        return True
    
    return False

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
        
    pesan_user = update.message.text
    
    if pesan_user.lower() == "portfolio":
        await update.message.reply_text("Berikut link portfolio saya: https://irbababul.github.io/irbabulsalass/")
        return
    
    video_downloaded = await download_video(update, context)
    if video_downloaded:
        return
    
    if not model:
        await update.message.reply_text("API Key Gemini belum diatur. Hubungi admin.")
        return
    
    try:
        await update.message.reply_text("Bot Salas sedang mengetik...")
        response = model.generate_content(pesan_user)
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text(f"Terjadi kesalahan: {str(e)}")

def main():
    if not TELEGRAM_TOKEN:
        print("ERROR: TELEGRAM_TOKEN tidak ditemukan. Silakan atur di Secrets.")
        return
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("mulai", mulai))
    app.add_handler(CommandHandler("start", mulai))
    app.add_handler(CommandHandler("biodata", biodata))
    app.add_handler(CommandHandler("fitur", fitur))
    app.add_handler(CommandHandler("portfolio", portfolio))
    
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    print("✅ Bot Salas sedang berjalan...")
    print("🤖 Tekan Ctrl+C untuk menghentikan bot")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
