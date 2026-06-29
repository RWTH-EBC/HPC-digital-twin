from it_zauber_digital_twin.coordinator.coordinator import Coordinator
import polars as pl


class CoordinatorZIH(Coordinator):
    def __init__(
        self,
        coordinated_agents: dict,
        name: str = "Coordinator",
        stepsize: int = 120,
        timestep: int = 5,
        use_for_prediction: bool = False,
        real_time: bool = False,
    ) -> None:
        super().__init__(
            name=name,
            coordinated_agents=coordinated_agents,
            stepsize=stepsize,
            timestep=timestep,
            use_for_prediction=use_for_prediction,
            real_time=real_time,
            location="dresden"
        )

    def _get_fmu_kwargs_for_prediction(self) -> dict:
        return {"stepsize": self.stepsize,
                "current_sim_timestamp": self.current_input_timestamp}


    def _init_before_prediction(self, fmu_kwargs: dict):
        """
        Initialize the FMU or other model components before prediction. Not needed for ZIH
        """
        pass
    
    def prepare_input_for_prediction(
        self,
        input_dict: dict,
        pred_df_with_weather: pl.DataFrame,
    ):
        pred_df_with_weather = pred_df_with_weather.select(
            pl.col("outside_temperature_celsius//value").alias("LZR.H01.HKR02.B20//value"),
            pl.col("prediction_timestamps")
        )
        
        input_df = pred_df_with_weather.with_columns(
            [
                pl.lit(value).alias(key)
                for key, value in input_dict.items()
                if key not in pred_df_with_weather.columns
            ]
        )
        return input_df
