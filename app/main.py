from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Delta 9 running"}

@app.get("/api/leads")
async def get_leads():
    return {
        "signals_scanned": 0,
        "buyers_found": 0,
        "leads": []
    }
