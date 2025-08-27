import io
import pandas as pd
from prophet import Prophet
import pickle
from prophet.serialize import model_to_json, model_from_json
from datetime import datetime, timedelta
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# from .feed_sql import feed_db

# feed_db()

# Load model
# with open("model/prophet.json", "rb") as fjson:
#     model = model_from_json(fjson.read())

def generate_forecast(start_date: str, periods: int, name: str) -> pd.DataFrame:
    with open(f"model/prophet-{name}.pkl", "rb") as f:
        model = pickle.load(f)
        start_dt = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")

        # Create future dataframe
        future = pd.date_range(start=start_dt, periods=periods, freq="h")
        future_df = pd.DataFrame({"ds": future})

        # Predict
        forecast = model.predict(future_df)

        # Filter required fields (yhat and ds are names expected by prophet)
        return forecast[["ds", "yhat"]]

def generate_graph_bytes(start_date: str, periods: int, name: str, freq: str) -> pd.DataFrame:
    with open(f"model/prophet-{name}.pkl", "rb") as f:
        model = pickle.load(f)
        start_dt = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")

        # Create future dataframe
        future = pd.date_range(start=start_dt, periods=periods, freq=freq)
        future_df = pd.DataFrame({"ds": future})

        # Predict
        forecast = model.predict(future_df)

        fig = model.plot(forecast)

        img_buf = io.BytesIO()
        fig.savefig(img_buf, format='png')
        plt.close(fig)
        img_buf.seek(0)

        return img_buf
