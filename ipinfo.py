import os
import json
import requests
import sqlite3
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Ganti dengan token bot Telegram Anda
TOKEN = "7672001478:AAGKmw_FixFyqe4zADaifTc94hVqcW5uvOw"
DB_FILE = "ip_database.db"
API_URL = "https://ipwho.is/{}"

# Inisialisasi database
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ip_data (
            ip TEXT PRIMARY KEY,
            country TEXT,
            region TEXT,
            city TEXT,
            isp TEXT
        )
    """)
    conn.commit()
    conn.close()

# Fungsi untuk mengecek apakah IP valid
def is_valid_ip(ip):
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(part) <= 255 for part in parts)
    except ValueError:
        return False

# Fungsi untuk mendapatkan informasi IP dari ipwho.is
def get_ip_info(ip):
    response = requests.get(API_URL.format(ip))
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            return {
                "country": data.get("country"),
                "region": data.get("region"),
                "city": data.get("city"),
                "isp": data.get("isp")
            }
    return None

# Fungsi untuk menyimpan IP ke database
def save_ip(ip, info):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO ip_data (ip, country, region, city, isp) VALUES (?, ?, ?, ?, ?)",
                   (ip, info["country"], info["region"], info["city"], info["isp"]))
    conn.commit()
    conn.close()

# Fungsi untuk mengecek apakah IP sudah ada di database
def check_ip(ip):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ip_data WHERE ip = ?", (ip,))
    result = cursor.fetchone()
    conn.close()
    return result

# Fungsi untuk menangani pesan pengguna
def handle_message(update: Update, context: CallbackContext):
    ip = update.message.text.strip()
    if not is_valid_ip(ip):
        update.message.reply_text("⚠️ Format IP tidak valid. Harap masukkan IP yang benar.")
        return
    
    existing_ip = check_ip(ip)
    if existing_ip:
        update.message.reply_text(f"⚠️ IP {ip} sudah digunakan untuk Linode.")
    else:
        info = get_ip_info(ip)
        if info:
            save_ip(ip, info)
            update.message.reply_text(
                f"✅ IP {ip} telah disimpan!\n\n🌍 Lokasi: {info['city']}, {info['region']}, {info['country']}\n🏢 ISP: {info['isp']}"
            )
        else:
            update.message.reply_text("⚠️ Gagal mengambil data IP. Coba lagi nanti.")

# Fungsi untuk memulai bot
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Halo! Kirimkan IP yang ingin Anda cek.")

# Main function
def main():
    init_db()
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
