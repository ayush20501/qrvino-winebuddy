import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
from sshtunnel import SSHTunnelForwarder
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

api_key = os.getenv("OPENAI_API_KEY", "")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set. Add it to your .env file.")

openai_client = OpenAI(api_key=api_key)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_WEBSEARCH_MODEL = os.getenv("OPENAI_WEBSEARCH_MODEL", "gpt-5.6")

DB_CONFIG = dict(
    host=os.getenv("SOURCE_DB_HOST"),
    port=int(os.getenv("SOURCE_DB_PORT", 3306)),
    user=os.getenv("SOURCE_DB_USER"),
    password=os.getenv("SOURCE_DB_PASSWORD"),
    database=os.getenv("SOURCE_DB_NAME"),
    connection_timeout=30,
)

tunnel = None

def get_tunnel():
    global tunnel
    if tunnel is None:
        tunnel = SSHTunnelForwarder(
            ('ssh.pythonanywhere.com', 22),
            ssh_username=os.getenv("SSH_USER"),
            ssh_password=os.getenv("SSH_PASSWORD"),
            remote_bind_address=(DB_CONFIG['host'], 3306)
        )
        tunnel.start()
    return tunnel

def create_database_connection():
    if os.getenv("USE_SSH_TUNNEL") == "True":
        t = get_tunnel()
        config = DB_CONFIG.copy()
        config['host'] = '127.0.0.1'
        config['port'] = t.local_bind_port
        return mysql.connector.connect(**config)
    return mysql.connector.connect(**DB_CONFIG)
