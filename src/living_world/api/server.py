from fastapi import FastAPI

app = FastAPI(title="Living World Simulator")


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.1"}
