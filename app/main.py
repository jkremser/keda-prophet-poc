# main.py

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse
import logging
import os
from pydantic import BaseModel
from typing import List
import pandas as pd
from .model_utils import generate_forecast, generate_graph_bytes
from .db_utils import feed_db, retrain_and_save, insert, delete, reset_database

app = FastAPI(title="KEDA Prophet")
logger = logging.getLogger('uvicorn.info')

# Input schemas
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

@app.post("/model/{model}/predict", response_model=ForecastResponse)
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
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/model/{model}/retrain")
def retrain(model):
    try:
        retrain_and_save(model)
        return {"message": "Models have been retrained to fit the data in the db"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/model/{model}")
def feed_measurement(model, request: MetricStoreRequest):
    try:
        insert(model, request.date, request.value)
        return {"message": f"Measurement was stored in the db for model {model}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/model/{model}")
def delete_model(model):
    try:
        delete(model)
        return {"message": f"Model {model} has been deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/resetDb")
def reset_db():
    try:
        reset_database()
        return {"message": f"Database with the metrics has been nulled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/model/{model}/testData")
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
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/model/{model}/graph",
    responses={
        200: {
            "content": {"image/png": {}},
        }
    }
)
def graph(model, freq: str = "h", periods: int = 600):
    try:
        image_bytes = generate_graph_bytes('2025-03-02 02:00:00', periods, model, freq)
        return StreamingResponse(image_bytes, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e) + ". Make sure you call the /feed and /retrain endpoints first")

def init():
    logger.info("KEDA Prophet API is starting up")
    logger.info(f"Version: {os.getenv("VERSION", "main")}")
    logger.info(f"Git Sha: {os.getenv("GIT_SHA", "main")}")

init()