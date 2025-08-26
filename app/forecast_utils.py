import pandas as pd
from prophet import Prophet
import pickle
from prophet.serialize import model_to_json, model_from_json
from datetime import datetime, timedelta

# Load model
# with open("model/prophet_model.pkl", "rb") as f:
#     model = pickle.load(f)
with open("model/prophet.json", "rb") as fjson:
    model = model_from_json(fjson.read())

def generate_forecast(start_date: str, periods: int, name: str) -> pd.DataFrame:
    start_dt = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")

    # Create future dataframe
    future = pd.date_range(start=start_dt, periods=periods, freq="h")
    future_df = pd.DataFrame({"ds": future, "name": name})

    # Predict
    forecast = model.predict(future_df)

    # Filter required fields (yhat and ds are names expected by prophet)
    return forecast[["ds", "yhat"]]
