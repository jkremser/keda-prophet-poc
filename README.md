##  How to Run Locally

###  Set Up Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

## Launch the FastAPI Server

```bash
python3 -m uvicorn app.main:app --reload
```

Navigate to:
📍 http://127.0.0.1:8000


### Insert Sample Data
```bash
# bootstrap model called foo w/ some sample data
curl 'http://127.0.0.1:8000/model/foo/testData'
# bootstrap model called bar w/ some sample data
curl 'http://127.0.0.1:8000/model/bar/testData?days=20&daysTrendFactor=1.2&offHoursFactor=.3&jitter=.1'
```

### Train Models to Fit the Data
```bash
curl http://127.0.0.1:8000/model/foo/retrain
curl http://127.0.0.1:8000/model/bar/retrain
```

### Visualize the Future Prediction as Graph
```bash
open 'http://127.0.0.1:8000/model/foo/graph'
open 'http://127.0.0.1:8000/model/bar/graph'
open 'http://127.0.0.1:8000/model/foo/graph?periods=1000&freq=m'
open 'http://127.0.0.1:8000/model/foo/graph?periods=800&freq=h'

# or open a shipped test model
open http://127.0.0.1:8000/model/test/graph
```

sample output of the last call:
<!-- curl http://127.0.0.1:8000/graph/test -o ./test-graph.png -->
![test-graph](./test-graph.png "Future predictions")

### Insert More Data for a Model
```bash
for i in {0..9}; do
  curl -X POST \
    http://127.0.0.1:8000/model/foo \
    -H "Content-Type: application/json" \
    -d '{
    "date": "2025-05-01 12:0'${i}':00",
    "value": 6'${i}'0
  }';
done

# retrain
curl http://127.0.0.1:8000/retrain/foo
```

### Predict
```bash
curl -s -X POST \
  http://127.0.0.1:8000/predict/foo \
  -H "Content-Type: application/json" \
  -d '{
  "start_date": "2025-03-05 12:00:00",
  "periods": 2
}' | jq
{
  "forecast": [
    {
      "ds": "2025-03-05 12:00:00",
      "yhat": 745.58
    },
    {
      "ds": "2025-03-05 13:00:00",
      "yhat": 827.69
    }
  ]
}
```

### Reset database
```bash
# reset database
curl http://127.0.0.1:8000/resetDb
```

### Delete a Model
```bash
# delete model called foo (removes its data from DB and its serialized Prophet model from fs)
curl -X DELETE http://127.0.0.1:8000/model/foo
```

## Dev

### Inspect Database

```bash
sqlite3 data/db.sqlite 'select count(*) from metrics;'
3744
```

```bash
sqlite3 data/db.sqlite
SQLite version 3.43.2 2023-10-10 13:08:14
Enter ".help" for usage hints.
sqlite> SELECT * FROM metrics WHERE name = 'foo';
2025-03-02 00:00:00.000|foo|462.06306463961
..
```
