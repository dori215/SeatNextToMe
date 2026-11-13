from fastapi import FastAPI

app = FastAPI(title="Tandem API")


@app.get("/")
def home():
    return {"message": "Merge backend-ul!"}


@app.get("/events")
def list_events():
    return [
        {"id": 1, "title": "Concert Filarmonica", "city": "Timisoara"},
        {"id": 2, "title": "Teatrul National: Hamlet", "city": "Timisoara"},
    ]