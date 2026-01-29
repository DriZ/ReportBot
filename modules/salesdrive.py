import aiohttp, os
from modules.utils import bom, eom, calc_plan, workdays_count, format_num, get_status_by_id, get_poshta_status_by_code, shorten_report, write_fact
from datetime import date, timedelta, datetime
from time import strftime


wholesale_plan_skok = 150000

class SalesDrive:
    def __init__(self, url: str, token: str):
        self.url = url
        self.token = token


    async def _request(self, params: object = None) -> object:
        if params is None:
            params = {
                'filter[orderTime][from]': strftime('%Y-%m-%d'),
                'filter[orderTime][to]': strftime('%Y-%m-%d'),
                'page': 1,
                'per_page': 50,
            }
        async with aiohttp.ClientSession() as session:
            async with session.get(url=self.url, headers={'Form-Api-Key': self.token}, params=params) as response:
                return await response.json()


    async def new_orders_today(self, data) -> object:
        return await self._request({
            'filter[orderTime][from]': data['from'].strftime('%Y-%m-%d'),
            'filter[orderTime][to]': data['to'].strftime('%Y-%m-%d'),
            'page': 1,
            'per_page': 50,
        })


    async def new_retail_today(self, data) -> object:
        return await self._request({
            'filter[gurt]': 0,
            'filter[orderTime][from]': data['from'].strftime('%Y-%m-%d'),
            'filter[orderTime][to]': data['to'].strftime('%Y-%m-%d'),
            'page': 1,
            'per_page': 50,
        })


    async def new_wholesale_today(self, data) -> object:
        return await self._request({
            'filter[gurt]': 1,
            'filter[orderTime][from]': data['from'].strftime('%Y-%m-%d'),
            'filter[orderTime][to]': data['to'].strftime('%Y-%m-%d'),
            'page': 1,
            'per_page': 50,
        })


    async def delivered_orders(self, data) -> object:
        return await self._request({
            'filter[paymentDate][from]': data['from'].strftime('%Y-%m-%d'),
            'filter[paymentDate][to]': data['to'].strftime('%Y-%m-%d'),
            'page': 1,
            'per_page': 50,
        })


    async def delivered_retail(self, data) -> object:
        return await self._request({
            'filter[gurt]': 0,
            'filter[paymentDate][from]': data['from'].strftime('%Y-%m-%d'),
            'filter[paymentDate][to]': data['to'].strftime('%Y-%m-%d'),
            'page': 1,
            'per_page': 50,
        })


    async def delivered_retail_today(self, data) -> object:
        return await self._request({
            'filter[gurt]': 0,
            'filter[paymentDate][from]': data['from'].strftime('%Y-%m-%d'),
            'filter[paymentDate][to]': data['to'].strftime('%Y-%m-%d'),
            'page': 1,
            'per_page': 50,
        })


    async def delivered_wholesale(self, data) -> object:
        return await self._request({
            'filter[gurt]': 1,
            'filter[paymentDate][from]': data['from'].strftime('%Y-%m-%d'),
            'filter[paymentDate][to]': data['to'].strftime('%Y-%m-%d'),
            'page': 1,
            'per_page': 50,
        })


    async def delivered_wholesale_today(self, data) -> object:
        return await self._request({
            'filter[gurt]': 1,
            'filter[paymentDate][from]': data['to'].strftime('%Y-%m-%d'),
            'filter[paymentDate][to]': data['to'].strftime('%Y-%m-%d'),
            'page': 1,
            'per_page': 50,
        })


    async def delivered_orders_today(self) -> object:
        return await self.delivered_orders(data_from=date.today().strftime('%Y-%m-%d'), data_to=date.today().strftime('%Y-%m-%d'))


    async def generate_report(self, chat_id, data: object = None):
        if data is None:
            data = {}
            data['from'], data['to'] = date.today(), date.today()

        new_orders_today: object = await self.new_orders_today(data)
        retail_total = await self.delivered_retail({'from': bom(data['from']), 'to': eom(data['to'])})
        retail_sum = retail_total.get("totals", {}).get("paymentAmount", 0)
        write_fact(data['from'], retail_sum, 'skok' if self.token is os.getenv('SKOK') else 'pok')
        today_retail = await self.delivered_retail_today(data)
        today_retail_sum = today_retail.get("totals", {}).get("paymentAmount", 0)
        today_retail_count = today_retail.get("totals", {}).get("count", 0)
        plan_sum = calc_plan(data['from'], 'skok' if self.token is os.getenv('SKOK') else 'pok')

        today_wholesale = await self.delivered_wholesale_today(data)
        today_wholesale_sum = today_wholesale.get("totals", {}).get("paymentAmount", 0)
        today_wholesale_count = today_wholesale.get("totals", {}).get("count", 0)
        wholesale_sum = await self.delivered_wholesale({'from': bom(data['from']), 'to': eom(data['to'])})
        wholesale_sum = wholesale_sum.get("totals", {}).get("paymentAmount", 0)

        fact_sum = retail_sum + wholesale_sum
        plan_perc = round(fact_sum / plan_sum * 100, 2)

        workdays_in_month = workdays_count(bom(data['from']), eom(data['to']))
        days_left = workdays_count(data['from'] + timedelta(days=1), eom(data['to']))

        forecast = round(fact_sum / (workdays_in_month - days_left) * workdays_in_month)
        forecast_perc = round(forecast / plan_sum * 100, 2)

        report_lines = [f'Дата: {data["from"].strftime("%d.%m.%Y")} р.\n']

        report_lines.append(
            f""" 🤑ПРОЕКТ {'КомпікОК' if self.token is os.getenv("SKOK") else "ПринтерОК"} B2C & B2B🤑
План: {format_num(plan_sum)} грн.
Факт: {format_num(fact_sum)} грн:
    - B2C: {format_num(retail_sum)} грн.
    - B2B: {format_num(wholesale_sum)} грн.
Прогноз: {format_num(forecast)} грн. {forecast_perc}(%)
    
Одержано сьогодні на: {today_retail_sum+today_wholesale_sum} грн. ({today_retail_count+today_wholesale_count} відправок)   
Виконання: {plan_perc}   %\n\n """
        )

        for item in new_orders_today.get('data', []):
            formatted_products = " + ".join(
                f'{product["text"]} <b>{"x" + str(product["amount"]) if product["amount"] > 1 else ""}</b>' for product in item["products"]
            )

            report_lines.append(
                f'<pre><code class="language-ruby">{"ОПТ | " if item.get("gurt") else ""}{item["id"]} | {shorten_report(formatted_products)} | {item["paymentAmount"]} грн. \nСтатус: {get_status_by_id(item.get("statusId"))}\nТТН: {"Не додано" if item.get("ord_delivery_data")[0].get("trackingNumber") is None else item.get("ord_delivery_data")[0].get("trackingNumber")}{"" if item.get("ord_delivery_data")[0].get("statusCode") is None else ": "+get_poshta_status_by_code(item.get("ord_delivery_data")[0].get("statusCode"))}</code></pre>\n'
            )

        report_lines.append(
            f'\nСьогодні нових замовлень {new_orders_today.get("totals", {}).get("paymentAmount", "0")} грн. ({new_orders_today.get("totals", {}).get("count", "0")} шт.)'
        )

        return report_lines
