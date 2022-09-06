from telegram_bot import TelegramBot
#from expl import TelegramBot
from air_bnb_api import AirBnbApi
from booking_api import BookingApi
from db_manager import DbManager



# cek="חופים"
# b=db.execute("select category from rent_bot.airbnb_category where category_hebrew='%s'" %cek)
# print(b[0][0])
# b2 = db.execute("select category_hebrew from rent_bot.airbnb_category;")
# cat=[]
# print(b2)
# print(b2[2][0])
# for i in range(0, len(b2)):
#     cat.append(b2[i][0])
# print(cat)
link = "https://he.airbnb.com/rooms/"

# airbnb = AirBnbApi(url="airbnb19.p.rapidapi.com", token="TOKEN")
# a = airbnb.get(name="searchPropertyByPlace", params={"id":"ChIJ7cv00DwsDogRAMDACa2m4K8","adults": 1})
# print(a)
# des=airbnb.get(name="searchDestination", params={"query":"Israel","country":"Tel Aviv"})
# print(des)
# a1=des['data'][0]
# a2=a1['id']
# a = airbnb.get(name="searchPropertyByPlace",
#                params={"id": "ChIJ7cv00DwsDogRAMDACa2m4K8", "totalRecords": "3", "category": "Beach",
#                        "adults": "2", "children": "2", "priceMax": "5000"})
# print(a)

#
# result = [f"{link}rooms/{i['id']}" for i in a["data"]]
# print(result)
# booking = BookingApi(url="booking-com.p.rapidapi.com", token="TOKEN")
# a=booking.get(name="car-rental/locations", params={"name":"Berlin","locale":"en-gb"})
# print(a)

c = [("israel", ), ("usa", ), ("italy", )]
for i, country in enumerate(c):
    print(i , country)
db = DbManager(user="root", password="1234", host="localhost", database="rent_bot")
b = db.execute("select * from rent_bot.airbnb_category;")
bot = TelegramBot(token="TOKEN", db=db)
bot.trigger()
