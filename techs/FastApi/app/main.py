from fastapi import FastAPI

app = FastAPI(title="FastAPI Service")

@app.get("/")
def read_root():
    return {"message": "Welcome to FastAPI Service"}