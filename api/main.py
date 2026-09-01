"""FastAPI app entrypoint -- mounts the public (/tonight, /events) and ops
(candidate inbox, promote, claim intake) routers. See CLAUDE.md for the pipeline these
endpoints sit at the end of.
"""
from fastapi import FastAPI

from api.claims import router as claims_router
from api.ops_candidates import router as ops_router
from api.public import router as public_router
from worker.sentinel import init_sentry

init_sentry("api")

app = FastAPI(title="One Live API")
app.include_router(public_router)
app.include_router(ops_router)
app.include_router(claims_router)


@app.get("/healthz")
def healthz():
    return {"ok": True}
