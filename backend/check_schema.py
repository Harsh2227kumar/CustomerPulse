import sys
import os
import asyncio

from app.db.session import engine
from sqlalchemy import inspect

async def print_schemas():
    async with engine.connect() as conn:
        def do_inspect(sync_conn):
            inspector = inspect(sync_conn)
            
            print("=== communication_history schema ===")
            try:
                for col in inspector.get_columns('communication_history'):
                    print(f"- {col['name']}: {col['type']}")
            except Exception as e:
                print(f"Error: {e}")
                
            print("\n=== escalations schema ===")
            try:
                for col in inspector.get_columns('escalations'):
                    print(f"- {col['name']}: {col['type']}")
            except Exception as e:
                print(f"Error: {e}")
                
        await conn.run_sync(do_inspect)

if __name__ == "__main__":
    asyncio.run(print_schemas())
