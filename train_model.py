import pandas as pd
from prophet import Prophet
import pickle
import os

# Load data
df = pd.read_csv("data/sensor_data.csv", parse_dates=["timestamp"])
df = df.rename(columns={"timestamp": "ds", "temperature": "y"})

# Train model
model = Prophet()
model.fit(df)

# Save model
os.makedirs("model", exist_ok=True)
with open("model/prophet_model.pkl", "wb") as f:
    pickle.dump(model, f)

print("✅ Model trained and saved to model/prophet_model.pkl")
