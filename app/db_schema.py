
insert_measurement_q = ''' INSERT INTO metrics(name,timestamp,value)
              VALUES(?,?,?) '''

delete_measurements_q = ''' DELETE FROM metrics WHERE name = ? '''

list_models_q = ''' SELECT DISTINCT name FROM metrics '''
get_model_q = ''' SELECT 
                    yearly_seasonality,                   -- 0
                    weekly_seasonality,                   -- 1
                    daily_seasonality,                    -- 2
                    custom_seasonality_name,              -- 3
                    custom_seasonality_period,            -- 4
                    custom_seasonality_fourier_order,     -- 5
                    seasonality_mode,                     -- 6
                    holidays,                             -- 7
                    holidays_prior_scale,                 -- 8
                    changepoint_prior_scale,              -- 9
                    default_horizon                       -- 10
                FROM models WHERE name = ? '''

upsert_model_q = '''INSERT INTO models(
                                    name,
                                    yearly_seasonality,                    -- 0
                                    weekly_seasonality,                    -- 1
                                    daily_seasonality,                     -- 2
                                    custom_seasonality_name,               -- 3
                                    custom_seasonality_period,             -- 4
                                    custom_seasonality_fourier_order,      -- 5
                                    seasonality_mode,                      -- 6
                                    holidays,                              -- 7
                                    holidays_prior_scale,                  -- 8
                                    changepoint_prior_scale,               -- 9
                                    default_horizon                        -- 10
                                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(name) DO
                    UPDATE SET
                        yearly_seasonality=excluded.yearly_seasonality,                                 -- 0
                        weekly_seasonality=excluded.weekly_seasonality,                                 -- 1
                        daily_seasonality=excluded.daily_seasonality,                                   -- 2
                        custom_seasonality_name=excluded.custom_seasonality_name,                       -- 3
                        custom_seasonality_period=excluded.custom_seasonality_period,                   -- 4
                        custom_seasonality_fourier_order=excluded.custom_seasonality_fourier_order,     -- 5
                        seasonality_mode=excluded.seasonality_mode,                                     -- 6
                        holidays=excluded.holidays,                                                     -- 7
                        holidays_prior_scale=excluded.holidays_prior_scale,                             -- 8
                        changepoint_prior_scale=excluded.changepoint_prior_scale,                       -- 9
                        default_horizon=excluded.default_horizon,                                       -- 10
                    WHERE name = excluded.name'''

# select_measurements = ''' SELECT * FROM metrics WHERE name = (?) '''

drop_tables_q = [
    """DROP TABLE IF EXISTS metrics;""",
    """DROP INDEX IF EXISTS ux_measurement;""",
    """DROP TABLE IF EXISTS models;""",
]

create_tables_q = [
    """CREATE TABLE IF NOT EXISTS metrics (
            timestamp DATE NOT NULL,
            name TEXT NOT NULL,
            value REAL NOT NULL
        );""",
    """CREATE UNIQUE INDEX IF NOT EXISTS ux_measurement ON metrics(name,timestamp);""",
    # https://github.com/facebook/prophet/blob/v1.1.7/python/prophet/forecaster.py#L33-L83
    """CREATE TABLE IF NOT EXISTS models (
            name TEXT PRIMARY KEY,
            yearly_seasonality TEXT NOT NULL DEFAULT 'False',    -- 0
            weekly_seasonality TEXT NOT NULL DEFAULT 'auto',     -- 1
            daily_seasonality TEXT NOT NULL DEFAULT 'auto',      -- 2
            custom_seasonality_name TEXT,                        -- 3
            custom_seasonality_period REAL,                      -- 4
            custom_seasonality_fourier_order INT,                -- 5
            seasonality_mode TEXT NOT NULL DEFAULT 'additive',   -- 6
            holidays TEXT,                                       -- 7
            holidays_prior_scale REAL,                           -- 8
            changepoint_prior_scale REAL,                        -- 9
            default_horizon TEXT                                 -- 10
        );"""
]
