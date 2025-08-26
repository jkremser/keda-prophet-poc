import pandas as pd
from prophet import Prophet
import sqlite3
import pickle
import os

# Load data
con = sqlite3.connect("data/db.sqlite")
df = pd.read_sql_query("SELECT * FROM metrics", con)
# df = df.rename(columns={"timestamp": "ds", "value": "y"})

# Train model
model = Prophet()
model.fit(df)

# Save model
os.makedirs("model", exist_ok=True)
with open("model/prophet_model.pkl", "wb") as f:
    pickle.dump(model, f)

print("✅ Model trained and saved to model/prophet_model.pkl")
