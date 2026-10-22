import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import urllib.parse


pasta_atual = os.path.dirname(os.path.abspath(__file__))
pasta_raiz = os.path.dirname(pasta_atual)
caminho_env = os.path.join(pasta_raiz, '.env')


load_dotenv(caminho_env)

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

db_pass_enc = urllib.parse.quote_plus(DB_PASS) if DB_PASS else ""
DB_URL = f"postgresql://{DB_USER}:{db_pass_enc}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

date_process = (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
URL_BASE_FOCOS = 'http://service_access:9000/api/focos'
URL_BASE_EVENTOS = 'http://service_access:9000/api/access'
URL_INJECT = 'http://service_inject:9010/inject'

DELTA_TIME= timedelta(days=7)
