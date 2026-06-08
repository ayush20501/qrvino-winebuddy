import mysql.connector
from mysql.connector import pooling
import openai

openai.api_key = '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'

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
