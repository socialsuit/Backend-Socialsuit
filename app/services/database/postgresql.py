import asyncpg
import os
from contextlib import asynccontextmanager
import asyncio
from typing import AsyncGenerator, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get DB connection URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Retry config
MAX_RETRIES = 3
RETRY_DELAY = 1  # in seconds

# Connection pool variable
_pool: Optional[asyncpg.pool.Pool] = None

async def init_db_pool() -> None:
    """Initialize asyncpg connection pool with retries."""
    global _pool
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            _pool = await asyncpg.create_pool(
                dsn=DATABASE_URL,
                min_size=2,
                max_size=10,
                command_timeout=30,
                max_inactive_connection_lifetime=300
            )
            print("✅ PostgreSQL connection pool initialized")
            return
        except Exception as e:
            print(f"⚠️ Attempt {attempt} failed: {e}")
            if attempt == MAX_RETRIES:
                raise RuntimeError("❌ Failed to connect to PostgreSQL after multiple attempts") from e
            await asyncio.sleep(RETRY_DELAY * attempt)

@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Yield a DB connection from the pool."""
    if _pool is None:
        await init_db_pool()

    try:
        async with _pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 15000")
            yield conn
    except Exception as e:
        print(f"🚨 Error using DB connection: {e}")
        raise

async def close_db_pool() -> None:
    """Close all DB pool connections."""
    if _pool:
        await _pool.close()
        print("🔌 PostgreSQL pool closed")
