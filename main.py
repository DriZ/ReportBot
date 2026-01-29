import asyncio
import traceback
import schedule
import os
from modules import SalesDrive, Telegram
from dotenv import load_dotenv
from time import strftime
import pystray
from PIL import Image
import sys
import threading
import ctypes
from datetime import date, timedelta


ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

def create_tray_icon():
    image = Image.open('./tg.png')
    menu = (pystray.MenuItem("Выход", exit_app),)
    icon = pystray.Icon("ReportBot", image, "ReportBot", menu)
    icon.run()

def exit_app(icon, item):
    icon.stop()
    sys.exit()

threading.Thread(target=create_tray_icon, daemon=True).start()


load_dotenv()

async def send_report(bot: Telegram, chat_id, project: str, topic_id: str = None):
    sd = SalesDrive(os.getenv("URL"), os.getenv(project))
    report = await sd.generate_report(chat_id)
    await bot.send('\n'.join(report), chat_id, topic_id)
    print("Report sent at", strftime("%Y-%m-%d %H:%M:%S"))


async def run_bot(bot: Telegram):
    print("Запускаю бота...")
    await bot.start()


async def start():
    bot = Telegram(os.getenv("TG_TOKEN"))

    asyncio.create_task(run_bot(bot))

    schedule.every().day.at("19:00").do(lambda: asyncio.create_task(send_report(bot, chat_id=os.getenv('SKOK_REPORTS_CHAT_ID'), project='SKOK')))
    schedule.every().day.at("19:01").do(lambda: asyncio.create_task(send_report(bot, chat_id=os.getenv('POK_CHAT_ID'), project='POK')))
    schedule.every().day.at("21:00").do(lambda: asyncio.create_task(send_report(bot, chat_id=os.getenv('SKOK_REPORTS_CHAT_ID'), project='SKOK')))
    schedule.every().day.at("21:01").do(lambda: asyncio.create_task(send_report(bot, chat_id=os.getenv('POK_CHAT_ID'), project='POK')))
    await send_report(bot, chat_id = os.getenv('ADMIN2_ID'), project='SKOK')
    await send_report(bot, chat_id = os.getenv('ADMIN2_ID'), project='POK')


    while True:
        schedule.run_pending()
        await asyncio.sleep(1)


if __name__ == '__main__':
    try:
        asyncio.run(start())
    except Exception as e:
        print("Ошибка:", e)
        traceback.print_exc()
