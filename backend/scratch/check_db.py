import asyncio
from sqlalchemy import text
from database import engine

async def check():
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT * FROM regions LIMIT 1"))
            print("Table exists and is readable.")
            print(f"Row: {result.fetchone()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check())
