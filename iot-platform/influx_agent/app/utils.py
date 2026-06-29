import pandas as pd
import requests as req
from sqlalchemy import create_engine, text
from pprint import pprint
import json
import time
import requests as r
from psycopg2 import OperationalError
from pathlib import Path

with open(Path(__file__).parent / 'config.json', 'r') as f:
    config = json.load(f)
POSTGRES_IP = config['POSTGRES_IP']

def get_sql_engine():
    # Scheme: "postgresql+psycopg2://<USERNAME>:<PASSWORD>@<IP_ADDRESS>:<PORT>/<DATABASE_NAME>"
    DATABASE_URI = f"postgresql+psycopg2://orion:orion@{POSTGRES_IP}/orion_test"
    engine = create_engine(DATABASE_URI)

    return engine


def get_sql_df(engine=None):
    engine = engine if engine is not None else get_sql_engine()
    with engine.begin() as conn:
        query = text('select * from "attributes"')
        df = pd.read_sql_query(query, con=conn)

    return df