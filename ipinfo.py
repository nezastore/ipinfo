import logging
import base64
import json
import requests
import asyncio
import nest_asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Memperbaiki event loop
nest_asyncio.apply()

# Konfigurasi Bot Telegram
TOKEN = "7672001478:AAGKmw_FixFyqe4zADaifTc94hVqcW5uvOw"
IP_API_URL = "https://ipwho.is/{}"
DB_FILE = "ip_database.json"

# Konfigurasi GitHub
GITHUB_TOKEN = "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"
GITHUB_REPO = "ipinfo"
GITHUB_FILE_PATH = "ip_database.json"

# Logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

def load_ip_database():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def update_github_file(data):
    """Upload atau update file JSON ke GitHub"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

    # Ambil SHA file jika sudah ada
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        sha = response.json().get("sha")
    else:
        sha = None

    # Encode data JSON ke Base64
    try:
        encoded_content = base64.b64encode(json.dumps(data, indent=4).encode()).decode()
    except Exception as e:
        logging.error(f"⚠️ Gagal encode JSON: {e}")
        return False

    # Payload untuk update ke GitHub
    payload = {
        "message": "Update IP Database",
        "content": encoded_content,
        "sha": sha
    }

    # Kirim request untuk update
    update_response = requests.put(url, headers=headers, json=payload)
    
    if update_response.status_code == 200:
        logging.info("✅ Database berhasil diperbarui di GitHub")
        return True
    else:
        logging.error(f"❌ Gagal memperbarui database di GitHub: {update_response.json()}")
        return False

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Selamat datang! Kirimkan alamat IP untuk mendapatkan informasi.")

async def check_ip(update: Update, context: CallbackContext):
    user_input = update.message.text.strip()
    ip_db = load_ip_database()

    if user_input in ip_db:
        await update.message.reply_text(f"⚠️ IP {user_input} sudah pernah digunakan sebelumnya.")
    else:
        ip_info = lookup_ip(user_input)
        if ip_info:
            ip_db[user_input] = ip_info
            save_ip_database(ip_db)
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
            await update.message.reply_text("❌ Gagal mengambil informasi IP. Coba lagi nanti.")

async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_ip))
    print("✅ Bot berjalan...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
