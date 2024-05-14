import numpy as np
import xgboost as xgb

def smape(y_true, y_pred):
    denominator = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    diff = np.abs(y_pred - y_true) / denominator
    diff[denominator == 0] = 0.0
    return 100 * np.mean(diff)

def prepare_and_train(data, target_shift):
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

    return preds

def generate_forecasts(data_dict, target_shift):
    results = {}
    for ticker, data in data_dict.items():
        if data is not None and not data.empty:
            model, mae, rmse, smape_value, preds = prepare_and_train(data, target_shift)
            results[ticker] = {
                'Preds': preds
            }
        else:
            results[ticker] = {
                'Preds': preds
            }
    return results


errors_hourly = generate_forecasts(hourly_data, target_shift=30)  
errors_daily_weekly = generate_forecasts(daily_weekly_data, target_shift=720)  
errors_monthly = generate_forecasts(monthly_data, target_shift=20)  