import logging
import json
import requests
import asyncio
import nest_asyncio
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Memperbaiki event loop (hindari error di Jupyter / runtime async)
nest_asyncio.apply()

# Konfigurasi Bot Telegram (API Token TIDAK diubah)
TOKEN = "7672001478:AAGKmw_FixFyqe4zADaifTc94hVqcW5uvOw"

# Konfigurasi API IP Lookup
IP_API_URL = "https://ipwho.is/{}"

# Konfigurasi Google Sheets
SPREADSHEET_ID = "1GrxbYHdXzcdFna"
GOOGLE_CREDENTIALS_FILE = "dataiplinode-1df59f53d098.json"

# Logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# Load kredensial Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1  # Menggunakan sheet pertama


def lookup_ip(ip):
    """Mencari informasi IP menggunakan IPWho API"""
    response = requests.get(IP_API_URL.format(ip))
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            return {
                "ip": data.get("ip"),
                "country": data.get("country"),
                "region": data.get("region"),
                "city": data.get("city"),
                "isp": data.get("isp"),
                "org": data.get("org"),
                "lat": data.get("latitude"),
                "lon": data.get("longitude")
            }
    return None


def load_ip_database():
    """Memuat database IP dari Google Sheets"""
    try:
        data = sheet.get_all_records()
        return {row["IP"]: row for row in data}
    except Exception as e:
        logging.error(f"❌ Gagal memuat database dari Google Sheets: {e}")
        return {}


def save_to_google_sheets(ip, data):
    """Simpan data IP ke Google Sheets"""
    try:
        row = [ip, data["country"], data["region"], data["city"], data["isp"], data["lat"], data["lon"]]
        sheet.append_row(row)
        logging.info("✅ Data berhasil disimpan ke Google Sheets")
        return True
    except Exception as e:
        logging.error(f"❌ Gagal menyimpan data ke Google Sheets: {e}")
        return False


async def start(update: Update, context: CallbackContext):
    """Menjalankan command /start"""
    await update.message.reply_text("🚀 Selamat datang! Kirimkan alamat IP untuk mendapatkan informasi.")


async def check_ip(update: Update, context: CallbackContext):
    """Mengecek apakah IP valid dan menyimpan ke Google Sheets"""
    user_input = update.message.text.strip()
    ip_db = load_ip_database()

    if user_input in ip_db:
        await update.message.reply_text(f"⚠️ IP {user_input} sudah pernah digunakan.")
    else:
        ip_info = lookup_ip(user_input)
        if ip_info:
            saved = save_to_google_sheets(user_input, ip_info)
            
            google_maps_link = f"https://www.google.com/maps?q={ip_info['lat']},{ip_info['lon']}"
            keyboard = [[InlineKeyboardButton("📍 Lihat di Google Maps", url=google_maps_link)]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            message = (
                f"🔍 **Hasil Pencarian IP:**\n"
                f"📍 **IP:** `{ip_info['ip']}`\n"
                f"🌍 **Negara:** {ip_info['country']}\n"
                f"🏙 **Wilayah:** {ip_info['region']}\n"
                f"🏡 **Kota:** {ip_info['city']}\n"
                f"📡 **ISP:** {ip_info['isp']}\n"
                f"📌 **Latitude:** {ip_info['lat']}, **Longitude:** {ip_info['lon']}\n"
                f"✅ **Data {'berhasil' if saved else 'gagal'} disimpan ke Google Sheets**"
            )
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Gagal mengambil informasi IP. Pastikan format benar.")


async def main():
    """Menjalankan bot Telegram"""
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_ip))
    logging.info("✅ Bot berjalan...")
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
