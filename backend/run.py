#!/usr/bin/env python3
"""
Script to run the FastAPI application
"""

import os

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    env = os.getenv("ENV", "development")
    is_dev = env == "development"
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=is_dev,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
