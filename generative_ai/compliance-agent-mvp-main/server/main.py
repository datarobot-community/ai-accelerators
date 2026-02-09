import uvicorn

# Run the app
if __name__ == "__main__":
    uvicorn.run("fastapi_app:app", host="0.0.0.0", port=8080, reload=False)
