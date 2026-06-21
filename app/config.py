import os
from pathlib import Path

import mysql.connector
from mysql.connector import pooling
import openai
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

openai.api_key = os.getenv("OPENAI_API_KEY", "")
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY is not set. Add it to your .env file.")

OPENAI_MODEL = "gpt-4o-mini"

db_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="winebuddy_pool",
    pool_size=10,
    host=os.getenv("SOURCE_DB_HOST"),
    port=int(os.getenv("SOURCE_DB_PORT", 3306)),
    user=os.getenv("SOURCE_DB_USER"),
    password=os.getenv("SOURCE_DB_PASSWORD"),
    database=os.getenv("SOURCE_DB_NAME"),
    ssl_disabled=False
)

def create_database_connection():
    return db_pool.get_connection()
