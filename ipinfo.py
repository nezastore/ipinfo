import logging
import json
import aiohttp
import asyncio
import nest_asyncio
import gspread
import ipaddress
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Fix event loop
nest_asyncio.apply()

# Token Bot Telegram
TOKEN = "7672001478:AAGKmw_FixFyqe4zADaifTc94hVqcW5uvOw"

# API IP Lookup
IP_API_URL = "https://ipwho.is/{}"
IP_BLACKLIST_URL = "https://blacklistapi.com/api/v1/{}"  # Contoh URL untuk pengecekan blacklist

# Google Sheets Configuration
GOOGLE_CREDENTIALS_FILE = "dataiplinode-1df59f53d098.json"  # Pastikan file ini tersedia
SPREADSHEET_ID = "1GrxbYHdXzcdFna_-yywJXGNCPZHt__ug9PS9l2efKy8"  # Ganti dengan Spreadsheet ID yang benar

# Setup Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1  # Menggunakan sheet pertama

# Logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

def is_valid_ip(ip):
    """Cek apakah format IP yang dimasukkan valid (IPv4/IPv6)"""
    try:
        ipaddress.ip_address(ip)  # Cek format IP
        return True
    except ValueError:
        return False

async def lookup_ip(ip):
    """Mencari informasi IP menggunakan IPWhois API secara asinkron."""
    async with aiohttp.ClientSession() as session:
        async with session.get(IP_API_URL.format(ip)) as response:
            if response.status == 200:
                data = await response.json()
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

async def check_blacklist(ip):
    """Cek apakah IP ada dalam daftar hitam (blacklist)"""
    async with aiohttp.ClientSession() as session:
        async with session.get(IP_BLACKLIST_URL.format(ip)) as response:
            if response.status == 200:
                data = await response.json()
                # Misalnya kalau data "blacklisted" true, berarti IP di blacklist
                return data.get("blacklisted", False)
    return False

def is_ip_in_sheet(ip):
    """Cek apakah IP sudah ada di Google Sheets"""
    ip_list = sheet.col_values(1)  # Ambil semua IP di kolom pertama
    return ip in ip_list

def save_ip_to_sheet(ip_info):
    """Simpan IP ke Google Sheets jika belum ada"""
    if not is_ip_in_sheet(ip_info["ip"]):  # Cek apakah IP sudah ada
        sheet.append_row([
            ip_info["ip"], ip_info["country"], ip_info["region"], ip_info["city"],
            ip_info["isp"], ip_info["org"], ip_info["lat"], ip_info["lon"]
        ])
        return True
    return False  # Jika sudah ada, tidak menyimpan ulang

async def start(update: Update, context: CallbackContext):
    """Menangani perintah /start"""
    await update.message.reply_text("Selamat datang! Kirimkan alamat IP untuk mendapatkan informasi.")

async def check_ip(update: Update, context: CallbackContext):
    """Menangani pengecekan IP yang diberikan pengguna"""
    user_input = update.message.text.strip()
    
    # Cek apakah IP valid
    if not is_valid_ip(user_input):
        await update.message.reply_text("❌ Format IP tidak valid! Pastikan formatnya benar (IPv4/IPv6).")
        return
    
    # Cek apakah IP sudah ada di database
    if is_ip_in_sheet(user_input):
        await update.message.reply_text(f"⚠️ *IP {user_input} sudah pernah digunakan!*", parse_mode="Markdown")
        return  # Hentikan eksekusi lebih lanjut jika IP sudah tersimpan
    
    ip_info = await lookup_ip(user_input)
    
    if ip_info:
        # Cek blacklist
        blacklisted = await check_blacklist(user_input)
        if blacklisted:
            await update.message.reply_text(f"⚠️ *IP {user_input} terdeteksi sebagai IP yang diblacklist!*")
            return
        
        success = save_ip_to_sheet(ip_info)
        if success:
            google_maps_link = f"https://www.google.com/maps?q={ip_info['lat']},{ip_info['lon']}"
            keyboard = [[InlineKeyboardButton("🗺 Lihat di Google Maps", url=google_maps_link)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message = (
                f"🔍 **Hasil Pencarian IP:**\n"
                f"📍 **IP:** `{ip_info['ip']}`\n"
                f"🌍 **Negara:** {ip_info['country']}\n"
                f"🏙 **Wilayah:** {ip_info['region']}\n"
                f"🏡 **Kota:** {ip_info['city']}\n"
                f"📡 **ISP:** {ip_info['isp']}\n"
                f"🏢 **Organisasi:** {ip_info['org']}\n"
                f"📌 **Latitude:** {ip_info['lat']}, **Longitude:** {ip_info['lon']}\n"
            )
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await update.message.reply_text(f"IP {user_input} sudah ada di database.")
    else:
        await update.message.reply_text(f"❌ Gagal menemukan informasi untuk IP {user_input}. Periksa kembali IP yang Anda masukkan.")

async def main():
    """Menjalankan bot dengan polling"""
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_ip))
    logging.info("✅ Bot berjalan...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
