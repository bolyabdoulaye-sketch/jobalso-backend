from fastapi import FastAPI

app = FastAPI(title="Jobalso API")

@app.get("/")
def read_root():
    return {"status": "ok"}
