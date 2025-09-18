# main.py

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse
import logging
import os
import traceback
from pydantic import BaseModel
from typing import List
from datetime import datetime, timedelta

from .common_utils import to_bool
from .model_utils import generate_forecast, generate_graph_bytes
from .db_utils import feed_db, retrain_and_save, insert_measurement, insert_multiple_measurements, upsert_mod, list_models_db, delete, reset_database, init_database

description = """
KEDA Prophet - Exposing multiple Prophet models via REST api for KEDA. 🚀

<img src="https://kedify.io/assets/images/logo.svg" alt="logo" width="100"/>
"""

app = FastAPI(
    title="KEDA Prophet",
    description=description,
    version=os.getenv("VERSION", "main"),
    )
logger = logging.getLogger('uvicorn.info')
db_ready = False

# Input schemas
class CreateModelRequest(BaseModel):
    name: str
    yearly_seasonality: str | None = "False" # optional, default: False Can be 'auto', True, False, or a number of Fourier terms to generate.
    weekly_seasonality: str | None = "auto" # optional, default: 'auto'
    daily_seasonality: str | None = "auto"  # optional, default: 'auto'
    custom_seasonality_period: float | None = 0 # in days, so 1/24 represents hourly
    custom_seasonality_fourier_order: int | None = 0
    seasonality_mode: str | None = "additive" # 'additive' (default) or 'multiplicative'.

class ForecastRequest(BaseModel):
    start_date: str  # e.g., "2025-05-01 00:00:00"
    periods: int     # Number of future hours to predict

class MetricStoreRequest(BaseModel):
    date: str      # e.g., "2025-05-01 00:00:00"
    value: float   # Measured value

class MetricCsvStoreRequest(BaseModel):
    csvUrl: str

# Output schemas
class ForecastPoint(BaseModel):
    ds: str
    yhat: float

class ForecastResponse(BaseModel):
    forecast: List[ForecastPoint]

@app.get("/", include_in_schema=False)
def docs_redirect():
    return RedirectResponse(url='/docs')

@app.post("/models", description="Create or update Prophet model.")
@app.post("/models/", include_in_schema=False)
@app.put("/models", include_in_schema=False)
@app.put("/models/", include_in_schema=False)
def upsert_model(request: CreateModelRequest):
    try:
        upsert_mod(request)
        return {"message": f"Model params for model {request.name} have been stored."}
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/models/{model}/predict", response_model=ForecastResponse, description="Asks for the future prediction of the model.")
def predict(model, request: ForecastRequest):
    try:
        forecast_df = generate_forecast(request.start_date, request.periods, model)
        response = [
            ForecastPoint(
                ds=row.ds.strftime("%Y-%m-%d %H:%M:%S"),
                yhat=round(row.yhat, 2)
            ) for row in forecast_df.itertuples()
        ]
        return {"forecast": response}
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models/{model}/retrain", description="Calls .fit() method on the new data.")
def retrain(model):
    try:
        retrain_and_save(model)
        return {"message": f"Model {model} have been retrained to fit the data in the db"}
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/models/{model}/metrics", description="Inserts new datapoint into internal database.")
def feed_measurement(model, request: MetricStoreRequest):
    try:
        insert_measurement(model, request.date, request.value)
        return {"message": "ack"}
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/models/{model}/metricsCsv", description="Inserts multiple datapoints passed as external CSV file into internal database.")
def feed_csv(model, request: MetricCsvStoreRequest):
    try:
        inserted = insert_multiple_measurements(model, request.csvUrl)
        return {"message": f"inserted {inserted} samples"}
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models", response_model=List[str], description="Lists all the available models that have been created.")
@app.get("/models/", include_in_schema=False, response_model=List[str])
def list_models():
    import traceback
    try:
        models = list_models_db()
        return models
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/models/{model}", description="Deletes the model and its data from database and from filesystem.")
def delete_model(model):
    try:
        delete(model)
        return {"message": f"Model {model} has been deleted"}
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/resetDb", description="This will reset all the database tables.")
def reset_db():
    try:
        reset_database()
        return {"message": f"Database with the metrics has been nulled"}
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models/{model}/testData", description="Feeds the database with example data.")
def feed_test_data(model,days=14, daysTrendFactor=1.1, offHoursFactor=0, jitter=.05):
    try:
        feed_db(
            model=model,
            days=days,
            days_trend_factor=daysTrendFactor,
            off_hours_factor=offHoursFactor,
            jitter=jitter
        )
        return {"message": f"Sample metrics were created in the db for model {model}"}
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/models/{model}/graph",
    description="Returns png file representing the model and its prediction.",
    responses={
        200: {
            "content": {"image/png": {}},
        }
    }
)
def graph(model, legend = "F", trend = "F", uncertainty = "T", hoursAgo: int = 0, dataHoursAgo: int = 0, freq: str = "10min", periods: int = 60):
    try:
        if hoursAgo > 0:
            prediction_start_time = (datetime.today() - timedelta(hours=hoursAgo)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            prediction_start_time = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        if dataHoursAgo > 0:
            data_start_time = (datetime.today() - timedelta(hours=dataHoursAgo)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            data_start_time = None
        image_bytes = generate_graph_bytes(
            data_start_date=data_start_time,
            prediction_start_date = prediction_start_time,
            include_legend = to_bool(legend),
            uncertainty = to_bool(uncertainty),
            trend = to_bool(trend),
            periods = periods,
            name = model,
            freq = freq,
        )
        return StreamingResponse(image_bytes, media_type="image/png")
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e) + ". Make sure you call the /metrics and /retrain endpoints first")

@app.get(
    "/models/{model}/graphComponents",
    description="Returns png file representing the model and its predictions. Predictions are decomposed into seasonalities graphs.",
    responses={
        200: {
            "content": {"image/png": {}},
        }
    }
)
def graph_components(model, uncertainty = "1", hoursAgo: int = 0, freq: str = "10min", periods: int = 60):
    try:
        if hoursAgo > 0:
            prediction_start_time = (datetime.today() - timedelta(hours=hoursAgo)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            prediction_start_time = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        image_bytes = generate_graph_bytes(
            data_start_date=None,
            prediction_start_date = prediction_start_time,
            include_legend = False,
            uncertainty = to_bool(uncertainty),
            trend=False,
            periods = periods,
            name = model,
            freq = freq,
            components = True,
        )
        return StreamingResponse(image_bytes, media_type="image/png")
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e) + ". Make sure you call the /metrics and /retrain endpoints first")

@app.get("/readiness", include_in_schema=False)
async def readiness_probe():
    global db_ready
    if db_ready:
        return {"status": "ready"}
    raise HTTPException(status_code=503, detail="Not ready yet")

@app.get("/liveness", include_in_schema=False)
async def liveness_probe():
    return {"status": "alive"}

class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("/liveness") == -1 and record.getMessage().find("/readiness") == -1

# exclude endpoints /liveness & /readiness from logs
logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

def init():
    global db_ready
    logger.info("KEDA Prophet API is starting up")
    logger.info("-------------------------------")
    logger.info(f"Version: {os.getenv("VERSION", "main")}")
    logger.info(f"Git Sha: {os.getenv("GIT_SHA", "main")}")
    init_database()
    db_ready = True

init()
