import datetime
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ContextTypes, ConversationHandler, filters, CallbackContext, CallbackQueryHandler
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, ParseMode, bot, InlineKeyboardButton, InlineKeyboardMarkup
from currency_converter import CurrencyConverter
from air_bnb_api import AirBnbApi
from booking_api import BookingApi
import telegramcalendar
import time
import os

user_cache = {}

CATEGORY, FIND_CAR, ADULTS, CHILDREN, COUNTRY, START_DATE, END_DATE, MAX_PRICE, FIND_A, DAYS, DROP, CITY_PICK, START_DATE2, DAYS2, CITY_DROP = range(15)

class TelegramBot(object):
    def __init__(self, token, db):
        self.updater = Updater(token, use_context=True)
        self.db = db

    def trigger(self):
        # Get the dispatcher to register handlers
        dp = self.updater.dispatcher
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                CATEGORY: [MessageHandler(Filters.regex("^(דירה)$"), self.category), MessageHandler(Filters.regex("^(רכב)$"), self.same_dropoff)],
                #Apartment process
                ADULTS: [MessageHandler(Filters.regex("^(הכל|נופים|חופים|אגם|סקי)$"), self.adults)],
                CHILDREN: [MessageHandler(Filters.regex("^(1|2|3|4|5|6)$"), self.children)],
                COUNTRY: [MessageHandler(Filters.regex("^(0|1|2|3|4|5|6)$"), self.country), CallbackQueryHandler(self.button, pass_user_data=True), CommandHandler('Approve', self.start_date)],
                START_DATE: [MessageHandler(Filters.text, self.start_date), CallbackQueryHandler(self.inline_handler)],
                DAYS: [CommandHandler('Approve', self.days), CommandHandler('TryAgain', self.start_date)],
                MAX_PRICE: [MessageHandler(Filters.text, self.max_price)],
                FIND_A: [CommandHandler('TryAgain', self.days), MessageHandler(Filters.regex("^(2000|5000|8000|10000|יותר)$"), self.find_apartment)],
                #Car process
                DROP: [MessageHandler(Filters.regex("^(אותה נקודה)$"), self.des_country),  MessageHandler(Filters.regex("^(אחרת)$"), self.des_country), CallbackQueryHandler(self.country_query, pass_user_data=True), CommandHandler('Approve', self.city_pick)],
                CITY_PICK:[MessageHandler(Filters.text, self.city_pick), CallbackQueryHandler(self.city_query, pass_user_data=True), CommandHandler('Approve', self.start_date2)],
                CITY_DROP:[MessageHandler(Filters.text, self.city_drop), CallbackQueryHandler(self.city_query2, pass_user_data=True), CommandHandler('Approve', self.start_date2)],
                START_DATE2: [MessageHandler(Filters.text, self.start_date2), CallbackQueryHandler(self.inline_handler2)],
                DAYS2: [CommandHandler('Approve', self.days2), CommandHandler('TryAgain', self.start_date2)],
                FIND_CAR:[CommandHandler('TryAgain', self.days2), MessageHandler(Filters.text, self.find_car)]
            },
            fallbacks=[CommandHandler('cancel', self.cancel)]
        )

        dp.add_handler(conv_handler)
        self.updater.start_polling()
        self.updater.idle()


    def start(self,update, context: CallbackContext):
        """Send a message when the command /start is issued."""
        reply_keyboard = [["רכב", "דירה"]]
        user_cache[update.message.from_user.id] = {}
        update.message.reply_text(
            "היי! אני ביטי הבוט \U0001F916 \n\n"
            "אני אעזור לכם למצוא רכב ודירה להשכרה לטיול הבא שלכם.\n\n"
            " שלחו /cancel על מנת להפסיק לדבר איתי."
            "\n.",
        )
        update.message.reply_text( "תרצו להשכיר דירה או רכב?",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, input_field_placeholder="רכב או דירה?"
            ),
         )
        return CATEGORY

    #Apartment process
    def category(self,update, context: CallbackContext):
        user_cache[update.message.from_user.id]["api_type"] = update.message.text
        key=[]
        categories = self.db.execute("select category_hebrew from rent_bot.airbnb_category;")
        for i in categories:
            key.append(i[0])
        reply_keyboard = [key]
        update.message.reply_text(
            "כדי להכיר אותך אשמח לדעת מה הסגנון המועדף עליך?",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, input_field_placeholder="בחר קטגוריה"
            ),
        )

        return ADULTS

    def adults(self, update, context: CallbackContext):
        if update.message.text=="הכל":
            user_cache[update.message.from_user.id]["category"]="ALL"
        else:
            categuryen= self.db.execute("select category from rent_bot.airbnb_category where category_hebrew='%s'" % update.message.text)
            user_cache[update.message.from_user.id]["category"] = categuryen[0][0]
        reply_keyboard = [["1", "2", "3", "4", "5", "6"]]
        update.message.reply_text(
            "כמה מבוגרים תהיו?",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, input_field_placeholder="הכנס מספר"
            ),
        )

        return CHILDREN

    def children(self, update, context: CallbackContext):
        user_cache[update.message.from_user.id]["adults"] = update.message.text
        reply_keyboard = [["0", "1", "2", "3", "4", "5", "6"]]
        update.message.reply_text(
            "כמה ילדים יהיו?",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, input_field_placeholder="הכנס מספר"
            ),
        )

        return COUNTRY

    def country(self, update, context: CallbackContext):
        user_cache[update.message.from_user.id]["children"] = update.message.text
        update.message.reply_text(
            "\U0001F973",
            reply_markup=ReplyKeyboardRemove())
        keyboard = []
        countries = self.db.execute("select country_name_hebrew from rent_bot.countries;")
        for i, country in enumerate(countries):
            keyboard.insert(i, [InlineKeyboardButton(country[0], callback_data=i)])

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text("באיזה מדינה תרצה לשהות?", reply_markup=reply_markup)


    def button(self, update, context: CallbackContext):
        """Parses the CallbackQuery and updates the message text."""
        query = update.callback_query
        global country
        query.answer()
        country=query.message.reply_markup.inline_keyboard[int(query.data)][0].text
        query.edit_message_text(text= "המדינה שבחרת היא: " +country+" לחץ על /Approve כדי להמשיך")
        return START_DATE

    def start_date(self, update, context: CallbackContext):
        en_country=self.db.execute("select country_name from rent_bot.countries where country_name_hebrew='%s'" %country)
        user_cache[update.message.from_user.id]["country"] = en_country[0][0]
        update.message.reply_text(text='הכנס את תאריך ההגעה:',
                                  reply_markup=telegramcalendar.create_calendar())


    def inline_handler(self, update, context: CallbackContext):
        global sdate
        query = update.callback_query
        (kind, _, _, _, _) = query.data.split(";")
        selected, date = telegramcalendar.process_calendar_selection(update, context)
        if not selected:
            return START_DATE
        else:
            if date < datetime.datetime.now():
                context.bot.send_message(chat_id=update.callback_query.from_user.id,
                                         text="התאריך שהזנת עבר לחץ על /TryAgain כדי להזין שוב",
                                         reply_markup=ReplyKeyboardRemove())
                return START_DATE
            startdate = date.strftime("%d-%m-%Y")
            sdate=date.strftime("%Y-%m-%d")
            context.bot.send_message(chat_id=update.callback_query.from_user.id,
                                     text="התאריך שהזנת הוא " + (startdate) + " לחץ על /Approve כדי להמשיך",
                                     reply_markup=ReplyKeyboardRemove())
            return DAYS

    def days(self, update, context: CallbackContext):
        user_cache[update.message.from_user.id]["startdate"]=sdate
        update.message.reply_text(
            'כמה ימים תרצו להשכיר את הדירה? (ספרות בלבד)', reply_markup=ReplyKeyboardRemove()
        )
        return MAX_PRICE

    def max_price(self, update, context: CallbackContext):
        if update.message.text.isnumeric():
            date1 = datetime.datetime.strptime(sdate, '%Y-%m-%d')
            date2=date1+datetime.timedelta(days=int(update.message.text))
            enddate = date2.strftime("%Y-%m-%d")
            user_cache[update.message.from_user.id]["enddate"] = enddate
            reply_keyboard = [["2000", "5000", "8000", "10000", "יותר"]]
            update.message.reply_text(
                "מה המחיר המקסימלי (בשקלים) שתהיו מוכנים לשלם?",
                reply_markup=ReplyKeyboardMarkup(
                    reply_keyboard, one_time_keyboard=True, input_field_placeholder="הכנס מחיר"
                ),
            )
        else:
            update.message.reply_text(
                "נא הזן את מספר הימים בספרות לחץ על /TryAgain כדי להזין שוב",
                reply_markup=ReplyKeyboardRemove()
            )

        return FIND_A

    def find_apartment(self, update, context: CallbackContext):
        c = CurrencyConverter()
        if update.message.text=="יותר":
            user_cache[update.message.from_user.id]["price"] = ""

        else:
            price_conv=int(c.convert(int(update.message.text), 'ILS', 'USD'))
            user_cache[update.message.from_user.id]["price"] = price_conv
        update.message.reply_text(
            "מחפש לך את הדירה... \U0001F50E"	
            "\n (נא המתן מספר שניות)"
            "\n."
            , reply_markup=ReplyKeyboardRemove()
        )
        if user_cache[update.message.from_user.id]["category"]=="Beach":
            cityq = self.db.execute(
                "select Beach from rent_bot.countries where country_name='%s'" %user_cache[update.message.from_user.id]["country"])
            countryq = user_cache[update.message.from_user.id]["country"]
        elif user_cache[update.message.from_user.id]["category"]=="Amazing views":
                cityq = self.db.execute(
                    "select Amazingviews from rent_bot.countries where country_name='%s'" %user_cache[update.message.from_user.id]["country"])
                countryq = user_cache[update.message.from_user.id]["country"]
        elif user_cache[update.message.from_user.id]["category"]=="Lake":
                cityq = self.db.execute(
                    "select Lake from rent_bot.countries where country_name='%s'" %user_cache[update.message.from_user.id]["country"])
                countryq = user_cache[update.message.from_user.id]["country"]
        elif user_cache[update.message.from_user.id]["category"] == "Skiing":
            cityq = self.db.execute(
                "select Skiing from rent_bot.countries where country_name='%s'" %user_cache[update.message.from_user.id]["country"])
            countryq = user_cache[update.message.from_user.id]["country"]
        else:
            cityq = self.db.execute(
                "select main_city from rent_bot.countries where country_name='%s'" %user_cache[update.message.from_user.id]["country"])
            countryq = user_cache[update.message.from_user.id]["country"]
        link="https://he.airbnb.com/"

        airbnb = AirBnbApi(url="airbnb19.p.rapidapi.com", token=os.environ["AIRBNB_TOKEN"])
        dec=airbnb.get(name="searchDestination", params={"query":cityq[0][0],"country":countryq})
        if dec['message'] != "Success" or dec['status']=="false":
            update.message.reply_text(
                "לא נמצאה חופשה לפרמטרים שנבחרו \U0001F622", reply_markup=ReplyKeyboardRemove()
            )
            update.message.reply_text(
                dec['message'], reply_markup=ReplyKeyboardRemove()
            )

        else:
            time.sleep(3)
            if cityq[0][0] == "Athens":
                 id_city=dec['data'][1]['id']
            else:
                id_city=dec['data'][0]['id']
            a = airbnb.get(name="searchPropertyByPlace",
                           params={"id": dec['data'][0]['id'], "totalRecords": "3", "currency":"USD",
                                   "adults": user_cache[update.message.from_user.id]["adults"],
                                   "children": user_cache[update.message.from_user.id]["children"],
                                   "checkin":user_cache[update.message.from_user.id]["startdate"],
                                   "checkout":user_cache[update.message.from_user.id]["enddate"],
                                   "priceMax": user_cache[update.message.from_user.id]["price"]})
            if a['message'] != "Success" or a['status'] == "false":
                update.message.reply_text(
                    "לא נמצאה חופשה לפרמטרים שנבחרו \U0001F622", reply_markup=ReplyKeyboardRemove()
                )
            else:
                update.message.reply_text(
                    "מצאתי לך מספר יעדים:", reply_markup=ReplyKeyboardRemove()
                )
                result = []
                for i in a['data']:
                    if 'id' in i:
                        result.append(f"{link}rooms/{i['id']}")
                    else:
                        result.append("אין קישור")

                price=[]
                for i in a['data']:
                    if 'accessibilityLabel' in i:
                        price.append(i['accessibilityLabel'])
                    else:
                        if 'price' in i:
                            price.append(i['price'])
                        else:
                            price.append("לא מוצג מחיר")
                name=[]
                for i in a['data']:
                    if 'listingName' in i:
                        name.append(i['listingName'])
                    else:
                       name.append("לא מוצג שם")
                rate=[]
                for i in a['data']:

                    if 'avgRatingLocalized' in i:
                        if i['avgRatingLocalized']=="New":
                            rate.append("לא קיים דירוג")
                        else:
                            rate.append(i['avgRatingLocalized'])
                    else:
                       rate.append("לא קיים דירוג")
                for i in range(3):
                    update.message.reply_text(
                        "שם:\n"
                       f"{name[i]}\n\n"
                        "מחיר: \n"
                       f"{price[i]}\n\n"
                        "דירוג: \n"
                       f"{rate[i]}\n\n"
                        "קישור: \n"
                       f"{result[i]}\n\n"
                        "\n. ",
                        reply_markup=ReplyKeyboardRemove()
                    )
                update.message.reply_text(
                    "ביי, שתהיה לכם חופשה מהנה! \U00002708", reply_markup=ReplyKeyboardRemove()
                )

        return ConversationHandler.END

    # Car process
    def same_dropoff(self,update, context: CallbackContext):
        """Send a message when the command /start is issued."""
        reply_keyboard = [["אחרת", "אותה נקודה"]]
        update.message.reply_text( "האם תרצו לאסוף ולהחזיר את הרכב מאותה נקודה או אחרת?",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, input_field_placeholder="נקודת איסוף?"
            ),
         )
        return DROP

    def des_country(self, update, context: CallbackContext):
        user_cache[update.message.from_user.id]["api_type"] = update.message.text
        update.message.reply_text(
            "\U0001F973",
            reply_markup=ReplyKeyboardRemove())
        keyboard = []
        countries = self.db.execute("select country_name_hebrew from rent_bot.countries where country_name <>'Israel';")
        for i, country in enumerate(countries):
            keyboard.insert(i, [InlineKeyboardButton(country[0], callback_data=i)])


        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text("מאיזה מדינה תרצה להשכיר רכב?", reply_markup=reply_markup)


    def country_query(self, update, context: CallbackContext):
        """Parses the CallbackQuery and updates the message text."""
        query = update.callback_query
        global country_pick
        query.answer()
        country_pick=query.message.reply_markup.inline_keyboard[int(query.data)][0].text
        query.edit_message_text(text= "המדינה שבחרת היא: " +country_pick+" לחץ על /Approve כדי להמשיך")
        return CITY_PICK

    def city_pick(self, update, context: CallbackContext):
        global choice
        en_country = self.db.execute(
                "select country_name from rent_bot.countries where country_name_hebrew='%s'" % country_pick)
        user_cache[update.message.from_user.id]["country_pick"] = en_country[0][0]
        choice = user_cache[update.message.from_user.id]["api_type"]
        keyboard = []
        cities = self.db.execute(
            "select city1_he,city2_he,city3_he, city4_he from rent_bot.cities_cars where country_name='%s'" %
            en_country[0][0])
        for i, city in enumerate(cities[0]):
            keyboard.insert(i, [InlineKeyboardButton(city, callback_data=i)])

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text("מאיזה עיר תרצה להשכיר רכב?", reply_markup=reply_markup)

    def city_query(self, update, context: CallbackContext):
        """Parses the CallbackQuery and updates the message text."""
        query = update.callback_query
        global city_pick
        query.answer()
        city_pick=query.message.reply_markup.inline_keyboard[int(query.data)][0].text
        query.edit_message_text(text= "העיר שבחרת היא: " +city_pick+" לחץ על /Approve כדי להמשיך")
        if choice=="אותה נקודה":
            return START_DATE2
        else:
            return CITY_DROP

    def city_drop(self, update, context: CallbackContext):
        en_country = self.db.execute(
            "select country_name from rent_bot.countries where country_name_hebrew='%s'" % country_pick)
        s1 = self.db.execute(
            "select city1_en,city2_en,city3_en, city4_en from rent_bot.cities_cars where country_name='%s'" %
            user_cache[update.message.from_user.id]["country_pick"])
        s2 = self.db.execute(
            "select city1_he,city2_he,city3_he, city4_he from rent_bot.cities_cars where country_name='%s'" %
            user_cache[update.message.from_user.id]["country_pick"])
        city_en = ""
        for i, city in enumerate(s2[0]):
            if city == city_pick:
                city_en = s1[0][i]
        user_cache[update.message.from_user.id]["city_pick"] = city_en
        keyboard = []
        cities = self.db.execute(
            "select city1_he,city2_he,city3_he, city4_he from rent_bot.cities_cars where country_name='%s'" %
            en_country[0][0])
        for i, city in enumerate(cities[0]):
            keyboard.insert(i, [InlineKeyboardButton(city, callback_data=i)])

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text("לאיזה עיר תרצה להחזיר את הרכב?", reply_markup=reply_markup)

    def city_query2(self, update, context: CallbackContext):
        """Parses the CallbackQuery and updates the message text."""
        query = update.callback_query
        global city_drop
        query.answer()
        city_drop=query.message.reply_markup.inline_keyboard[int(query.data)][0].text
        query.edit_message_text(text= "העיר שבחרת היא: " +city_drop+" לחץ על /Approve כדי להמשיך")
        return START_DATE2

    def start_date2(self, update, context: CallbackContext):
        if(user_cache[update.message.from_user.id]["api_type"]=="אחרת"):
            s1=self.db.execute(
                "select city1_en,city2_en,city3_en, city4_en from rent_bot.cities_cars where country_name='%s'" %
                user_cache[update.message.from_user.id]["country_pick"])
            s2=self.db.execute(
                "select city1_he,city2_he,city3_he, city4_he from rent_bot.cities_cars where country_name='%s'" %
                user_cache[update.message.from_user.id]["country_pick"])
            city_en=""
            for i, city in enumerate(s2[0]):
                if city== city_drop:
                    city_en=s1[0][i]
            user_cache[update.message.from_user.id]["city_drop"] = city_en
        else:
            s1 = self.db.execute(
                "select city1_en,city2_en,city3_en, city4_en from rent_bot.cities_cars where country_name='%s'" %
                user_cache[update.message.from_user.id]["country_pick"])
            s2 = self.db.execute(
                "select city1_he,city2_he,city3_he, city4_he from rent_bot.cities_cars where country_name='%s'" %
                user_cache[update.message.from_user.id]["country_pick"])
            city_en = ""
            for i, city in enumerate(s2[0]):
                if city == city_pick:
                    city_en = s1[0][i]
            user_cache[update.message.from_user.id]["city_pick"] = city_en
            user_cache[update.message.from_user.id]["city_drop"] = city_en
        update.message.reply_text(text='הכנס את תאריך ההגעה:',
                                  reply_markup=telegramcalendar.create_calendar())

    def inline_handler2(self, update, context: CallbackContext):
        global sdate2
        query = update.callback_query
        (kind, _, _, _, _) = query.data.split(";")
        selected, date = telegramcalendar.process_calendar_selection(update, context)
        if not selected:
            return START_DATE2
        else:
            if date < datetime.datetime.now():
                context.bot.send_message(chat_id=update.callback_query.from_user.id,
                                         text="התאריך שהזנת עבר לחץ על /TryAgain כדי להזין שוב",
                                         reply_markup=ReplyKeyboardRemove())
                return START_DATE2
            startdate = date.strftime("%d-%m-%Y")
            sdate2 = date.strftime("%Y-%m-%d 09:00:00")
            context.bot.send_message(chat_id=update.callback_query.from_user.id,
                                     text="התאריך שהזנת הוא " + (startdate) + " לחץ על /Approve כדי להמשיך",
                                     reply_markup=ReplyKeyboardRemove())
            return DAYS2

    def days2(self, update, context: CallbackContext):
        user_cache[update.message.from_user.id]["startdate_car"] = sdate2
        update.message.reply_text(
            'כמה ימים תרצו להשכיר את הרכב? (ספרות בלבד)', reply_markup=ReplyKeyboardRemove()
        )
        return FIND_CAR

    def find_car(self, update, context: CallbackContext):
        if update.message.text.isnumeric():
            date1 = datetime.datetime.strptime(sdate2, '%Y-%m-%d %H:%M:%S')
            date2 = date1 + datetime.timedelta(days=int(update.message.text))
            enddate2 = date2.strftime("%Y-%m-%d 20:00:00")
            user_cache[update.message.from_user.id]["enddate_car"] = enddate2
            booking = BookingApi(url="booking-com.p.rapidapi.com", token=os.environ["BOOKING_TOKEN"])
            a1=booking.get(name="car-rental/locations", params={"name":user_cache[update.message.from_user.id]["city_pick"], "locale": "en-gb"})
            user_cache[update.message.from_user.id]["longitude_pick"]=a1[0]['longitude']
            user_cache[update.message.from_user.id]["latitude_pick"] = a1[0]['latitude']
            if user_cache[update.message.from_user.id]["city_pick"]!= user_cache[update.message.from_user.id]["city_drop"]:
                a2 = booking.get(name="car-rental/locations",
                                 params={"name": user_cache[update.message.from_user.id]["city_drop"],
                                         "locale": "en-gb"})
                user_cache[update.message.from_user.id]["longitude_drop"] = a2[0]['longitude']
                user_cache[update.message.from_user.id]["latitude_drop"] = a2[0]['latitude']
            else:
                user_cache[update.message.from_user.id]["longitude_drop"] = user_cache[update.message.from_user.id]["longitude_pick"]
                user_cache[update.message.from_user.id]["latitude_drop"] = user_cache[update.message.from_user.id]["latitude_pick"]
            update.message.reply_text(
                "מחפש לך את הרכב... \U0001F50E"
                "\n (נא המתן מספר שניות)"   
                "\n."
                , reply_markup=ReplyKeyboardRemove()
            )
            b1 = booking.get(name="car-rental/search",
                            params={"drop_off_longitude": user_cache[update.message.from_user.id]["longitude_drop"], "currency": "ILS", "sort_by": 'recommended',
                                    "drop_off_datetime":user_cache[update.message.from_user.id]["enddate_car"], "drop_off_latitude": user_cache[update.message.from_user.id]["latitude_drop"],
                                    "from_country": 'it', "pick_up_longitude":user_cache[update.message.from_user.id]["longitude_pick"],
                                    "locale": 'en-gb', "pick_up_datetime": user_cache[update.message.from_user.id]["startdate_car"], "pick_up_latitude":user_cache[update.message.from_user.id]["latitude_pick"]})
            try:
                if b1["meta"]["response_code"]!=200 or b1['search_results']==[]:
                    update.message.reply_text(
                        "לא נמצאה חופשה לפרמטרים שנבחרו \U0001F622", reply_markup=ReplyKeyboardRemove()
                    )
                    return ConversationHandler.END
                else:
                    update.message.reply_text(
                        "איזה כיף מצאנו לך שני רכבים!",
                        reply_markup=ReplyKeyboardRemove()
                    )
                    v_name1=b1['search_results'][0]['vehicle_info']['v_name']
                    price1=b1['search_results'][0]['pricing_info']['price']
                    sup_name1=b1['search_results'][0]['supplier_info']['name']
                    rate1=b1['search_results'][0]['rating_info']['average']
                    pickup1=b1['search_results'][0]['route_info']['pickup']['address']
                    dropoff1=b1['search_results'][0]['route_info']['dropoff']['address']
                    image1=b1['search_results'][0]['vehicle_info']['image_url']
                    if (rate1 == 0):
                        rate1 = "לא קיים דירוג"
                    update.message.reply_text(
                        "הרכב המומלץ ביותר:\n\n"
                        "שם הרכב:\n "
                         f"{v_name1}\n\n"  
                        "מחיר בשקלים: \n" 
                         f"{price1}\n\n"
                         "שם חברת ההשכרה: \n"
                        f"{sup_name1}\n\n"
                         "דירוג: \n"
                        f"{rate1}\n\n"
                        "כתובת איסוף: \n" 
                         f"{pickup1}\n\n"
                        "כתובת החזרה: \n" 
                        f"{dropoff1}\n\n"
                        "תמונה: \n"
                        f"{image1}\n\n"
                        "\n."
                    )
                    b2 = booking.get(name="car-rental/search",
                                     params={"drop_off_longitude": user_cache[update.message.from_user.id]["longitude_drop"],
                                             "currency": "ILS", "sort_by": 'price_low_to_high',
                                             "drop_off_datetime": user_cache[update.message.from_user.id]["enddate_car"],
                                             "drop_off_latitude": user_cache[update.message.from_user.id]["latitude_drop"],
                                             "from_country": 'it',
                                             "pick_up_longitude": user_cache[update.message.from_user.id]["longitude_pick"],
                                             "locale": 'en-gb',
                                             "pick_up_datetime": user_cache[update.message.from_user.id]["startdate_car"],
                                             "pick_up_latitude": user_cache[update.message.from_user.id]["latitude_pick"]})

                    v_name2 = b2['search_results'][0]['vehicle_info']['v_name']
                    price2 = b2['search_results'][0]['pricing_info']['price']
                    sup_name2 = b2['search_results'][0]['supplier_info']['name']
                    rate2 = b2['search_results'][0]['rating_info']['average']
                    pickup2 = b2['search_results'][0]['route_info']['pickup']['address']
                    dropoff2 = b2['search_results'][0]['route_info']['dropoff']['address']
                    image2 = b2['search_results'][0]['vehicle_info']['image_url']
                    if (rate2 == 0):
                        rate2 = "לא קיים דירוג"
                    if(v_name1==v_name2 and price1==price2 and sup_name1==sup_name2 and rate1==rate2):
                        v_name2 = b1['search_results'][1]['vehicle_info']['v_name']
                        price2 = b1['search_results'][1]['pricing_info']['price']
                        sup_name2 = b1['search_results'][1]['supplier_info']['name']
                        rate2 = b1['search_results'][1]['rating_info']['average']
                        pickup2 = b1['search_results'][1]['route_info']['pickup']['address']
                        dropoff2 = b1['search_results'][1]['route_info']['dropoff']['address']
                        image2 = b1['search_results'][1]['vehicle_info']['image_url']
                        if(rate2==0):
                            rate2="לא קיים דירוג"
                        update.message.reply_text(
                        "רכב מומלץ נוסף:\n\n"
                        "שם הרכב:\n "
                        f"{v_name2}\n\n"
                        "מחיר בשקלים: \n"
                        f"{price2}\n\n"
                        "שם חברת ההשכרה: \n"
                        f"{sup_name2}\n\n"
                        "דירוג: \n"
                        f"{rate2}\n\n"
                        "כתובת איסוף: \n"
                        f"{pickup2}\n\n"
                        "כתובת החזרה: \n"
                        f"{dropoff2}\n\n"
                        "תמונה: \n"
                        f"{image2}\n\n"
                        "\n."
                    )
                    else:
                        update.message.reply_text(
                            "הרכב הזול ביותר ביותר:\n\n"
                            "שם הרכב:\n "
                            f"{v_name2}\n\n"
                            "מחיר בשקלים: \n"
                            f"{price2}\n\n"
                            "שם חברת ההשכרה: \n"
                            f"{sup_name2}\n\n"
                            "דירוג: \n"
                            f"{rate2}\n\n"
                            "כתובת איסוף: \n"
                            f"{pickup2}\n\n"
                            "כתובת החזרה: \n"
                            f"{dropoff2}\n\n"
                            "תמונה: \n"
                            f"{image2}\n\n"
                            "\n."
                        )
                    update.message.reply_text(
                        "את הרכבים ניתן למצוא באתר:\n"
                        "https://bit.ly/rentcar_booking \n\n"
                        "ביי, שתהיה לכם חופשה מהנה!\n"
                        , reply_markup=ReplyKeyboardRemove()
                    )
                    return ConversationHandler.END
            except:
                update.message.reply_text(
                    "לא נמצאה חופשה לפרמטרים שנבחרו \U0001F622", reply_markup=ReplyKeyboardRemove()
                )
                return ConversationHandler.END

        else:
            update.message.reply_text(
                    "נא הזן את מספר הימים בספרות לחץ על /TryAgain כדי להזין שוב",
                    reply_markup=ReplyKeyboardRemove()
            )
            return FIND_CAR

    def cancel(self, update, context):
        """Cancels and ends the conversation."""

        update.message.reply_text(
            "ביי, שתהיה לכם חופשה מהנה!", reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END





