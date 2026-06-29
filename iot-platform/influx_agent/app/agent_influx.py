
import json
import os
import time
import traceback
from pathlib import Path

import pandas as pd
from dataframe_client import DataFrameClient
from ebcpy.utils import setup_logger
from requests.exceptions import ConnectionError
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text as sa_text
from utils import get_sql_df, get_sql_engine

SYNC_INTERVAL = os.environ.get('SYNC_INTERVAL')

class InfluxAgent:
    with open(Path(__file__).parent / 'config.json') as f:
        config = json.load(f)

    INFLUX_NAME = config['INFLUX_NAME']
    INFLUX_PORT = config['INFLUX_PORT']
    INFLUX_DB_NAME = config['INFLUX_DB_NAME']

    def __init__(self,
                 host=None,
                 port=None,
                 database_name=None,
                 sync_interval: int = None):
        if host is None:
            host = self.INFLUX_NAME

        if port is None:
            port = self.INFLUX_PORT

        if database_name is None:
            database_name = self.INFLUX_DB_NAME
        self.logger = setup_logger('influx_agent')
        self.engine = get_sql_engine()
        
        self.logger.info(f'Connecting to InfluxDB at {host}:{port} with database {database_name}')
        
        not_connected = True
        nr_not_connected = 0
        while not_connected:
            try:
                self.client = DataFrameClient(host=host,
                                            port=port,
                                            database=database_name)

                existing_databases = [i['name'] for i in self.client.get_list_database()]
                self.logger.debug('Database connected')
                not_connected = False
            except ConnectionError as con:
                nr_not_connected += 1
                if nr_not_connected >= 10:
                    self.logger.error('Couldnt get a connection 10 times. Restarting Docker Container')
                    raise con
                self.logger.warning('No connection to database')
                time.sleep(1)
            
        if database_name not in existing_databases:
            self.client.create_database(database_name)

        self.database_name = database_name

        use_def = False
        if sync_interval is None:
            use_def = True
        else:
            try:
                sync_interval = int(sync_interval)
            except ValueError:
                use_def = True

        if use_def:
            self.logger.info('Sync interval is either not specified or not an integer value.'
                             ' Defaulting to 10s')
            self.sync_interval = 10
        else:
            self.logger.info(f'Sync interval set to {sync_interval}s')
            self.sync_interval = sync_interval
            
        self.nr_read_sql_errors = 0


    def read_sql_df(self):
        df = get_sql_df(engine=self.engine)
        delete_entries = df.shape[0]
        
        df = df[~df["observedat"].isna()][["id", "entityid", "observedat", "number"]]
        df["id"] = df["id"].str.replace("https://uri.etsi.org/ngsi-ld/hasValue", "value", regex=False)
        df["id"] = df["id"].str.replace("https://uri.etsi.org/ngsi-ld/default-context/", "", regex=False)
        df.set_index("observedat", inplace=True)
        df.index = pd.to_datetime(df.index)
        
        return df, delete_entries

    def update_influx_df(self):
        try:
            sql_df, delete_entries = self.read_sql_df()
        except OperationalError as e:
            sql_df = None
            error_message = str(e)
            stack_trace = traceback.format_exc()
            self.nr_read_sql_errors += 1
            self.logger.error(f"OperationalError occurred: {error_message}\nStack Trace:\n{stack_trace}")
            if self.nr_read_sql_errors >= 10:
                self.logger.error('SQL Read Error 10 times in a row. Restarting docker')
                raise e
            

        if sql_df is None:
            self.logger.info('No connection to the TimeScale Database possible. Maybe there'
                             ' hasnt been an entity created yet?')
            return
        
        self.nr_read_sql_errors = 0
        if sql_df.shape[0] == 0:
            self.logger.debug('Nothing to update')
            return


        sql_df = sql_df.rename(columns={"id": "value_id",
                                        "entityid": "entity_id"}).dropna(how="any", axis=0)
        sql_df["entity_id"] = sql_df["entity_id"].str.split(":").str[-1]
        
        self.client.write_points(
            sql_df,
            measurement="data",
            tag_columns=["entity_id", "value_id"],
        )

        self.delete_sql_df(delete_entries=delete_entries)        
        self.logger.debug(f'Updated {sql_df.shape[0]} points')

    def delete_sql_df(self,
                      delete_entries: int):
        query = f"""
        DELETE FROM "attributes"
        WHERE "instanceid" IN (
            SELECT "instanceid"
            FROM "attributes"
            LIMIT {delete_entries}
        )
                """
        deleted = False
        nr_tries = 0
        while not deleted:
            try:
                Session = sessionmaker(bind=self.engine)
                
                with Session() as session:
                    session.execute(sa_text(query))
                    session.commit()
                    session.close()
                    deleted = True
            except Exception as e:
                nr_tries += 1
                if nr_tries >= 10:
                    self.logger.error('Couldnt delete points for 10 times in a row. Restarting Docker')
                    raise e
                self.logger.warning('Couldnt delete points from TimeScale. Probably connection error. Waiting 0.5s and trying again...')
                time.sleep(0.5)

    def run(self):
        while True:
            self.update_influx_df()
            time.sleep(self.sync_interval)
            

def main():
    influx_agent = InfluxAgent(sync_interval=SYNC_INTERVAL)
    influx_agent.run()


if __name__ == '__main__':
    main()
