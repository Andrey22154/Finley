import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import xgboost as xgb
import psycopg2

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


def smape(y_true, y_pred):
    denominator = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    diff = np.abs(y_pred - y_true) / denominator
    diff[denominator == 0] = 0.0
    return 100 * np.mean(diff)


def save_forecast_to_db(ticker, forecast_dates, predicted_prices):
    try:
        conn = psycopg2.connect(
            dbname="finley",
            user="user",
            password="password",
            host="localhost",
            port="5432"
        )
        cur = conn.cursor()
        for date, price in zip(forecast_dates, predicted_prices):
            cur.execute(
                """
                INSERT INTO forecasts (ticker, forecast_date, predicted_price)
                VALUES (%s, %s, %s)
                ON CONFLICT (ticker, forecast_date) DO UPDATE 
                SET predicted_price = EXCLUDED.predicted_price
                """,
                (ticker, date, price)
            )
        conn.commit()
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()


def prepare_and_train(data, ticker, target_shift):
    data['Return'] = data['Close'].pct_change()
    data['MA_10'] = data['Close'].rolling(window=10).mean()
    data['MA_5'] = data['Close'].rolling(window=5).mean()
    data['MA_3'] = data['Close'].rolling(window=3).mean()
    data['shift_3'] = data['Close'].shift(3)
    data['shift_5'] = data['Close'].shift(5)
    data['shift_8'] = data['Close'].shift(8)
    data.dropna(inplace=True)

    data['Target'] = data['Close'].shift(-target_shift)
    data.dropna(inplace=True)

    X = data[['Return', 'MA_10', 'MA_5', 'MA_3', 'shift_3', 'shift_5', 'shift_8']]
    y = data['Target']

    split_index = len(data) - target_shift
    X_train, X_test = X.iloc[:split_index], X.iloc[split_index:]
    y_train, y_test = y.iloc[:split_index], y.iloc[split_index:]

    model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100)
    model.fit(X_train, y_train)

    preds = model.predict(X_test)

    forecast_dates = y_test.index
    save_forecast_to_db(ticker, forecast_dates, preds)

    return preds


def generate_forecasts(data_dict, target_shift):
    results = {}
    for ticker, data in data_dict.items():
        if data is not None and not data.empty:
            preds = prepare_and_train(data, ticker, target_shift)
            results[ticker] = {
                'Preds': preds
            }
        else:
            results[ticker] = {
                'Preds': []
            }
    return results


# Загрузка данных и прогнозирование
hourly_data = fetch_data_concurrently(tickers, '7d', '1m')
daily_weekly_data = fetch_data_concurrently(tickers, '60d', '2m')
monthly_data = fetch_data_concurrently(tickers, '1y', '1d')

hourly_data = process_data(hourly_data)
daily_weekly_data = process_data(daily_weekly_data)
monthly_data = process_data(monthly_data)

errors_hourly = generate_forecasts(hourly_data, target_shift=30)
errors_daily_weekly = generate_forecasts(daily_weekly_data, target_shift=720)
errors_monthly = generate_forecasts(monthly_data, target_shift=20)


def print_data_info(data_dict):
    for ticker, df in data_dict.items():
        if df is not None:
            print(f"{ticker} данные загружены, размер: {df.shape}")
        else:
            print(f"{ticker} данные не загружены.")
