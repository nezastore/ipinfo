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
GITHUB_TOKEN = "ghp_YOUR_GITHUB_TOKEN"  # Ganti dengan token GitHub yang valid
GITHUB_REPO = "nezastore/ipinfo"
GITHUB_FILE_PATH = "ip_database.json"

# Logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)


def load_ip_database():
    """Memuat database IP dari file lokal"""
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_ip_database(data):
    """Menyimpan database IP ke file lokal"""
    try:
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=4)
        logging.info("✅ Database lokal berhasil diperbarui")
    except Exception as e:
        logging.error(f"❌ Gagal menyimpan database lokal: {e}")


def get_file_sha():
    """Mengambil SHA file yang ada di GitHub"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("sha")
    return None


def update_github_file(data):
    """Upload atau update file JSON ke GitHub"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    encoded_content = base64.b64encode(json.dumps(data, indent=4).encode()).decode()
    sha = get_file_sha()
    payload = {"message": "Update IP Database", "content": encoded_content, "sha": sha}
    response = requests.put(url, headers=headers, json=payload)
    if response.status_code in [200, 201]:
        logging.info("✅ Database berhasil diperbarui di GitHub")
    else:
        logging.error(f"❌ Gagal update GitHub: {response.json()}")


def lookup_ip(ip):
    """Mencari informasi IP menggunakan IPWhois API"""
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


async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Selamat datang! Kirimkan alamat IP untuk mendapatkan informasi.")


async def check_ip(update: Update, context: CallbackContext):
    user_input = update.message.text.strip()
    ip_db = load_ip_database()
    if user_input in ip_db:
        await update.message.reply_text(f"⚠️ IP {user_input} sudah pernah digunakan.")
    else:
        ip_info = lookup_ip(user_input)
        if ip_info:
            ip_db[user_input] = ip_info
            save_ip_database(ip_db)
            update_github_file(ip_db)
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
    logging.info("✅ Bot berjalan...")
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
