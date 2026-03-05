import os
import datetime
import re
import traceback
from typing import Optional, Union
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import certifi

# --- MongoDB Connection Pooling ---
# MongoClient спроектирован для создания одного экземпляра и его повторного использования.
# Этот глобальный клиент будет управлять пулом соединений.
_mongo_client = None


def bom(date: datetime.date) -> datetime.date:
    """

    :param date:
    :return: first day of the month
    """
    return date.replace(day=1)


def eom(data: datetime.date) -> datetime.date:
    """

    :param data:
    :return: last day of the month
    """
    return datetime.date(year=data.year + 1 if data.month == 12 else data.year, month=1 if data.month == 12 else data.month + 1, day=1) - datetime.timedelta(days=1)


def workdays_count(start_date: datetime.date, end_date: datetime.date) -> int:
    return sum(1 for day in range((end_date - start_date).days + 1)
                    if (start_date + datetime.timedelta(days=day)).weekday() < 5)


def get_collection():
    global _mongo_client
    if _mongo_client is None:
        uri = os.getenv("MONGODB_URI")
        # Этот клиент создается один раз и используется повторно, управляя пулом соединений.
        _mongo_client = MongoClient(uri, server_api=ServerApi('1'), tlsCAFile=certifi.where())
    # Примечание: Мы не возвращаем клиент, чтобы избежать его закрытия в каждой функции.
    # Пул соединений управляется единственным экземпляром MongoClient.
    return _mongo_client.get_database()["totals"]


def calc_plan(date: datetime.date, project):
    collection = get_collection()
    target_year = date.year
    target_month = date.month

    pipeline = [
        {
            "$match": {
                "project": project,
                "month": target_month,
                "year": {"$lt": target_year},
                "value": {"$ne": None}
            }
        },
        {
            "$group": {
                "_id": None,
                "numerator": {"$sum": "$value"},
                "denominator": {
                    "$sum": {"$cond": [{"$gt": ["$value", 0]}, 1, 0]}
                }
            }
        }
    ]
    result_doc = next(collection.aggregate(pipeline), None)

    if result_doc and result_doc.get('denominator', 0) > 0:
        return round(result_doc['numerator'] / result_doc['denominator'] * 1.2)
    return 0


def write_fact(date: datetime.date, fact, project):
    collection = get_collection()
    try:
        target_year = date.year
        target_month = date.month

        collection.update_one(
            {"project": project, "year": target_year, "month": target_month},
            {"$set": {"value": fact}},
            upsert=True
        )
    except Exception as e:
        print(f'Виникла помилка при збереженні даних {fact} в MongoDB:\n{e}')
        traceback.print_exc()


def format_num(num: Optional[Union[int, float]]) -> str:
    """

    :param num:
    :return: string with formatted number like "* ***"
    """
    return "{:,}".format(num).replace(",", " ")


def sort_orders_to_retail_or_wholesale(data: object) -> object:
    gurt = [item for item in data.get('data') if item.get('gurt') == 1]
    retail = [item for item in data.get('data') if item.get('gurt') == 0 or item.get('gurt') is None]
    print({'wholesale': gurt, 'retail': retail})


def get_status_by_id(status: int):
    """
    
    :param status
    :return: name of order status
    """
    return {
        1: "Новий",
        3: "На відправку",
        4: "Відправлено",
        5: "Продаж",
        6: "Відмова",
        7: "Повернення",
        10: "Новий",
        18:"Недозвон",
        11: "Підтверджено",
        31: "На упаковку",
        12: "На відправку",
        13: "Відправлений",
        14: "Продаж",
        33: "Очікуємо гарантію",
        35: "Гарантія отримана",
        36: "Відправити гарантію",
        15: "Відмова",
        16: "Повернення",
        34: "Скасовано"
    }.get(status, f'Невідомий статус: {status}')


def get_poshta_status_by_code(status_code: int) -> str:
    return {
        1: "Відправник самостійно створив цю накладну, але ще не надав до відправки",
        2: "Видалено",
        3: "Номер не знайдено",
        4: "Відправлення у місті відправника",
        41: "Відправлення у місті відправника",
        5: "Відправлення прямує до міста",
        6: "Відправлення у місті. Очікуйте додаткове повідомлення про прибуття",
        7: "Прибув на відділення",
        8: "Прибув на відділення (завантажено в Поштомат)",
        9: "Відправлення отримано",
        10: "Відправлення отримано. Протягом доби ви одержите SMS-повідомлення про надходження грошового переказу та зможете отримати його в касі відділення «Нова пошта»",
        11: "Відправлення отримано. Грошовий переказ видано одержувачу.",
        12: "Нова Пошта комплектує ваше відправлення",
        101: "На шляху до одержувача",
        102: "Відмова від отримання (Відправником створено замовлення на повернення)",
        103: "Відмова від отримання",
        104: "Змінено адресу",
        105: "Припинено зберігання",
        106: "Одержано і створено ЄН зворотньої доставки",
        111: "Невдала спроба доставки через відсутність Одержувача на адресі або зв'язку з ним",
        112: "Дата доставки перенесена Одержувачем",
        10100: "Відправлення прийняте у відділенні",
        20700: "Надходження на сортувальний центр",
        20800: "Відправлення посилки",
        20900: "Відправлення до ВПЗ",
        21500: "Відправлено до відділення",
        21700: "Відправлення у відділенні",
        31100: "Відправлення не вручено під час доставки",
        41000: "Відправлення вручено",
        48000: "Міжнародне відправлення вручено у країні одержувача",
        41010: "Відправлення вручено відправнику",
        31200: "Повернення відправлення",
        31300: "Відправлення перенаправлене до іншого відділення",
        31400: "Невдала спроба вручення (передача на зберігання)",
        10602: "Прийом скасовано",
        10600: "Прийом скасовано (на вимогу Відправника)",
        10601: "Створено онлайн, очікує приймання",
        10603: "Видалено клієнтом",
        21400: "Передано на зберігання"
    }.get(status_code, f"Невідомий статус код: {status_code}")


def shorten_report(text: str):
    replacements = [
        # Единицы измерения
        (r'\bгц\b', 'Hz'),
        (r'\s*дюйм(и|ів|ов)?\s*', '"'),
        (r'\bсм\b', 'см'), 
        (r'б/(в|у)\s*', ''),
        (r'мон(і|и)тор\s+', ''),
        (r'\s*4:3\s+', 'к'),
        (r'\s*16:9\s+', 'ш'),
        (r'\s*в\sа(с+)ортимент(і|е)\s*', ''),
        (r'\s*категор(і|и)я\s*', ''),
        (r'кабель (живлення|питания)\s*', 'КЖ '),
        (r'лазерний\s*принтер\s*', ''),
        (r'ВЕНТИЛЯТОР\s*ПІДЛОГОВИЙ\s*', 'Вентилятор '),
        (r'КАБЕЛЬ VGA - ', ''),
        (r'КАБЕЛЬ USB для принтера ', ''),
        (r'3 pin \(ПК, монітор, принтер\) ', ''),
        (r'\|*', ''),
        # Бренды
        (r'\(\w+\)', '')
    ]
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    return text
