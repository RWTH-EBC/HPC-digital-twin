import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import polars as pl

from it_zauber_digital_twin.utils.fiware_utils import (
    validate_devices,
    validate_entities,
)
from it_zauber_digital_twin.utils.mqtt_utils import get_mqtt_broker
from it_zauber_digital_twin.utils.utils import (
    get_string_from_datetime,
    setup_logger,
)
from dotenv import load_dotenv
import os
from it_zauber_digital_twin.utils.config_loader import get_project_root

load_dotenv()

class DataPublishingAgent:
    def __init__(
        self,
        timestep: int = 5,
    ) -> None:
        """
        # TODO: Wenn daten abgelaufen sind, wird einfach letzter Wert immer weiter gespielt, nur ein Beispiel
        """
        self.logger = setup_logger("DataPublishingAgent")
        self.deployment = os.getenv("DEPLOYMENT_ENV", "itc")
        self.logger.info(f"Deployment environment: {self.deployment}")
        
        self.config = self._load_config(self.deployment)        
        self.timestep = timestep
        self.push_to_fiware = self.config["push_to_fiware"]
        self._init_online()
        self.data = self._load_data(self.deployment)
        
        

        self.logger.info("Running Live")
        self._adjust_data_to_yesterday()


        
    def _load_config(self, deployment: str) -> dict:
        if deployment == "itc":
            config_path = Path(__file__).parent / "config_itc.json"
        elif deployment == "zih":
            config_path = Path(__file__).parent / "config_zih.json"
        else:
            raise ValueError(f"Unknown deployment environment: {deployment}")
        
        with open(config_path, "r") as f:
            config = json.load(f)
            
        return config
    
    def _load_data(self, deployment: str) -> pl.DataFrame:
        if deployment == "itc":
            df_raw_path = get_project_root() / "data" / "itc-example-data.parquet"
        elif deployment == "zih":
            df_raw_path = get_project_root() / "data" / "zih-example-data.parquet"
        else:
            raise ValueError(f"Unknown deployment environment: {deployment}")
        
        df = pl.read_parquet(df_raw_path)

        rename = {i: f"{i}//value" for i in df.columns if i != "time"}
        df = df.rename(rename)
        
        
        if deployment == "zih":
            return df
        
        core_p = get_project_root() / "data" / "itc-num_allocated_cores.json"
        gpus_p = get_project_root() / "data" / "itc-num_allocated_gpus.json"
        
        with open(core_p, "r") as f:
            self.num_allocated_cores = json.load(f)
        
        with open(gpus_p, "r") as f:
            self.num_allocated_gpus = json.load(f)
            
        del self.num_allocated_cores["TimeInstant"]
        del self.num_allocated_gpus["TimeInstant"]
        
        self.n_pred_temp = len(self.num_allocated_gpus["Future_value"])
        
        return df

    def _adjust_data_to_yesterday(self):
        if not self.data.schema["time"].is_temporal():
            self.data = self.data.with_columns(
                pl.col("time").str.strptime(pl.Datetime, format="%Y-%m-%dT%H:%M:%SZ")
                .dt.replace_time_zone("UTC")
            )

        first_date = self.data.select(pl.col("time").first()).item()
        today = datetime.now(timezone.utc)
        yesterday = (today - timedelta(days=1)).day
        month = (today - timedelta(days=1)).month
        year = (today - timedelta(days=1)).year

        dt_ref = datetime(
            year=year,
            month=month,
            day=yesterday,
            hour=first_date.hour,
            minute=first_date.minute,
            second=first_date.second,
            tzinfo=timezone.utc,
        )

        offset = dt_ref - first_date

        self.data = self.data.with_columns(pl.col("time") + offset)

    def _init_online(self):
        validate_entities(to_check=self.push_to_fiware, check_attributes=True)
        validate_devices(push_to_fiware=self.push_to_fiware)

        self.broker = get_mqtt_broker()

    def _get_row_by_time(self):
        timestamp_now = datetime.now(timezone.utc)
        closest_row = (
            self.data.filter(pl.col("time") <= timestamp_now)
            .sort("time", descending=True)
            .row(0, named=True)
        )
        return closest_row
    
    def _get_gpu_and_core_dicts(self, dt: datetime) -> dict:
        future_time_instants = [
            (dt + timedelta(minutes=1 * (n+1))).isoformat() for n in range(self.n_pred_temp)
        ]
        self.num_allocated_cores["TimeInstant"] = dt.isoformat()
        self.num_allocated_gpus["TimeInstant"] = dt.isoformat()
        self.num_allocated_cores["Future_TimeInstant"] = future_time_instants
        self.num_allocated_gpus["Future_TimeInstant"] = future_time_instants
        

    def run(self) -> None:
        start_time = time.perf_counter()
        interval = self.timestep
        deadline = start_time + interval

        while True:
            row = self._get_row_by_time()
            dt = row["time"]
            timestamp_use = get_string_from_datetime(dt)
            
            self.logger.info(f"Publishing data for time {timestamp_use}")

            for var in self.push_to_fiware:
                ent_name, attr_name = var.split("//")
                self.broker.publish_to_iot_agent(
                    device_id=ent_name,
                    attribute_dict={attr_name: row[var]},
                    timestamp=timestamp_use,
                )
                time.sleep(0.05)
                
            if self.deployment == "itc":
                self._get_gpu_and_core_dicts(dt)                
                self.broker.publish_to_iot_agent(
                    device_id="num_allocated_cores",
                    attribute_dict=self.num_allocated_cores,
                    timestamp=timestamp_use,
                )
                
                self.broker.publish_to_iot_agent(
                    device_id="num_allocated_gpus",
                    attribute_dict=self.num_allocated_gpus,
                    timestamp=timestamp_use,
                )
  
            sleep_time = deadline - time.perf_counter()
            deadline += interval
            if sleep_time > 0:
                time.sleep(sleep_time)


if __name__ == "__main__":
    agent = DataPublishingAgent(timestep=10)
    agent.run()
