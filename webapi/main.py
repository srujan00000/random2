from fastapi import FastAPI
from api import router
from cors_config import add_cors_middleware

app = FastAPI(title="Content Workflow (LangGraph + SSE)")
add_cors_middleware(app)
app.include_router(router)

# Optional root probe
@app.get("/")
def root():
    return {"status": "ok", "service": "content-workflow", "routes": [
        "/workflow/stream/create",
        "/workflow/stream/resume",
        "/workflow/stream/{thread_id}"
    ]}
