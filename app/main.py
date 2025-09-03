# main.py

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse
import logging
import os
import traceback
from pydantic import BaseModel
from typing import List
import pandas as pd
from datetime import datetime, timedelta
from .model_utils import generate_forecast, generate_graph_bytes
from .db_utils import feed_db, retrain_and_save, insert_measurement, upsert_mod, list, delete, reset_database, init_database

app = FastAPI(title="KEDA Prophet")
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

# Output schemas
class ForecastPoint(BaseModel):
    ds: str
    yhat: float

class ForecastResponse(BaseModel):
    forecast: List[ForecastPoint]

@app.get("/", include_in_schema=False)
def docs_redirect():
    return RedirectResponse(url='/docs')

@app.post("/models")
@app.post("/models/")
@app.put("/models")
@app.put("/models/")
def upsert_model(request: CreateModelRequest):
    try:
        upsert_mod(request)
        return {"message": f"Model params for model {request.name} have been stored."}
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/models/{model}/predict", response_model=ForecastResponse)
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

@app.get("/models/{model}/retrain")
def retrain(model):
    try:
        retrain_and_save(model)
        return {"message": f"Model {model} have been retrained to fit the data in the db"}
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/models/{model}/metrics")
def feed_measurement(model, request: MetricStoreRequest):
    try:
        insert_measurement(model, request.date, request.value)
        return {"message": f"Measurement was stored in the db for model {model}"}
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models/")
@app.get("/models")
def list_models():
    import traceback
    try:
        models = list()
        return {"models": [ ','.join(models) ]}
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/models/{model}")
def delete_model(model):
    try:
        delete(model)
        return {"message": f"Model {model} has been deleted"}
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/resetDb")
def reset_db():
    try:
        reset_database()
        return {"message": f"Database with the metrics has been nulled"}
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models/{model}/testData")
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
    responses={
        200: {
            "content": {"image/png": {}},
        }
    }
)
def graph(model, hoursAgo: int = 0, freq: str = "h", periods: int = 600):
    try:
        if hoursAgo > 0:
            startTime = (datetime.today() - timedelta(hours=hoursAgo)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            startTime = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        image_bytes = generate_graph_bytes(startTime, periods, model, freq)
        return StreamingResponse(image_bytes, media_type="image/png")
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e) + ". Make sure you call the /metrics and /retrain endpoints first")

@app.get("/readiness")
async def readiness_probe():
    global db_ready
    if db_ready:
        return {"status": "ready"}
    raise HTTPException(status_code=503, detail="Not ready yet")

@app.get("/liveness")
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
