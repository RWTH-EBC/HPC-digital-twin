import json
import time
import warnings
from datetime import datetime
from pathlib import Path

from requests.exceptions import ConnectionError

from it_zauber_digital_twin.influx_agent.dataframe_client import DataFrameClient
from it_zauber_digital_twin.utils import get_iot_config

# TODO Would be smarter to use the one in ngsi-ld-stack, to not have double implementation


class InfluxAgent:
    def __init__(self, config_path: Path = None):
        if config_path is None:
            config = get_iot_config()
        else:
            with open(config_path, "r") as f:
                config = json.load(f)

        host = config["HOST"]
        port = config["INFLUX_PORT"]
        database_name = config["INFLUX_DB_NAME"]

        not_connected = True
        nr_not_connected = 0

        while not_connected:
            try:
                self.client = DataFrameClient(
                    host=host, port=port, database=database_name
                )

                existing_databases = [
                    i["name"] for i in self.client.get_list_database()
                ]
                not_connected = False
            except ConnectionError as con:
                nr_not_connected += 1
                if nr_not_connected >= 10:
                    self.logger.error(
                        "Couldnt get a connection 10 times. Restarting Docker Container"
                    )
                    raise con
                print("No connection to database")
                time.sleep(1)

        if database_name not in existing_databases:
            self.client.create_database(database_name)

        self.database_name = database_name

    def clean_database(self):
        """
        Completely cleans the InfluxDB database by dropping and recreating it.
        Requires explicit confirmation with 'YES' to proceed.

        Args:
            confirmation (str): Must be exactly 'YES' to proceed with deletion

        Returns:
            bool: True if database was cleaned, False if operation was cancelled
        """

        inp = input(
            f"Are you sure you want to drop the database '{self.database_name}'? This operation is irreversible. Type 'YES' to confirm: "
        )

        if inp != "YES":
            print(
                "Database cleanup cancelled. To proceed, call this method with confirmation='YES'"
            )
            return False
        try:
            print(f"Dropping database: {self.database_name}")
            self.client.drop_database(self.database_name)
            print(f"Creating fresh database: {self.database_name}")
            self.client.create_database(self.database_name)
            print("Database cleaned successfully")
            return True
        except Exception as e:
            print(f"Error cleaning database: {str(e)}")
            return False

    def get_all_influx_table_names(self) -> list:
        """
        Returns all table names in the influx database
        Returns:
            list:
                list of table names
        """
        table_names = [i["name"] for i in self.client.get_list_measurements()]
        return table_names

    def get_all_entitys_from_influx(self):
        query = """
        SHOW TAG VALUES FROM "data" WITH KEY = "entity_id"
        """
        result = self.client.query(query)

        entities = [i["value"] for i in result["data"]]

        return entities

    def get_all_value_ids(self):
        query = """
        SHOW TAG VALUES FROM "data" with KEY = "value_id"
        """

        result = self.client.query(query)
        value_ids = [i["value"] for i in result["data"]]
        return value_ids

    def get_var_names_for_entity(self, entity_name: str) -> list:
        """
        Get all variable names for a given entity from the InfluxDB.

        Args:
            entity_name (str): The name of the entity to query.

        Returns:
            list: A list of variable names associated with the entity.
        """
        query = f"""
        SHOW TAG VALUES FROM "data" WITH KEY = "value_id" WHERE "entity_id" = '{entity_name}'
        """
        result = self.client.query(query)

        if not result["data"]:
            return []

        return [i["value"] for i in result["data"]]

    def delete_template_data(self, template_name: str = None):
        """
        Delete data points from the InfluxDB based on template_name.

        Args:
            template_name (str, optional): The template name to delete.
            - If None: deletes all points where value_id is not "value" or "value_pred"
            - If provided: deletes points where value_id equals "value_{template_name}"
        """
        if template_name is None:
            query = 'DELETE FROM "data" WHERE "value_id" != \'value\' AND "value_id" != \'value_pred\''
        else:
            query = f'DELETE FROM "data" WHERE "value_id" = \'value_{template_name}\''

        self.client.query(query)

    def get_latest_points_from_influx(self, entity_names: list):
        query = "SELECT * FROM data"
        where_conditions = []
        entity_names = [entity.replace("/", r"\/") for entity in entity_names]
        if len(entity_names) == 1:
            where_conditions.append(f"entity_id = '{entity_names[0]}'")
        else:
            entities_pattern = "|".join(entity_names)
            where_conditions.append(f"entity_id =~ /^({entities_pattern})$/")

        if where_conditions:
            query += " WHERE " + " AND ".join(where_conditions)

        query += " AND value_id = 'value'"
        query += " ORDER BY time DESC LIMIT 1"
        print(query)
        result = self.client.query(query)
        if len(result) == 0:
            warnings.warn(
                f"There is no data for entities {entity_names} with the specified filters"
            )
            return None

        return result["data"]

    def read_influx_table(
        self,
        entity_names: str | list = None,
        start_time: str | datetime = None,
        end_time: str | datetime = None,
        time_range: str = None,
        additional_filters: dict = None,
    ):
        """
        Enhanced version with additional filter support

        Args:
            entity_names: str, list of str, or None - entity IDs to filter for
            start_time: str or datetime - start time for the query
            end_time: str or datetime - end time for the query
            time_range: str - time range in format 'Xs' where X is seconds
            additional_filters: dict - additional tag filters, e.g., {'location': 'building_a'}

        Returns:
            DataFrame with filtered data or None if no data found
        """

        query = 'SELECT * FROM "data"'
        where_conditions = []

        # Handle entity filtering
        if entity_names is not None:
            if isinstance(entity_names, str):
                entity_list = [entity_names]
            elif isinstance(entity_names, list):
                entity_list = entity_names
            else:
                raise ValueError(
                    "entity_names must be a string, list of strings, or None"
                )

            if len(entity_list) == 1:
                where_conditions.append(f"entity_id = '{entity_list[0]}'")
            else:
                entities_pattern = "|".join(entity_list)
                where_conditions.append(f"entity_id =~ /^({entities_pattern})$/")

        # Handle additional tag filters
        if additional_filters:
            for tag_key, tag_value in additional_filters.items():
                if isinstance(tag_value, list):
                    if len(tag_value) == 1:
                        where_conditions.append(f"{tag_key} = '{tag_value[0]}'")
                    else:
                        values_pattern = "|".join(tag_value)
                        where_conditions.append(f"{tag_key} =~ /^({values_pattern})$/")
                else:
                    where_conditions.append(f"{tag_key} = '{tag_value}'")

        # Handle time filtering (same as before)
        if time_range:
            if isinstance(time_range, str) and time_range.endswith("s"):
                try:
                    seconds = int(time_range[:-1])
                    where_conditions.append(f"time > now() - {seconds}s")
                except ValueError:
                    raise ValueError(
                        "Invalid time_range format. Use 'Xs' where X is the number of seconds."
                    )
            else:
                raise ValueError(
                    "time_range must be a string in the format 'Xs' where X is the number of seconds."
                )
        elif start_time or end_time:
            if start_time:
                if isinstance(start_time, str):
                    where_conditions.append(f"time >= '{start_time}'")
                elif isinstance(start_time, datetime):
                    where_conditions.append(f"time >= '{start_time.isoformat()}'")
                else:
                    raise ValueError("start_time must be a string or datetime object")

            if end_time:
                if isinstance(end_time, str):
                    where_conditions.append(f"time <= '{end_time}'")
                elif isinstance(end_time, datetime):
                    where_conditions.append(f"time <= '{end_time.isoformat()}'")
                else:
                    raise ValueError("end_time must be a string or datetime object")

        # Add WHERE clause if we have conditions
        if where_conditions:
            query += " WHERE " + " AND ".join(where_conditions)
        print(query)
        result = self.client.query(query)
        if len(result) == 0:
            entity_str = (
                "all entities"
                if entity_names is None
                else (
                    entity_names
                    if isinstance(entity_names, str)
                    else ", ".join(entity_names)
                )
            )
            warnings.warn(
                f"There is no data for {entity_str} with the specified filters"
            )
            return None

        return result["data"]
