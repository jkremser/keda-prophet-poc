import io
import os
import pandas as pd
import logging
logging.getLogger("prophet.plot").disabled = True
from prophet import Prophet
import pickle
from prophet.serialize import model_to_json, model_from_json
from datetime import datetime, timedelta
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


models_path = os.getenv("MODELS_PATH", "model/")

# Load model
# with open("model/prophet.json", "rb") as fjson:
#     model = model_from_json(fjson.read())

def generate_forecast(start_date: str, periods: int, name: str) -> pd.DataFrame:
    with open(f"{models_path}/prophet-{name}.pkl", "rb") as f:
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
    with open(f"{models_path}/prophet-{name}.pkl", "rb") as f:
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

def delete_serialized_model(model_name):
    os.remove(f"{models_path}/prophet-{model_name}.pkl")
    print(f"✅ Model {models_path}/prophet-{model_name}.pkl was deleted")

def train_and_save(model_name, params, df):
    parsed_params = parseModelParams(params)
    model = Prophet(
        changepoint_prior_scale=0.01,
        yearly_seasonality=parsed_params.yearly_seasonality,
        weekly_seasonality=parsed_params.weekly_seasonality,
        daily_seasonality=parsed_params.daily_seasonality,
        seasonality_mode=parsed_params.seasonality_mode,
    )
    
    if parsed_params.has_custom_seasonality:
        model.add_seasonality(name='custom', period=parsed_params.custom_seasonality_period, fourier_order=parsed_params.custom_seasonality_fourier_order)
    # Train model
    model.fit(df)

    # Save model
    print(models_path)
    os.makedirs(models_path, exist_ok=True)
    with open(f"{models_path}/prophet-{model_name}.pkl", "wb") as f:
        pickle.dump(model, f)
    # with open("model/prophet.json", "w") as fjson:
    #     fjson.write(model_to_json(model))

    print(f"✅ Model trained and saved to {models_path}/prophet-{model_name}.pkl")
    # print("✅ Model trained and saved to model/prophet.json")

class ModelParams():
    yearly_seasonality: str | bool | int
    weekly_seasonality: str | bool | int
    daily_seasonality: str | bool | int
    seasonality_mode: str
    has_custom_seasonality: bool


def parseModelParams(params):
    ModelParams(
        yearly_seasonality=parseSeasonality(params[0]),
        weekly_seasonality=parseSeasonality(params[1]),
        daily_seasonality=parseSeasonality(params[2]),
        seasonality_mode=params[5],
        has_custom_seasonality=params[3] > 0 and params[4] > 0
    )

def parseSeasonality(seasonality):
    match seasonality:
        case "False":
            return False
        case "True":
            return True
        case "auto":
            return "auto"
        case _:
            return seasonality
