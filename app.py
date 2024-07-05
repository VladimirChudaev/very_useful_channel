import requests
import pandas as pd
import json 
import os
from datetime import datetime 
import numpy as np
from itertools import count
from  pprint import pprint
from dotenv import load_dotenv
import tabulate

load_dotenv()

def get_cur():
    url = 'https://www.cbr-xml-daily.ru/daily_json.js'
    response = requests.get(url) # делаем запрос к сайту ЦБРФ
    currencies = response.json() # преобразуем в json-стандарт
    fr_currencies = (
        currencies["Valute"]["KZT"], currencies["Valute"]["CNY"], 
        currencies["Valute"]["AED"], currencies["Valute"]["USD"], currencies["Valute"]["EUR"]
    )
# cоздаем переменную с нужными валютами (в нашем случае 3 "дружественных" и 2 "мировые" валюты)
    df_currenc = pd.DataFrame(fr_currencies) # создаем датафрэйм
    df_cur = (
        df_currenc[['CharCode', 'Nominal', 'Value']]
        .rename(columns={'CharCode':'Валюта', 'Nominal':'Кол-во', 'Value':'За ед.'})
    ) #вытаскиваем и переименовываем нужные столбцы и переименовываем
    
    # Форматируем сообщение в Markdown
    markdown_message = "*Курсы валют от ЦБРФ:*\n"
    for index, row in df_cur.iterrows():
        markdown_message += f"- *{row['Валюта']}*: {row['Кол-во']} = {row['За ед.']} руб.\n"
    
    return markdown_message

# 2. Функция для получения всех данных с API MOEX
def get_market():
    url_hist = "http://iss.moex.com/iss/history/engines/stock/markets/shares/boards/TQBR/securities.json"
    all_data = []  # Список для хранения всех данных

    for stz_row in count(start=0, step=100):
        # Формирование URL с параметром start
        url = f"{url_hist}?start={stz_row}"
        # Выполнение GET-запроса к API
        response = requests.get(url)
        # Разбор JSON-ответа
        result_h = json.loads(response.text)
        # Извлечение данных
        dt_r = result_h['history']['data']
        if not dt_r:
            break  # Выход из цикла, если данные закончились
        # Добавление данных в общий список
        all_data.extend(dt_r)

    # Извлечение имен столбцов
    dt_c = result_h['history']['columns']
    # Создание DataFrame из всех данных
    df_sh = pd.DataFrame(all_data, columns=dt_c)
    # Возвращаем DataFrame
    return df_sh

# 3. Функция для фильтрации данных голубых фишек
def filter_blue_chips(df_sh):
    df_market_bc = df_sh[['SHORTNAME', 'LEGALCLOSEPRICE', 'TRENDCLSPR']]
    df_market_bc = (
        df_market_bc[(df_market_bc['SHORTNAME'] == 'АЛРОСА ао')| (df_market_bc['SHORTNAME'] == 'ГАЗПРОМ ао') | 
        (df_market_bc['SHORTNAME']=='Сбербанк') | (df_market_bc['SHORTNAME'] == 'Татнфт 3ао') | 
        (df_market_bc['SHORTNAME'] == 'ГМКНорНик')|(df_market_bc['SHORTNAME'] =='ММК')|(df_market_bc['SHORTNAME'] =='Магнит ао')|
        (df_market_bc['SHORTNAME'] == 'Полюс')|(df_market_bc['SHORTNAME'] =='НЛМК ао')|(df_market_bc['SHORTNAME'] == 'Новатэк ао')|
        (df_market_bc['SHORTNAME'] == 'Роснефть')|(df_market_bc['SHORTNAME'] == 'СевСт-ао')|(df_market_bc['SHORTNAME'] == 'РУСАЛ ао')|
        (df_market_bc['SHORTNAME'] =='Сургнфгз')|(df_market_bc['SHORTNAME'] == 'ЛУКОЙЛ')
    ]).rename(columns={'SHORTNAME':'Назв.', 'LEGALCLOSEPRICE':'Цена', 'TRENDCLSPR':'Изм.(%)'})
    return df_market_bc

# 4. Функция для отправки сообщения в Telegram

def send_message(message):
    
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    TELEGRAM_CENNAL_ID = os.getenv('TELEGRAM_CENNAL_ID')
    
    
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    
    params = {
        'chat_id': TELEGRAM_CENNAL_ID,
        'text': message
    }
    
    res = requests.post(url, params=params)
    return res.json()

if __name__ == '__main__':
    
    currencies = get_cur() # Получение данных с ЦБРФ
    df_sh = get_market()  # Получение данных с Мосбиржи
    
    # Фильтрация данных голубых фишек
    df_market_bc = filter_blue_chips(df_sh)
    
    # Формируем сообщения для отправки
    currency_message = "Курсы валют от ЦБРФ:\n\n"
    currency_message += currencies
    
    stock_message = "*Акции голубых фишек Мосбиржи:*\n\n"
    for index, row in df_market_bc.iterrows():
        stock_message += f"*{row['Назв.']}*\n"
        stock_message += f"Цена: {row['Цена']}\n"
        stock_message += f"Изм.(%): {row['Изм.(%)']}\n\n"
    
    # Отправляем сообщения в Telegram
    send_message(currency_message)
    send_message(stock_message)