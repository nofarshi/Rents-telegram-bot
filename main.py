from telegram_bot import TelegramBot
from db_manager import DbManager

db = DbManager(user="root", password="1234", host="localhost", database="rent_bot")
bot = TelegramBot(token="TOKEN", db=db)
bot.trigger()
