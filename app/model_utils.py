import io
import os
import os.path
import pandas as pd
import logging
logging.getLogger("prophet.plot").disabled = True
from prophet import Prophet
from prophet.plot import add_changepoints_to_plot
from pydantic import BaseModel
import pickle
from datetime import datetime, timedelta
import matplotlib
import traceback
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

def generate_graph_bytes(data_start_date: str|None, prediction_start_date: str, include_legend: bool, uncertainty: bool, trend: bool, periods: int, name: str, freq: str, components = False) -> pd.DataFrame:
    with open(f"{models_path}/prophet-{name}.pkl", "rb") as f:
        model = pickle.load(f)
        # Create future dataframe
        future = pd.date_range(start=prediction_start_date, periods=periods, freq=freq)
        future_df = pd.DataFrame({"ds": future})

        # Predict
        forecast = model.predict(future_df)

            # bar = forecast[forecast["ds"] >= data_start_date]

        # print(bar)

        if components:
            fig = model.plot_components(forecast, uncertainty=uncertainty)
        else:
            fig = model.plot(forecast, include_legend = include_legend, uncertainty=uncertainty)
            if trend:
                add_changepoints_to_plot(fig.gca(), model, forecast)

        if data_start_date:
            print("sdfsfd")
            ax = fig.gca()
            ax.set_xlim(pd.to_datetime([data_start_date, forecast["ds"].max()]))

        img_buf = io.BytesIO()
        fig.savefig(img_buf, format='png')
        plt.close(fig)
        img_buf.seek(0)

        return img_buf

def delete_serialized_model(model_name):
    p = os.path.abspath(f"{models_path}/prophet-{model_name}.pkl")
    try:
        os.remove(p)
        print(f"✅ Model {p} was deleted")
    except Exception as e:
        print(traceback.format_exc())

def train_and_save(model_name, params, df):
    parsed_params: ModelParams = parseModelParams(params)
    print(f"Training model {model_name} using following model params:")
    print(parsed_params)
    model = Prophet(
        changepoint_prior_scale=0.01,
        yearly_seasonality=parsed_params.yearly_seasonality,
        weekly_seasonality=parsed_params.weekly_seasonality,
        daily_seasonality=parsed_params.daily_seasonality,
        seasonality_mode=parsed_params.seasonality_mode,
    )
    # by default, add six-hour seasonality
    model.add_seasonality(name='six', period=6/24, fourier_order=10)
    if parsed_params.has_custom_seasonality:
        model.add_seasonality(name='custom', period=parsed_params.custom_seasonality_period, fourier_order=parsed_params.custom_seasonality_fourier_order)
    # Train model
    model.fit(df)

    # Save model
    os.makedirs(models_path, exist_ok=True)
    p = os.path.abspath(f"{models_path}/prophet-{model_name}.pkl")
    with open(p, "wb") as f:
        pickle.dump(model, f)
    # with open("model/prophet.json", "w") as fjson:
    #     fjson.write(model_to_json(model))

    print(f"✅ Model trained and saved to {p}")
    print(f"Size on disk: {human_readable_size(os.path.getsize(p))}")
    # print("✅ Model trained and saved to model/prophet.json")

class ModelParams(BaseModel):
    yearly_seasonality: str | bool | int
    weekly_seasonality: str | bool | int
    daily_seasonality: str | bool | int
    seasonality_mode: str
    has_custom_seasonality: bool
    custom_seasonality_period: float
    custom_seasonality_fourier_order: int

def parseModelParams(params):
    if params == None:
        print("using default params")
        return get_default_model_params()
    return ModelParams(
        yearly_seasonality=parseSeasonality(params[0]),
        weekly_seasonality=parseSeasonality(params[1]),
        daily_seasonality=parseSeasonality(params[2]),
        seasonality_mode=params[5],
        has_custom_seasonality=params[3] > 0 and params[4] > 0,
        custom_seasonality_period=params[3],
        custom_seasonality_fourier_order=params[4],
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

def get_default_model_params():
    return ModelParams(
        yearly_seasonality=False,
        weekly_seasonality=True,
        daily_seasonality=True,
        seasonality_mode="additive",
        has_custom_seasonality=True,
        custom_seasonality_period=0.04167,
        custom_seasonality_fourier_order=4,
    )

def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']:
        if size < 1024.0 or unit == 'PiB':
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"
