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
from datetime import datetime, timezone
import matplotlib
import traceback
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from timelength import TimeLength


models_path = os.getenv("MODELS_PATH", "model/")

def generate_forecast(horizon: str | None, name: str) -> pd.DataFrame:
    with open(f"{models_path}/prophet-{name}.pkl", "rb") as f:
        model = pickle.load(f)
        tl = TimeLength(horizon)
        start_dt = tl.hence(base=datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M:%S")

        # Create future dataframe
        future = pd.date_range(start=start_dt, periods=1, freq=str(int(tl.to_minutes()))+"min")
        future_df = pd.DataFrame({"ds": future})

        # Predict
        forecast = model.predict(future_df)

        # Filter required fields (yhat and ds are names expected by prophet)
        return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]]

def generate_graph_bytes(data_start_date: str|None, prediction_start_date: str, include_legend: bool, uncertainty: bool, trend: bool, periods: int, name: str, freq: str, components = False) -> pd.DataFrame:
    with open(f"{models_path}/prophet-{name}.pkl", "rb") as f:
        model = pickle.load(f)
        # Create future dataframe
        future = pd.date_range(start=prediction_start_date, periods=periods, freq=freq)
        future_df = pd.DataFrame({"ds": future})

        # Predict
        forecast = model.predict(future_df)

        if components:
            fig = model.plot_components(forecast, uncertainty=uncertainty)
        else:
            fig = model.plot(forecast, include_legend = include_legend, uncertainty=uncertainty)
            if trend:
                add_changepoints_to_plot(fig.gca(), model, forecast)

        if data_start_date:
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
    if isinstance(params, ModelParams):
        parsed_params = params
    else:
        parsed_params: ModelParams = parseModelParams(params)
    print(f"Training model {model_name} using following model params:")
    print(parsed_params)
    model = Prophet(
        yearly_seasonality=parsed_params.yearly_seasonality,
        weekly_seasonality=parsed_params.weekly_seasonality,
        daily_seasonality=parsed_params.daily_seasonality,
        seasonality_mode=parsed_params.seasonality_mode,
    )
    if parsed_params.changepoint_prior_scale is not None and parsed_params.changepoint_prior_scale > 0:
        model.changepoint_prior_scale = parsed_params.changepoint_prior_scale
    if parsed_params.has_holidays:
        model.holidays_prior_scale = parsed_params.holidays_prior_scale
        model.add_country_holidays(parsed_params.country_holidays)

    # by default, add six-hour seasonality
    model.add_seasonality(name='six', period=6/24, fourier_order=10)
    if parsed_params.has_custom_seasonality:
        model.add_seasonality(
            name=parsed_params.custom_seasonality_name,
            period=parsed_params.custom_seasonality_period,
            fourier_order=parsed_params.custom_seasonality_fourier_order,
        )
    # Train model
    model.fit(df)

    # Save model
    os.makedirs(models_path, exist_ok=True)
    p = os.path.abspath(f"{models_path}/prophet-{model_name}.pkl")
    with open(p, "wb") as f:
        pickle.dump(model, f)

    print(f"✅ Model trained and saved to {p}")
    print(f"Size on disk: {human_readable_size(os.path.getsize(p))}")

class ModelParams(BaseModel):
    yearly_seasonality: str | bool | int
    weekly_seasonality: str | bool | int
    daily_seasonality: str | bool | int
    seasonality_mode: str
    has_custom_seasonality: bool = False
    custom_seasonality_name: str = None
    custom_seasonality_period: float = None
    custom_seasonality_fourier_order: int = None
    has_holidays: bool = False
    holidays: str | None = None
    holidays_prior_scale: float | None = None
    changepoint_prior_scale: float
    default_horizon: str

def parseModelParams(params):
    if params == None:
        print("using default params")
        return get_default_model_params()
    mp = ModelParams(
        yearly_seasonality=parseSeasonality(params[0]),
        weekly_seasonality=parseSeasonality(params[1]),
        daily_seasonality=parseSeasonality(params[2]),
        has_custom_seasonality=params[3] is not None and len(params[3]) > 0 and params[4] is not None and params[4] > 0 and params[5] is not None and params[5] > 0,
        seasonality_mode=params[6],
        has_holidays=params[7] is not None and len(params[7]) > 0 and params[8] is not None and params[8] > 0,
        changepoint_prior_scale = 0 if params[9] is None else params[9],
        default_horizon = params[10],
    )
    if mp.has_custom_seasonality:
        mp.custom_seasonality_name=params[3]
        mp.custom_seasonality_period=params[4]
        mp.custom_seasonality_fourier_order=params[5]
    if mp.has_holidays:
        mp.holidays = params[7]
        mp.holidays_prior_scale = params[8]

    return mp

def parseSeasonality(seasonality):
    match seasonality:
        case "False" | "false":
            return False
        case "True" | "true":
            return True
        case "Auto" | "auto":
            return "auto"
        # number
        case _:
            return seasonality

def get_default_model_params():
    m = ModelParams(
        yearly_seasonality=False,
        weekly_seasonality="auto",
        daily_seasonality="auto",
        has_custom_seasonality=False,
        custom_seasonality_name="",
        custom_seasonality_period=0,
        custom_seasonality_fourier_order=0,
        seasonality_mode="additive",
        has_holidays=False,
        holidays="",
        holidays_prior_scale=0,
        changepoint_prior_scale=.1,
        default_horizon="2m",
    )
    return m

def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']:
        if size < 1024.0 or unit == 'PiB':
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"
