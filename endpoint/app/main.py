import urllib.parse

from fastapi import FastAPI

app = FastAPI()


@app.post("/")
async def main(q: dict):
    result = urllib.parse.urlencode(q, doseq=True)
    return result
