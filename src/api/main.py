from fastapi import FastAPI

app = FastAPI(title="First Agent API", description="AI Agent Gateway")


@app.get("/")
async def root():
    return {"status": "ok", "message": "API Gateway is running"}
