from aiogram import Bot, Dispatcher, executor, types
import os
import requests
from bs4 import BeautifulSoup
import nest_asyncio

import numpy as np
import pandas as pd

from dostoevsky.tokenization import RegexTokenizer
from dostoevsky.models import FastTextSocialNetworkModel
from flashtext import KeywordProcessor


nest_asyncio.apply()

bot_token = os.environ.get('BOT_TOKEN', 'token')
bot = Bot(token=bot_token)
dp = Dispatcher(bot)

channels = [
    'channels name'
]

def calculate_news_score(result):
    positive = result[0].get('positive', 0)
    neutral = result[0].get('neutral', 0)
    negative = result[0].get('negative', 0)
    skip = result[0].get('skip', 0)

    weighted_sum = (positive * 5 + neutral * 2 - negative * 2.5)
    total_probability = positive + neutral + negative + skip

    if total_probability != 0:
        score = 2.5 + (weighted_sum / total_probability)
    else:
        score = 2.5

    score = max(0, min(5, score))
    return round(score)

def analyze_news(news_list):
    results_list = []
    for news in news_list:
        news_text = ' '.join(news)
        tokens = tokenizer.split(news_text)
        result = model.predict([news_text], k=4)
        results_list.append(result[0])
    return results_list


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply("Привет! Я твой финансовый помощник. Введи название компании, по которой хочешь получить обратную связь:")

def generate_response(score, keyword):
    if score >= 4:
        return f"По итогам оценки последних новостей, компания {keyword} показала отличные результаты. Продолжайте следить за дальнейшими обновлениями!"
    elif score >= 3:
        return f"По итогам оценки последних новостей, компания {keyword} показала хорошие результаты. Есть некоторые области для улучшения, но в целом положительная динамика."
    elif score >= 2:
        return f"По итогам оценки последних новостей, результаты компании {keyword} оставляют желать лучшего. Рекомендуем обратить внимание на потенциальные риски и возможности для улучшения."
    else:
        return f"По итогам оценки последних новостей, компания {keyword} показала недостаточно хорошие результаты. Возможно, стоит пересмотреть стратегию или ожидать значимых изменений в управлении или продуктах."

@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def process_text(message: types.Message):
    keyword = message.text.strip()
    results = []

    for channel_url in channels:
        response = requests.get(channel_url)
        soup = BeautifulSoup(response.content, "html.parser")
        texts = soup.find_all(text=True)
        channel_results = [text for text in texts if keyword.lower() in text.lower()]

        if channel_results:
            news_text = ' '.join(channel_results[:25])
            results.append(news_text)

    if results:
        model_news = analyze_news(results)
        scores = calculate_news_score(model_news)#[calculate_news_score(result) for result in model_news]  
        #average_score = sum(scores) / len(scores) if scores else 0
        reply_text = generate_response(scores, keyword)
    else:
        reply_text = f"Новостей с '{keyword}' не найдено."

    await message.reply(reply_text)
    print(results)


if __name__ == '__main__':
    executor.start_polling(dp)