import os
import io
import psycopg2
import nest_asyncio
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# Применение nest_asyncio
nest_asyncio.apply()

bot_token = os.environ.get('BOT_TOKEN', 'token')
bot = Bot(token=bot_token)
dp = Dispatcher(bot, storage=MemoryStorage())

class Form(StatesGroup):
    choosing_action = State()
    input_ticker = State()

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True, selective=True
    )
    buttons = [
        "Прогнозы", "Исторические данные", "Информация о компании",
        "Дивиденды и расщепления", "Финансовые показатели", "Опции и фьючерсы"
    ]
    markup.add(*buttons)
    await message.reply(
        "Выберите тип информации, которую вы хотите получить:",
        reply_markup=markup
    )
    await Form.choosing_action.set()

@dp.message_handler(
    lambda message: message.text in ["Прогнозы"], state=Form.choosing_action
)
async def handle_forecast_request(message: types.Message):
    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True, selective=True
    )
    buttons = [
        "Прогноз на день", "Прогноз на неделю", "Прогноз на месяц", "Назад"
    ]
    markup.add(*buttons)
    await message.reply(
        "Введите тикер акции и выберите прогноз:", reply_markup=markup
    )

@dp.message_handler(
    lambda message: message.text in [
        "Прогноз на день", "Прогноз на неделю", "Прогноз на месяц"
    ], state=Form.choosing_action
)
async def show_forecast(message: types.Message, state: FSMContext):
    await state.update_data(action=message.text)
    await message.reply("Введите тикер акции:")
    await Form.input_ticker.set()

@dp.message_handler(
    lambda message: message.text in [
        "Исторические данные", "Информация о компании",
        "Дивиденды и расщепления", "Финансовые показатели",
        "Опции и фьючерсы"
    ], state=Form.choosing_action
)
async def handle_financial_info_request(message: types.Message, state: FSMContext):
    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True, selective=True
    )
    buttons = ["Назад"]
    markup.add(*buttons)
    await state.update_data(action=message.text)
    await message.reply("Введите тикер акции:", reply_markup=markup)
    await Form.input_ticker.set()

@dp.message_handler(lambda message: message.text == "Назад", state="*")
async def go_back(message: types.Message, state: FSMContext):
    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True, selective=True
    )
    buttons = [
        "Прогнозы", "Исторические данные", "Информация о компании",
        "Дивиденды и расщепления", "Финансовые показатели", "Опции и фьючерсы"
    ]
    markup.add(*buttons)
    await message.reply(
        "Выберите тип информации, которую вы хотите получить:",
        reply_markup=markup
    )
    await Form.choosing_action.set()

async def send_forecast_graph(chat_id, preds, ticker):
    x = np.arange(len(preds))
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.plot(x, preds, label='Predicted', color='red')
    ax.set_title(f'Predicted Prices for {ticker}')
    ax.set_xlabel('Data Points')
    ax.set_ylabel('Price')
    ax.legend()
    ax.grid(True)
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    await bot.send_photo(chat_id, photo=buf)
    buf.close()
    plt.close(fig)

async def send_long_message(chat_id, text):
    max_length = 4096
    for i in range(0, len(text), max_length):
        await bot.send_message(chat_id, text[i:i + max_length])

def format_series(series):
    formatted = series.apply(
        lambda x: x.strftime('%Y-%m-%d') if isinstance(x, pd.Timestamp) else x
    )
    return '\n'.join(f"{idx.date()} {val}" for idx, val in formatted.items())

def fetch_forecasts_from_db(ticker, action):
    try:
        conn = psycopg2.connect(
            dbname="finley",
            user="user",
            password="password",
            host="localhost",
            port="5432"
        )
        cur = conn.cursor()
        cur.execute(
            """
            SELECT forecast_date, predicted_price
            FROM forecasts
            WHERE ticker = %s
            ORDER BY forecast_date
            """,
            (ticker,)
        )
        rows = cur.fetchall()
        cur.close()
        return rows
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        return []
    finally:
        if conn is not None:
            conn.close()

@dp.message_handler(state=Form.input_ticker)
async def fetch_financial_data(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    action = user_data['action']
    ticker = message.text.upper()

    if action == "Прогнозы":
        forecasts = fetch_forecasts_from_db(ticker, action)
        if forecasts:
            forecast_message = "\n".join([f"{date}: {price}" for date, price in forecasts])
            await message.reply(f"Прогнозы для {ticker}:\n{forecast_message}")
        else:
            await message.reply(f"Прогнозы для {ticker} не найдены.")
    else:
        await message.reply("Функционал в разработке.")

if __name__ == '__main__':
    executor.start_polling(dp)
