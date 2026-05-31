import mysql.connector
from mysql.connector import pooling
import openai

openai.api_key = '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'

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
