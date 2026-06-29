from pathlib import Path
import time
import polars as pl
from it_zauber_digital_twin.utils.fiware_utils import EntityValueNoneError
from it_zauber_digital_twin.base_agents.base_model_agent import BaseModelAgent
from it_zauber_digital_twin.utils.utils_zih import calc_KPIs
from it_zauber_digital_twin.utils.mqtt_utils import get_mqtt_broker
from it_zauber_digital_twin.utils.fiware_utils import get_values_from_fiware

class PreprocessingAgent(BaseModelAgent):
    def __init__(
        self,
        timestep: int = 5,
        name: str = "PreprocessingAgent",
        log_level: str = "DEBUG",
        offline_mode: bool = False,
    ) -> None:
        config_path = Path(__file__).parent / "config.json"
        super().__init__(
            name=name,
            config_path=config_path,
            log_level=log_level,
            dont_validate=offline_mode,
        )
        
        self.timestep = timestep
        self.mqtt_broker = get_mqtt_broker()
        
    def run(self):
        self.logger.info("Starting Preprocessing Agent")

        start_time = time.perf_counter()
        interval = self.timestep
        deadline = start_time + interval
        while True:
            try:
                input_data, timestamp = get_values_from_fiware(self.get_from_fiware)

                input_data_df = pl.DataFrame(input_data)

                result = self.do_step(input_data=input_data_df)
                self.logger.debug(f"Do stepped for time {timestamp}")
                to_push = result.select(self.push_to_fiware).to_dicts()[0]
                self.mqtt_broker.res_dict_to_iot_agent(to_push, timestamp, self.push_to_fiware)
            except EntityValueNoneError as e:
                self.logger.warning(f"Skipping timestep due to missing data: {e}")
                

            sleep_time = deadline - time.perf_counter()
            deadline += interval
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                self.logger.warning(
                    f"PreprocessingAgent is lagging behind by {-sleep_time:.2f} seconds"
                )
    
    def do_step(self, input_data: dict | pl.DataFrame) -> dict | pl.DataFrame:
        is_polars = isinstance(input_data, pl.DataFrame)
        if not is_polars:
            input_data = pl.DataFrame(input_data)

        input_data = self.to_si(input_data)

        PUE, ERF, ERE = calc_KPIs(input_data=input_data, attr="//value")
        result = input_data.with_columns(PUE, ERF, ERE)
        result = self.from_si(result)

        if not is_polars:
            result = result.to_dict(as_series=False)
        return result
