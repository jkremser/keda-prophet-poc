import pandas as pd
from prophet import Prophet
from prophet.serialize import model_to_json, model_from_json
import sqlite3
import pickle
import os

insert_measurement = ''' INSERT INTO metrics(name,timestamp,value)
              VALUES(?,?,?) '''

tables = [ 
    """CREATE TABLE IF NOT EXISTS metrics (
            timestamp DATE NOT NULL, 
            name TEST NOT NULL,
            value REAL NOT NULL
        );"""
]

# Load data
# try:
def feed():
    with sqlite3.connect("data/db.sqlite") as con:
        # create a cursor
        cursor = con.cursor()

        # execute statements
        for statement in tables:
            cursor.execute(statement)
        cursor.execute(insert_measurement, ('test', '2025-01-01 01:00:00.000', 1))
        cursor.execute(insert_measurement, ('test', '2025-01-01 02:00:00.000', 2))
        cursor.execute(insert_measurement, ('test', '2025-01-01 03:00:00.000', 3))
        cursor.execute(insert_measurement, ('test', '2025-01-01 04:00:00.000', 4))

        cursor.execute(insert_measurement, ('test', '2025-01-01 05:00:00.000', 5))
        cursor.execute(insert_measurement, ('test', '2025-01-01 06:00:00.000', 6))
        cursor.execute(insert_measurement, ('test', '2025-01-01 07:00:00.000', 7))
        cursor.execute(insert_measurement, ('test', '2025-01-01 08:00:00.000', 8))

        cursor.execute(insert_measurement, ('tset', '2025-01-01 01:00:00.000', 42))
        cursor.execute(insert_measurement, ('tset', '2025-01-01 02:00:00.000', 42))
        cursor.execute(insert_measurement, ('tset', '2025-01-01 03:00:00.000', 42))
        cursor.execute(insert_measurement, ('tset', '2025-01-01 04:00:00.000', 42))
        # cursor.execute(insert_measurement, ('2025-01-01 09:00:00.000', 9))
        # cursor.execute(insert_measurement, ('2025-01-01 10:00:00.000', 10))
        # cursor.execute(insert_measurement, ('2025-01-01 11:00:00.000', 11))
        # cursor.execute(insert_measurement, ('2025-01-01 12:00:00.000', 12))

        # cursor.execute(insert_measurement, ('2025-01-01 09:00:00.000', 1))
        # cursor.execute(insert_measurement, ('2025-01-01 10:00:00.000', 2))
        # cursor.execute(insert_measurement, ('2025-01-01 11:00:00.000', 3))
        # cursor.execute(insert_measurement, ('2025-01-01 12:00:00.000', 4))

        # cursor.execute(insert_measurement, ('2025-01-01 13:00:00.000', 1))
        # cursor.execute(insert_measurement, ('2025-01-01 14:00:00.000', 2))
        # cursor.execute(insert_measurement, ('2025-01-01 15:00:00.000', 3))
        # cursor.execute(insert_measurement, ('2025-01-01 16:00:00.000', 4))

        # cursor.execute(insert_measurement, ('2025-01-01 17:00:00.000', 1))
        # cursor.execute(insert_measurement, ('2025-01-01 18:00:00.000', 2))
        # cursor.execute(insert_measurement, ('2025-01-01 19:00:00.000', 3))
        # cursor.execute(insert_measurement, ('2025-01-01 20:00:00.000', 4))

        # cursor.execute(insert_measurement, ('2025-01-01 21:00:00.000', 1))
        # cursor.execute(insert_measurement, ('2025-01-01 22:00:00.000', 2))
        # cursor.execute(insert_measurement, ('2025-01-01 23:00:00.000', 3))


        # commit the changes
        con.commit()

        print("Tables created successfully.")

        df = pd.read_sql_query("SELECT * FROM metrics", con)
        df = df.rename(columns={"timestamp": "ds", "value": "y"})

        # Train model
        model = Prophet()
        model.fit(df)

        # Save model
        os.makedirs("model", exist_ok=True)
        with open("model/prophet.pkl", "wb") as f:
            pickle.dump(model, f)

        with open("model/prophet.json", "w") as fjson:
            fjson.write(model_to_json(model))

        print("✅ Model trained and saved to model/prophet.pkl")
        print("✅ Model trained and saved to model/prophet.json")

feed()
