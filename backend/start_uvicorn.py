import os
import uvicorn
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv("../.env")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8081)
