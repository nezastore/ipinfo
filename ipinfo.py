import logging
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
IP_API_URL = "https://ipwho.is/{}"  # API untuk cek IP
DB_FILE = "ip_database.json"

# Konfigurasi GitHub
GITHUB_TOKEN = "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"
GITHUB_REPO = "nezastore/ipinfo"
GITHUB_FILE_PATH = "ip_database.json"

# Logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

def load_ip_database():
    """Load database IP dari file JSON"""
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def update_github_file(data):
    """Upload atau update file JSON ke GitHub"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

    # Ambil SHA file jika sudah ada
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        sha = response.json()["sha"]
    else:
        sha = None

    # Encode data JSON ke Base64
    encoded_content = base64.b64encode(json.dumps(data, indent=4).encode()).decode()

    # Payload untuk update ke GitHub
    payload = {
        "message": "Update IP Database",
        "content": encoded_content,
        "sha": sha
    }

    # Kirim request untuk update
    update_response = requests.put(url, headers=headers, json=payload)
    return update_response.status_code == 200

def save_ip_database(data):
    """Simpan database ke file lokal dan update ke GitHub"""
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)
    
    # Update file di GitHub
    if update_github_file(data):
        logging.info("✅ Database berhasil diperbarui di GitHub")
    else:
        logging.error("❌ Gagal memperbarui database di GitHub")

def lookup_ip(ip):
    """Mencari informasi tentang IP menggunakan API"""
    response = requests.get(IP_API_URL.format(ip))
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            return {
                "ip": ip,
                "country": data.get("country", "Tidak diketahui"),
                "region": data.get("region", "Tidak diketahui"),
                "city": data.get("city", "Tidak diketahui"),
                "isp": data.get("isp", "Tidak diketahui"),
                "org": data.get("org", "Tidak tersedia"),
                "lat": data.get("latitude"),
                "lon": data.get("longitude"),
            }
    return None

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
            ip_db[user_input] = ip_info  # Simpan ke database
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
