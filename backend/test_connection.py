"""Verify MongoDB and Gemini connectivity before starting the server."""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

mongo_ok = False
gemini_ok = False

# 1. MongoDB
try:
    from motor.motor_asyncio import AsyncIOMotorClient
    import asyncio

    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")

    async def check_mongo():
        client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
        await client.admin.command("ping")
        client.close()

    asyncio.run(check_mongo())
    print("✓ MongoDB connected")
    mongo_ok = True
except Exception as e:
    print(f"✗ MongoDB error: {e}")

# 2. Gemini
try:
    import google.generativeai as genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError("GEMINI_API_KEY is not set — add your key to .env")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    model.generate_content("ping", generation_config={"max_output_tokens": 5})
    print("✓ Gemini ready")
    gemini_ok = True
except Exception as e:
    print(f"✗ Gemini error: {e}")

if mongo_ok and gemini_ok:
    print("\nAll systems ready — run: uvicorn main:app --reload")
    sys.exit(0)
else:
    sys.exit(1)
