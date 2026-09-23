"""Entry point: `python -m src`. Reads PORT so the same image runs locally and on Railway."""

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
