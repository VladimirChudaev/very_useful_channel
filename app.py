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

STATE_FILE = "state.txt"

def read_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return f.read().strip()
    return "cbrf"

def write_state(state):
    with open(STATE_FILE, "w") as f:
        f.write(state)

def get_cur():
    url = 'https://www.cbr-xml-daily.ru/daily_json.js'
    response = requests.get(url) # делаем запрос к сайту ЦБРФ
    currencies = response.json() # преобразуем в json-стандарт
    fr_currencies = (
        currencies["Valute"]["KZT"], currencies["Valute"]["CNY"], 
        currencies["Valute"]["AED"], currencies["Valute"]["USD"], currencies["Valute"]["EUR"]
    )
# cоздаем переменную с нужными валютами (в нашемслучае 3 "дружественных" валюты)
    df_currenc = pd.DataFrame(fr_currencies) # создаем датафрэйм
    df_cur = (
        df_currenc[['CharCode', 'Nominal', 'Value']]
        .rename(columns={'CharCode':'Валюта', 'Nominal':'Кол-во', 'Value':'За ед.'})
    ) #вытаскиваем и переименовываем нужные столбцы и переименовываем
    
    return df_cur.to_string(index=None)

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

def main():
    state = read_state()
    
    if state == 'cbrf':
        currencies = get_cur()
        currency_message = "Курсы валют от ЦБРФ:\n\n"
        currency_message += currencies
        send_message(currency_message)
        write_state('moex')
    elif state == 'moex':
        df_sh = get_market()
        df_market_bc = filter_blue_chips(df_sh)
        stock_message = "Акции голубых фишек Мосбиржи:\n\n"
        stock_message += tabulate.tabulate(df_market_bc, headers='keys', tablefmt='plain')
        send_message(stock_message)
        write_state('cbrf')
        
if __name__ == '__main__':
    main()