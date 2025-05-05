from fastapi import FastAPI

app = FastAPI(
    title="FastAPI Service",
    description="Documentation de l'API FastAPI",
    version="1.0.0",
    docs_url="/swagger",  # URL pour Swagger UI
    redoc_url="/redoc",   # URL pour ReDoc
)

@app.get("/")
def read_root():
    return {"message": "Welcome to FastAPI Service"}