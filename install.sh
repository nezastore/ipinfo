#!/bin/bash

# Memastikan Python dan pip sudah terinstall
echo "Memastikan Python dan pip sudah terinstall..."
python3 --version
pip3 --version

# Install dependencies dari requirements.txt
echo "Menginstall dependencies..."
pip3 install -r requirements.txt

# Menyelesaikan setup untuk Google Sheets API (hanya jika belum tersetup)
echo "Pastikan kamu sudah punya file credentials JSON untuk Google Sheets (dataiplinode-1df59f53d098.json)"
echo "Tempatkan file credentials tersebut di direktori yang sama dengan script ini."

echo "Penginstalan selesai!"
