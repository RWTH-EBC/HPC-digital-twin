from datetime import datetime

import polars as pl

from it_zauber_digital_twin.coordinator.coordinator import Coordinator
from it_zauber_digital_twin.utils.fiware_utils import (
    get_entity,
)


class CoordinatorITC(Coordinator):
    def __init__(
        self,
        coordinated_agents: dict,
        name: str = "CoordinatorITC",
        stepsize: int = 120,
        timestep: int = 5,
        use_for_prediction: bool = False,
        real_time: bool = False,
    ) -> None:
        super().__init__(
            coordinated_agents=coordinated_agents,
            name=name,
            stepsize=stepsize,
            timestep=timestep,
            use_for_prediction=use_for_prediction,
            real_time=real_time,
            location="aachen"
        )
    
    def prepare_input_for_prediction(
        self,
        input_dict: dict,
        pred_df_with_weather: pl.DataFrame,
    ):
        input_df = pred_df_with_weather.with_columns(
            [
                pl.lit(value).alias(key)
                for key, value in input_dict.items()
                if key not in pred_df_with_weather.columns
            ]
        )

        for pump_is_on_key, rkw_is_on_key in [
            ("rkw01pump_is_on//value", "rkw01_is_on//value"),
            ("rkw02pump_is_on//value", "rkw02_is_on//value"),
            ("rkw03pump_is_on//value", "rkw03_is_on//value"),
        ]:
            if rkw_is_on_key not in input_df.columns:
                raise KeyError(f"Expected column {rkw_is_on_key} not found in input DataFrame.")
            
            input_df = input_df.with_columns(
                pl.col(rkw_is_on_key).alias(pump_is_on_key)
            )

        return input_df
    
    

    def _get_fmu_kwargs_for_prediction(self) -> dict:
        fmu_state = self.coordinated_agents[
            "infrastructure_agent"
        ].fmu_handler.get_state()
        current_sim_time = self.coordinated_agents[
            "infrastructure_agent"
        ].fmu_handler.current_time
        current_sim_timestamp = self.coordinated_agents[
            "infrastructure_agent"
        ].fmu_handler.current_timestamp

        return {
            "fmu_state": fmu_state,
            "stepsize": self.stepsize,
            "current_sim_time": current_sim_time,
            "current_sim_timestamp": current_sim_timestamp,
        }

    def _init_before_prediction(self, fmu_kwargs: dict):
        infrastructure_agent = self.coordinated_agents["infrastructure_agent"]
        infrastructure_agent.fmu_handler.set_state(fmu_kwargs.get("fmu_state"))
        infrastructure_agent.fmu_handler.current_time = fmu_kwargs.get(
            "current_sim_time"
        )
        infrastructure_agent.fmu_handler.current_timestamp = fmu_kwargs.get(
            "current_sim_timestamp"
        )

    def prepare_pred_df_with_weather(
        self,
        fmu_kwargs: dict,
        current_sim_timestamp: datetime,
    ):
        input_data = super().prepare_pred_df_with_weather(
            fmu_kwargs=fmu_kwargs,
            current_sim_timestamp=current_sim_timestamp,
        )
        input_data = self._add_cores_and_gpus_itc(input_data=input_data)

        return input_data

    def _add_cores_and_gpus_itc(self, input_data: pl.DataFrame):
        """
        Adds the number of allocated cores and GPUs to the input data for ITC.
        """
        cores_entity = "urn:ngsi-ld:num_allocated_cores"
        gpus_entity = "urn:ngsi-ld:num_allocated_gpus"

        core_entity = get_entity(cores_entity)
        gpu_entity = get_entity(gpus_entity)

        core_df = pl.DataFrame(
            {
                "num_allocated_cores//value": core_entity["Future_value"]["value"],
                "time": core_entity["Future_TimeInstant"]["value"],
            }
        ).with_columns(pl.col("time").str.to_datetime())

        input_data = (
            input_data.join_asof(
                core_df,
                left_on="prediction_timestamps",
                right_on="time",
                strategy="backward",
            )
            .drop("time")
            .fill_null(0)
        )

        gpu_df = pl.DataFrame(
            {
                "num_allocated_gpus//value": gpu_entity["Future_value"]["value"],
                "time": gpu_entity["Future_TimeInstant"]["value"],
            }
        ).with_columns(pl.col("time").str.to_datetime())

        input_data = (
            input_data.join_asof(
                gpu_df,
                left_on="prediction_timestamps",
                right_on="time",
                strategy="backward",
            )
            .drop("time")
            .fill_null(0)
        )

        return input_data
