import json
import os
import datetime
import re
import traceback
from typing import Optional, Union


def bom(date: datetime.date):
    """

    :param date:
    :return: first day of the month
    """
    return date.replace(day=1)


def eom(data: datetime.date):
    """

    :param data:
    :return: last day of the month
    """
    return datetime.date(year=data.year + 1 if data.month == 12 else data.year, month=1 if data.month == 12 else data.month + 1, day=1) - datetime.timedelta(days=1)


def workdays_count(start_date: datetime.date, end_date: datetime.date) -> int:
    return sum(1 for day in range((end_date - start_date).days + 1)
                    if (start_date + datetime.timedelta(days=day)).weekday() < 5)


def calc_plan(date: datetime.date, project):
    with open(f"{os.path.dirname(os.path.abspath(__file__))}/../totals_{project}.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    target_year = date.year
    target_month = date.month

    numerator = sum(
        value for year, months in data.items()
        for month, value in months.items()
        if month == str(target_month) and int(year) < target_year and value is not None
    )

    denominator = sum(
        int(value > 0)
        for year, months in data.items()
        for month, value in months.items()
        if month == str(target_month) and int(year) < target_year and value is not None
    )

    result = round(numerator / denominator * 1.2) if denominator != 0 else 0

    if str(target_year) not in [*data]:
        data[str(target_year)] = {}

    data[str(target_year)][str(target_month)] = result

    return result


def write_fact(date: datetime.date, fact, project):
    try:
        with open(f"{os.path.dirname(os.path.abspath(__file__))}/../totals_{project}.json", "r", encoding="utf-8") as file:
            dat = json.load(file)

        target_year = date.year
        target_month = date.month

        if str(target_year) not in [*dat]:
            dat[str(target_year)] = {}

        dat[str(target_year)][str(target_month)] = fact

        with open(f"{os.path.dirname(os.path.abspath(__file__))}/../totals_{project}.json", "w", encoding="utf-8") as f:
            json.dump(dat, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f'Виникла помилка при збереженні даних {fact} в totals_{project}.json:\n{e}')
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

