# main.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import pandas as pd
from .forecast_utils import generate_forecast
from .feed_sql import feed

app = FastAPI()

# Input schemas
class ForecastRequest(BaseModel):
    start_date: str  # e.g., "2024-04-01 00:00:00"
    periods: int     # Number of future hours to predict
    name: str        # name of the metric

class MetricStoreRequest(BaseModel):
    date: str      # e.g., "2024-04-01 00:00:00"
    value: float   # Measured value
    name: str      # name of the metric

# Output schemas
class ForecastPoint(BaseModel):
    ds: str
    yhat: float

class ForecastResponse(BaseModel):
    forecast: List[ForecastPoint]

@app.post("/predict", response_model=ForecastResponse)
def predict(request: ForecastRequest):
    try:
        forecast_df = generate_forecast(request.start_date, request.periods, request.name)
        response = [
            ForecastPoint(
                ds=row.ds.strftime("%Y-%m-%d %H:%M:%S"),
                yhat=round(row.yhat, 2)
            ) for row in forecast_df.itertuples()
        ]
        return {"forecast": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/retrain")
def fit():
    try:
        feed()
        return {"message": "Models have been retrained to fit the data in the db"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feed")
def predict(request: MetricStoreRequest):
    try:
        # todo: store to sql db
        return {"message": "Metric has been stored"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
