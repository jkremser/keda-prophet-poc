import pandas as pd
import logging
logging.getLogger("prophet.plot").disabled = True
from prophet import Prophet
from prophet.serialize import model_to_json, model_from_json
import sqlite3
import pickle
import os
import sys
from numpy import random
from .model_utils import train_and_save, delete_serialized_model

db_file = os.getenv("DB_FILE", "data/db.sqlite")

insert_measurement = ''' INSERT INTO metrics(name,timestamp,value)
              VALUES(?,?,?) '''

delete_measurements = ''' DELETE FROM metrics WHERE name = ? '''

# select_measurements = ''' SELECT * FROM metrics WHERE name = (?) '''

drop_tables = [ 
    """DROP TABLE IF EXISTS metrics;""",
]

create_tables = [ 
    """CREATE TABLE IF NOT EXISTS metrics (
            timestamp DATE NOT NULL, 
            name TEST NOT NULL,
            value REAL NOT NULL
        );"""
]

def retrain_and_save(model):
    with sqlite3.connect(db_file) as con:
        cur = con.cursor()
        df = pd.read_sql_query(f"SELECT * FROM metrics WHERE name = '{model}' ", con)
        df = df.rename(columns={"timestamp": "ds", "value": "y"})
        train_and_save(model, df)

def reset_database():
    with sqlite3.connect(db_file) as con:
        cur = con.cursor()
        for statement in drop_tables + create_tables:
            cur.execute(statement)
        print("\n✅ Tables dropped successfully.")

def feed_db(model, days, days_trend_factor, off_hours_factor, jitter):
    with sqlite3.connect(db_file) as con:
        cur = con.cursor()

        # execute statements (DDL)
        for statement in create_tables:
            cur.execute(statement)
        print("\n✅ Tables created successfully.")
        
        value_fun = lambda hour, min: ((hour%16)*60) + min
        prepare_samples(
            cur=cur,
            days=14,
            days_trend_factor=days_trend_factor,
            off_hours_factor=off_hours_factor,
            value_fun=value_fun,
            jitter=jitter,
            model=model,
        )
        # commit the changes
        con.commit()


def make_jitter(val, jitter):
    return random.uniform(val*(1-jitter),val*(1+jitter))

def prepare_samples(cur, days, days_trend_factor, off_hours_factor, value_fun, jitter, model):
    counter=0
    for day in range(1, days):
        for hour in range(0, 24):
            for min in range(0, 60, 5):
                day_in_month = (day % 30) + 1
                month = (day // 30) + 3
                off_hours = hour < 8
                value = day * days_trend_factor + make_jitter(value_fun(hour, min), jitter)
                value = value * (off_hours_factor if off_hours else 1)
                ts = f'2025-{month:02}-{day_in_month:02} {hour:02}:{min:02}:00.000'
                # print(f'day: {day}: {ts}')
                insert_sample(cur, model, ts , value)
                counter+=1
                sys.stdout.write("\r%d" % counter)
                sys.stdout.flush()
    print(" records were inserted into db.")

def insert(name, time, value):
    with sqlite3.connect(db_file) as con:
        cur = con.cursor()
        insert_sample(cur, name, time, value)

def delete(name):
    with sqlite3.connect(db_file) as con:
        cur = con.cursor()
        cur.execute(delete_measurements, (name,))
        con.commit()
    delete_serialized_model(name)

def insert_sample(cur, name, time, value):
    cur.execute(insert_measurement, (name, time, value))

# feed_db()
