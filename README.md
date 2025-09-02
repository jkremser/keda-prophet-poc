# KEDA Prophet

This projects runs a simple REST API to interface with the Prophet models. It makes it possible to run  multiple Prophet models simultaneously and retrain them on the new data. Internally, it uses SQLite database stored as a file with single table called `metrics`. Each row also contains the name of the metric so that models can be retrained only on their own data.

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

Navigate to: http://127.0.0.1:8000

### Create model & Insert Sample Data (only for demos)
```bash
# bootstrap model called foo w/ some sample data
curl 'http://127.0.0.1:8000/models/foo/testData'
# bootstrap model called bar w/ some sample data
curl 'http://127.0.0.1:8000/models/bar/testData?days=20&daysTrendFactor=1.2&offHoursFactor=.3&jitter=.1'
```

### Create or Update Model (the proper way)
```bash
# this creates a Prophet model with non-default settings, overriding the `weekly_seasonality` and adding one custom seasonality
hourlyInDays=$(echo "scale=4;1/24" | bc -l | awk '{printf "%.4f\n", $0}')
curl -X POST \
  http://127.0.0.1:8000/models \
  -H "Content-Type: application/json" \
  -d '{
    "name": "foo",
    "weekly_seasonality": "False",
    "custom_seasonality_period": '${hourlyInDays}',
    "custom_seasonality_fourier_order": 3
  }';
```

### Train Models to Fit the Data
```bash
curl http://127.0.0.1:8000/models/foo/retrain
curl http://127.0.0.1:8000/models/bar/retrain
```

### Visualize the Future Prediction as Graph
```bash
open 'http://127.0.0.1:8000/models/foo/graph'
open 'http://127.0.0.1:8000/models/bar/graph'
open 'http://127.0.0.1:8000/models/foo/graph?periods=1000&freq=m'
open 'http://127.0.0.1:8000/models/foo/graph?periods=800&freq=h'

# or open a shipped test model
open http://127.0.0.1:8000/models/test/graph
```

sample output of the last call:
<!-- curl http://127.0.0.1:8000/graph/test -o ./test-graph.png -->
![test-graph](./test-graph.png "Future predictions")

### Insert More Data for a Model
```bash
for i in {0..9}; do
  curl -X POST \
    http://127.0.0.1:8000/models/foo/metrics \
    -H "Content-Type: application/json" \
    -d '{
      "date": "2025-05-01 12:0'${i}':00",
      "value": 6'${i}'0
    }';
done

# retrain
curl http://127.0.0.1:8000/models/foo/retrain
```

### Predict
```bash
curl -s -X POST \
  http://127.0.0.1:8000/models/foo/predict \
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
curl -X DELETE http://127.0.0.1:8000/models/foo
```

##  How to Run on Kubernetes

```bash
# this will deploy the k8s manifest from k8s/deployment.yaml (2 PVCs, Deployment and Service)
make deploy-k8s
```

### Container images

```bash
make build-image
make build-image-multiarch
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
