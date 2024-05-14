import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

# Загрузка списка тикеров S&P 500
data = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
tickers = data['Symbol'].tolist()

def get_data(ticker, period="1mo", interval="1d"):
    try:
        stock = yf.Ticker(ticker)
        return stock.history(period=period, interval=interval)
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return pd.DataFrame()

def fetch_data_concurrently(tickers, period, interval):
    all_data = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(get_data, ticker, period, interval): ticker 
            for ticker in tickers
        }
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                all_data[ticker] = future.result()
            except Exception as e:
                print(f"Error processing data for {ticker}: {e}")
    return all_data

def process_data(all_data):
    def filter_and_fill(df):
        max_size = max(
            (df.size for df in all_data.values() if not df.empty), 
            default=0
        )
        if df.size < 0.95 * max_size:
            return None
        df = df.interpolate().fillna(df.mean())
        return df

    return {
        ticker: filter_and_fill(df) 
        for ticker, df in all_data.items() if not df.empty
    }

hourly_data = fetch_data_concurrently(tickers, '7d', '1m')
daily_weekly_data = fetch_data_concurrently(tickers, '60d', '2m')
monthly_data = fetch_data_concurrently(tickers, '1y', '1d')

hourly_data = process_data(hourly_data)
daily_weekly_data = process_data(daily_weekly_data)
monthly_data = process_data(monthly_data)

def print_data_info(data_dict):
    for ticker, df in data_dict.items():
        if df is not None:
            print(f"{ticker} данные загружены, размер: {df.shape}")
        else:
            print(f"{ticker} данные не загружены.")