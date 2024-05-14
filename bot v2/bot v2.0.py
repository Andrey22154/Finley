import os
import io
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

bot_token = os.environ.get(
    'BOT_TOKEN', '6920057637:AAFu4r9aH8ayP3iP-rS87uQ1hgRg_JvAr4s'
)
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


@dp.message_handler(state=Form.input_ticker)
async def fetch_financial_data(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    action = user_data['action']
    ticker = message.text.upper()
    stock = yf.Ticker(ticker)

    if action == "Исторические данные":
        data = stock.history(period="1mo")
        if data.empty:
            await message.answer("Исторические данные не найдены.")
        else:
            await send_long_message(message.chat.id, str(data))
    elif action == "Информация о компании":
        info = stock.info
        if not info:
            await message.answer("Информация о компании не найдена.")
        else:
            await send_long_message(message.chat.id, str(info))
    elif action == "Дивиденды и расщепления":
        dividends = stock.dividends
        splits = stock.splits
        if dividends.empty:
            div_text = "Данные по дивидендам не найдены."
        else:
            div_text = f"Дивиденды:\n{format_series(dividends)}"
        if splits.empty:
            split_text = "Данные по расщеплениям не найдены."
        else:
            split_text = f"Расщепления:\n{format_series(splits)}"
        await message.answer(f"{div_text}\n\n{split_text}")
    elif action == "Финансовые показатели":
        financials = stock.financials
        if financials.empty:
            await message.answer("Финансовые показатели не найдены.")
        else:
            await send_long_message(message.chat.id, str(financials))
    elif action == "Опции и фьючерсы":
        options = stock.options
        if not options:
            await message.answer("Опции и фьючерсы не найдены.")
        else:
            await message.answer(f"Доступные опции: {options}")
    elif action in [
        "Прогноз на день", "Прогноз на неделю", "Прогноз на месяц"
    ]:
        forecast_data = None
        title = f"{action} для {ticker}"
        if action == "Прогноз на день":
            forecast_data = errors_hourly.get(ticker, "Тикер не найден.")
        elif action == "Прогноз на неделю":
            forecast_data = errors_daily_weekly.get(ticker, "Тикер не найден.")
        elif action == "Прогноз на месяц":
            forecast_data = errors_monthly.get(ticker, "Тикер не найден.")
        if isinstance(forecast_data, dict) and 'Preds' in forecast_data:
            predictions = forecast_data['Preds']
            await send_forecast_graph(message.chat.id, predictions, title)
        else:
            await message.answer("Данные для прогноза не найдены.")

    await state.finish()


if __name__ == '__main__':
    executor.start_polling(dp)