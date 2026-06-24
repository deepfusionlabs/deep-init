from fastapi import FastAPI
from app.auth.routes import router as auth_router
from app.tasks.routes import router as tasks_router
from app.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mini Task Manager", version="1.0.0")
app.include_router(auth_router)
app.include_router(tasks_router)

@app.get("/health")
def health():
    return {"status": "ok"}
