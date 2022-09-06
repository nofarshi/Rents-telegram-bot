import datetime
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ContextTypes, ConversationHandler, filters, CallbackContext, CallbackQueryHandler
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, ParseMode, bot, InlineKeyboardButton, InlineKeyboardMarkup
from currency_converter import CurrencyConverter
from air_bnb_api import AirBnbApi
from booking_api import BookingApi
import telegramcalendar
import time

user_cache = {}

CATEGORY, ENDCONV, ADULTS, CHILDREN, COUNTRY, START_DATE, END_DATE, MAX_PRICE, PROPERTY, FIND_A, DAYS = range(11)



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
                CATEGORY: [MessageHandler(Filters.regex("^(דירה)$"), self.category), MessageHandler(Filters.regex("^(רכב)$"), self.endconv)],
                ADULTS: [MessageHandler(Filters.regex("^(הכל|נופים|חופים|אגם|סקי)$"), self.adults)],
                CHILDREN: [MessageHandler(Filters.regex("^(1|2|3|4|5|6)$"), self.children)],
                COUNTRY: [MessageHandler(Filters.regex("^(0|1|2|3|4|5|6)$"), self.country), CallbackQueryHandler(self.button, pass_user_data=True), CommandHandler('Approve', self.max_price)],
                START_DATE: [MessageHandler(Filters.text, self.start_date), CallbackQueryHandler(self.inline_handler)],
                DAYS: [CommandHandler('Approve', self.days), CommandHandler('TryAgain', self.start_date)],
                MAX_PRICE: [MessageHandler(Filters.text, self.max_price)],
                FIND_A: [CommandHandler('TryAgain', self.days), MessageHandler(Filters.regex("^(2000|5000|8000|10000|יותר)$"), self.find_apartment)]

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


    def category(self,update, context: CallbackContext):
        user_cache[update.message.from_user.id]["api_type"] = update.message.text
        #reply_keyboard = [["הכל","סקי","אגם","נופים","חופים"]]
        key=[]
        categories = self.db.execute("select category_hebrew from rent_bot.airbnb_category;")
        for i in categories:
            key.append(i[0])
        print(key)
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
        # CallbackQueries need to be answered, even if no notification to the user is needed
        # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
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
            price=int(c.convert(int(update.message.text), 'ILS', 'USD'))
            user_cache[update.message.from_user.id]["price"] = price
        print(user_cache[update.message.from_user.id])
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
            print(cityq[0][0])
            print(countryq)
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

        airbnb = AirBnbApi(url="airbnb19.p.rapidapi.com", token="fa8cff67a0mshe9948d6063463b0p1ff194jsn31a255f19176")
        dec=airbnb.get(name="searchDestination", params={"query":cityq[0][0],"country":countryq})
        print(dec['data'][0]['id'])
        print(dec)
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
        print(a)
        #result = [f"{link}rooms/{i['id']}" for i in a['data']]
        #pri =[i['price'] for i in a['data']]
        # ls = [i['listingName']for i in a['data']]
        # rv= [i['avgRatingLocalized'] for i in a['data']]
        if a['message'] !="Success":
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

            pri=[]
            for i in a['data']:
                if 'accessibilityLabel' in i:
                    pri.append(i['accessibilityLabel'])
                else:
                    if 'price' in i:
                        pri.append(i['price'])
                    else:
                        pri.append("לא מוצג מחיר")
            ls=[]
            for i in a['data']:
                if 'listingName' in i:
                    ls.append(i['listingName'])
                else:
                   ls.append("לא מוצג שם")


            rv=[]
            for i in a['data']:

                if 'avgRatingLocalized' in i:
                    if i['avgRatingLocalized']=="New":
                        rv.append("לא קיים דירוג")
                    else:
                        rv.append(i['avgRatingLocalized'])
                else:
                   rv.append("לא קיים דירוג")
            print(result)
            print(pri)
            print(ls)
            print(rv)
            for i in range(3):
                update.message.reply_text(
                   f" שם: {ls[i]} "
                   f"\n מחיר: {pri[i]}"
                   f"\n דירוג: {rv[i]}"
                   f"\n קישור: {result[i]}"
                    "\n. ",
                    reply_markup=ReplyKeyboardRemove()
                )
            update.message.reply_text(
                "ביי, שתהיה לכם חופשה מהנה! \U00002708", reply_markup=ReplyKeyboardRemove()
            )

        return ConversationHandler.END

    def endconv(self,update, context: CallbackContext):
        update.message.reply_text(
            "ביי, שתהיה לכם חופשה מהנה! ", reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    def cancel(self,update, context):
            """Cancels and ends the conversation."""

            update.message.reply_text(
                "ביי, שתהיה לכם חופשה מהנה!", reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END





