from telegram_bot import TelegramBot
from db_manager import DbManager
import os

db = DbManager(user="root", password="1234", host="localhost", database="rent_bot")
bot = TelegramBot(token=os.environ["TELEGRAM_TOKEN"], db=db)
bot.trigger()
