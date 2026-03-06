import aiohttp
import os
import ssl
import certifi
from modules.utils import bom, eom, calc_plan, workdays_count, format_num, get_status_by_id, get_poshta_status_by_code, shorten_report, write_fact
from datetime import date, timedelta
from time import strftime

class SalesDrive:
    def __init__(self, url: str, token: str):
        self.url = url
        self.token = token
        # Определяем имя проекта один раз при инициализации для чистоты кода.
        # Используем '==' для сравнения строк вместо 'is'.
        if self.token == os.getenv('SKOK'):
            self.project_name = 'skok'
        else:
            self.project_name = 'pok'

        # Создаем SSL-контекст, который использует сертификаты из `certifi`
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        self._session = aiohttp.ClientSession(connector=connector)


    async def close(self):
        """Закрывает сессию aiohttp."""
        await self._session.close()

    async def _request(self, params: object = None) -> object:
        if params is None:
            params = {
                'filter[orderTime][from]': strftime('%Y-%m-%d'),
                'filter[orderTime][to]': strftime('%Y-%m-%d'),
                'page': 1,
                'per_page': 50,
            }
        async with self._session.get(url=self.url, headers={'Form-Api-Key': self.token}, params=params) as response:
            return await response.json()

    async def _get_orders(self, date_from: date, date_to: date, gurt: int = None, optOpt: int = None, date_filter_type: str = 'orderTime', per_page: int = 50):
        params = {
            f'filter[{date_filter_type}][from]': date_from.strftime('%Y-%m-%d'),
            f'filter[{date_filter_type}][to]': date_to.strftime('%Y-%m-%d'),
            'page': 1,
            'per_page': per_page,
        }
        if gurt is not None:
            params['filter[gurt]'] = gurt
        if optOpt is not None:
            params['filter[optOpt]'] = optOpt
        return await self._request(params)


    async def new_orders_today(self, data) -> object:
        return await self._get_orders(data['from'], data['to'])


    async def new_retail_today(self, data) -> object:
        return await self._get_orders(data['from'], data['to'], gurt=0, optOpt=0)


    async def new_wholesale_today(self, data) -> object:
        return await self._get_orders(data['from'], data['to'], gurt=1, optOpt=0)


    async def delivered_orders(self, data) -> object:
        return await self._get_orders(data['from'], data['to'], date_filter_type='paymentDate')


    async def delivered_retail(self, data) -> object:
        return await self._get_orders(data['from'], data['to'], gurt=0, optOpt=0, date_filter_type='paymentDate')


    async def delivered_opt_opt(self, data) -> object:
        return await self._get_orders(data['from'], data['to'], gurt=0, optOpt=1, date_filter_type='paymentDate')


    async def delivered_retail_today(self, data) -> object:
        return await self._get_orders(data['from'], data['to'], gurt=0, optOpt=0, date_filter_type='paymentDate')


    async def delivered_opt_opt_today(self, data) -> object:
        return await self._get_orders(data['from'], data['to'], gurt=0, optOpt=1, date_filter_type='paymentDate')


    async def delivered_wholesale(self, data) -> object:
        return await self._get_orders(data['from'], data['to'], gurt=1, optOpt=0, date_filter_type='paymentDate')


    async def delivered_wholesale_today(self, data) -> object:
        return await self._get_orders(data['from'], data['to'], gurt=1, optOpt=0, date_filter_type='paymentDate')


    async def delivered_orders_today(self) -> object:
        today = date.today()
        return await self.delivered_orders({'from': today, 'to': today})


    async def generate_report(self, data: object = None):
        if data is None:
            data = {}
            data['from'], data['to'] = date.today(), date.today()

        new_orders_today: object = await self.new_orders_today(data)
        retail_total = await self.delivered_retail({'from': bom(data['from']), 'to': eom(data['to'])})
        retail_sum = retail_total.get("totals", {}).get("paymentAmount", 0)
        today_retail = await self.delivered_retail_today(data)
        today_retail_sum = today_retail.get("totals", {}).get("paymentAmount", 0)
        today_retail_count = today_retail.get("totals", {}).get("count", 0)

        today_wholesale = await self.delivered_wholesale_today(data)
        today_wholesale_sum = today_wholesale.get("totals", {}).get("paymentAmount", 0)
        today_wholesale_count = today_wholesale.get("totals", {}).get("count", 0)
        wholesale_sum = await self.delivered_wholesale({'from': bom(data['from']), 'to': eom(data['to'])})
        wholesale_sum = wholesale_sum.get("totals", {}).get("paymentAmount", 0)

        write_fact(data['from'], retail_sum+wholesale_sum, self.project_name)

        opt_opt_total: object = await self.delivered_opt_opt({'from': bom(data['from']), 'to': eom(data['to']), 'optOpt': 1, 'gurt': 0})
        opt_opt_sum = opt_opt_total.get("totals", {}).get("paymentAmount", 0)
        today_opt_opt = await self.delivered_opt_opt_today(data)
        today_opt_opt_sum = today_opt_opt.get("totals", {}).get("paymentAmount", 0)
        today_opt_opt_count = today_opt_opt.get("totals", {}).get("count", 0)

        plan_sum = calc_plan(data['from'], self.project_name)

        fact_sum = retail_sum + wholesale_sum
        plan_perc = round(fact_sum / plan_sum * 100, 2)

        workdays_in_month = workdays_count(bom(data['from']), eom(data['to']))
        days_left = workdays_count(data['from'] + timedelta(days=1), eom(data['to']))

        forecast = round(fact_sum / (workdays_in_month - days_left) * workdays_in_month)
        forecast_perc = round(forecast / plan_sum * 100, 2)

        report_lines = [f'Дата: {data["from"].strftime("%d.%m.%Y")} р.\n']

        report_lines.append(
            f""" 🤑ПРОЕКТ {'КомпікОК' if self.project_name == "skok" else "ПринтерОК"} B2C & B2B🤑
План: {format_num(plan_sum)} грн.
Факт: {format_num(fact_sum)} грн:
    - B2C: {format_num(retail_sum)} грн.
    - B2B: {format_num(wholesale_sum)} грн.
Прогноз: {format_num(forecast)} грн. {forecast_perc}(%)
{f"""
<i>B2B²: {format_num(opt_opt_sum)} грн.</i>""" if self.project_name == "pok" else ""}
    
Одержано сьогодні на: {today_retail_sum+today_wholesale_sum+today_opt_opt_sum} грн. ({today_retail_count+today_wholesale_count+today_opt_opt_count} відправок)   
Виконання: {plan_perc}   %\n\n """
        )

        for item in new_orders_today.get('data', []):
            formatted_products = " + ".join(
                f'{product["text"]} <b>{"x" + str(product["amount"]) if product["amount"] > 1 else ""}</b>' for product in item["products"]
            )

            delivery_data = item.get("ord_delivery_data", [])
            ttn_info = "Не додано"
            if delivery_data is not None and len(delivery_data[0]) > 0 and delivery_data[0].get("trackingNumber"):
                ttn_info = delivery_data[0].get("trackingNumber")
                status_code = delivery_data[0].get("statusCode")
                if status_code is not None:
                    ttn_info += f': {get_poshta_status_by_code(status_code)}'

            report_lines.append(
                f'<pre><code class="language-ruby">{"ОПТ | " if item.get("gurt") else ""}{"ОПТ² | " if item.get("optOpt") else ""}{item["id"]} | {shorten_report(formatted_products)} | {item["paymentAmount"]} грн. \nСтатус: {get_status_by_id(item.get("statusId"))}\nТТН: {ttn_info}</code></pre>\n'
            )

        report_lines.append(
            f'\nСьогодні нових замовлень {new_orders_today.get("totals", {}).get("paymentAmount", "0")} грн. ({new_orders_today.get("totals", {}).get("count", "0")} шт.)'
        )

        return report_lines
