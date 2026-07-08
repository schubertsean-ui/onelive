from fastapi import FastAPI

from api.public import router as public_router
from api.ops_candidates import router as ops_router

app = FastAPI(title="One Live API")
app.include_router(public_router)
app.include_router(ops_router)


@app.get("/healthz")
def healthz():
    return {"ok": True}
