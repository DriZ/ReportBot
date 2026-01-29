from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties


class Telegram:
    def __init__(self, token: str):
        self.bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        self.dp = Dispatcher()


    async def send(self, message: str, chat_id: str, topic_id: str = None) -> None:
        try:
            await self.bot.send_message(chat_id, text=message) if topic_id is None else await self.bot.send_message(chat_id, text=message, message_thread_id=topic_id)
        except Exception as e:
            print(e)


    async def start(self):
        try:
            print("Бот запущен!")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            print(e)