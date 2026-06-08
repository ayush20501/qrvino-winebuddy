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
    host='198.12.233.20',
    user='ai_qrvino_user',
    password='ai_qrvino_user',
    database='ai_qrvino'
)

def create_database_connection():
    return db_pool.get_connection()
