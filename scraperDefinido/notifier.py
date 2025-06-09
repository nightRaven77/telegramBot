from telegram import Bot
from telegram.error import TelegramError

import os
from dotenv import load_dotenv
import asyncio

load_dotenv()


TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

async def send_telegram_notificaction(message:str):
	try:
		bot = Bot(token=TELEGRAM_TOKEN)
		await bot.send_message(chat_id=CHAT_ID, text=message)
		await bot.send_document(chat_id=CHAT_ID, document=open("./output/products.csv", "rb"))
	except TelegramError as e:
		print(f"Error al enviar notificacion: {e}")

def sync_send_telegram_notificaction(message:str):
	asyncio.run(send_telegram_notificaction(message))
