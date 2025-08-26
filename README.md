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
📍 http://127.0.0.1:8000/docs

### Train
```bash
curl 'http://127.0.0.1:8000/retrain'
```

### Insert Data
```bash
# todo
```

### Predict
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/predict' \
  -d '{
  "start_date": "2025-01-01 12:00:00",
  "periods": 1,
  "name": "tset"
}'
```

