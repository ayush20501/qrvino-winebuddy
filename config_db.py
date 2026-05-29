
import mysql.connector
import openai
# Set OpenAI API key
openai.api_key ='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'

# Create a function to establish a database connection
def create_database_connection():
    return mysql.connector.connect(
    host="198.12.233.20",
    user="ai_qrvino_user",
    password="ai_qrvino_user",
    database="ai_qrvino"
    )