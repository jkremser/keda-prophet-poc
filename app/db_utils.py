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
from datetime import date,timedelta
from .model_utils import train_and_save, delete_serialized_model

db_file = os.getenv("DB_FILE", "data/db.sqlite")

insert_measurement_q = ''' INSERT INTO metrics(name,timestamp,value)
              VALUES(?,?,?) '''

delete_measurements_q = ''' DELETE FROM metrics WHERE name = ? '''

list_models_q = ''' SELECT DISTINCT name FROM metrics '''
get_model_q = ''' SELECT 
                    yearly_seasonality,
                    weekly_seasonality,
                    daily_seasonality,
                    custom_seasonality_period,
                    custom_seasonality_fourier_order,
                    seasonality_mode 
                FROM models WHERE name = ? '''

upsert_model_q = '''INSERT INTO models(
                                    name,
                                    yearly_seasonality,
                                    weekly_seasonality,
                                    daily_seasonality,
                                    custom_seasonality_period,
                                    custom_seasonality_fourier_order,
                                    seasonality_mode
                                ) VALUES(?,?,?,?,?,?,?)
                    ON CONFLICT(name) DO
                    UPDATE SET
                        yearly_seasonality=excluded.yearly_seasonality,
                        weekly_seasonality=excluded.weekly_seasonality,
                        daily_seasonality=excluded.daily_seasonality,
                        custom_seasonality_period=excluded.custom_seasonality_period,
                        custom_seasonality_fourier_order=excluded.custom_seasonality_fourier_order,
                        seasonality_mode=excluded.seasonality_mode
                    WHERE name = excluded.name'''

# select_measurements = ''' SELECT * FROM metrics WHERE name = (?) '''

drop_tables_q = [ 
    """DROP TABLE IF EXISTS metrics;""",
    """DROP TABLE IF EXISTS models;""",
]

create_tables_q = [ 
    """CREATE TABLE IF NOT EXISTS metrics (
            timestamp DATE NOT NULL,
            name TEXT NOT NULL,
            value REAL NOT NULL
        );""",
    # https://github.com/facebook/prophet/blob/v1.1.7/python/prophet/forecaster.py#L33-L83
    """CREATE TABLE IF NOT EXISTS models (
            name TEXT PRIMARY KEY,
            yearly_seasonality TEXT NOT NULL DEFAULT 'False',
            weekly_seasonality TEXT NOT NULL DEFAULT 'auto',
            daily_seasonality TEXT NOT NULL DEFAULT 'auto',
            custom_seasonality_period REAL NOT NULL,
            custom_seasonality_fourier_order INT NOT NULL,
            seasonality_mode TEXT NOT NULL DEFAULT 'additive'
        );"""
]

def retrain_and_save(model_name):
    with sqlite3.connect(db_file) as con:
        cur = con.cursor()
        df = pd.read_sql_query(f"SELECT * FROM metrics WHERE name = '{model_name}' ", con)
        df = df.rename(columns={"timestamp": "ds", "value": "y"})
        params = get_model(model_name)
        train_and_save(model_name, params, df)

def reset_database():
    with sqlite3.connect(db_file) as con:
        cur = con.cursor()
        for statement in drop_tables_q + create_tables_q:
            cur.execute(statement)
        print("\n✅ Tables dropped successfully.")

def feed_db(model, days, days_trend_factor, off_hours_factor, jitter):
    with sqlite3.connect(db_file) as con:
        cur = con.cursor()

        # execute statements (DDL)
        for statement in create_tables_q:
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
    nDaysAgo = date.today() - timedelta(days)
    for day in range(1, days):
        for hour in range(0, 24):
            for min in range(0, 60, 5):
                off_hours = hour < 8
                value = day * days_trend_factor + make_jitter(value_fun(hour, min), jitter)
                value = value * (off_hours_factor if off_hours else 1)
                datum = nDaysAgo + timedelta(day)
                ts = f'{datum.year}-{datum.month:02}-{datum.day:02} {hour:02}:{min:02}:00.000'
                # print(f'day: {day}: {ts}')
                insert_sample(cur, model, ts , value)
                counter+=1
                sys.stdout.write("\r%d" % counter)
                sys.stdout.flush()
    print(" records were inserted into db.")

def insert_measurement(name, time, value):
    with sqlite3.connect(db_file) as con:
        cur = con.cursor()
        insert_sample(cur, name, time, value)

def upsert_mod(m):
    with sqlite3.connect(db_file) as con:
        cur = con.cursor()
        m_data = (
            m.name,
            m.yearly_seasonality,
            m.weekly_seasonality,
            m.daily_seasonality,
            m.custom_seasonality_period,
            m.custom_seasonality_fourier_order,
            m.seasonality_mode,
        )
        print("Model update")
        print(m_data)
        cur.execute(upsert_model_q, m_data)
        con.commit()

def get_model(name):
    with sqlite3.connect(db_file) as con:
        cur = con.cursor()
        cur.execute(get_model_q, (name,))
        rows = cur.fetchone()
        return rows

def list():
    with sqlite3.connect(db_file) as con:
        cur = con.cursor()
        cur.execute(list_models_q)
        rows = cur.fetchall()
        return map(lambda row : row[0], rows)

def delete(name):
    with sqlite3.connect(db_file) as con:
        cur = con.cursor()
        cur.execute(delete_measurements_q, (name,))
        con.commit()
    delete_serialized_model(name)

def insert_sample(cur, name, time, value):
    cur.execute(insert_measurement_q, (name, time, value))

