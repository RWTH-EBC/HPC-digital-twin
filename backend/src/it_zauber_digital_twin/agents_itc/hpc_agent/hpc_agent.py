import pickle
from pathlib import Path
from typing import cast

import joblib
import pandas as pd
import polars as pl
from it_zauber_digital_twin.base_agents.base_model_agent import BaseModelAgent
from sklearn.linear_model import LinearRegression


class HPCAgent(BaseModelAgent):
    def __init__(
        self,
        name: str = "HPCAgent",
        log_level: str = "DEBUG",
    ) -> None:
        self.config_path = Path(__file__).parent / "config.json"
        super().__init__(
            name=name,
            config_path=self.config_path,
            log_level=log_level,
        )
        self.use_quantile = self.config.get("use_quantile", "medium")
        self._load_models()
        
    def _load_models(self):
        base_model_path = Path(__file__).parent / "models"
        long_term_model_path = base_model_path / f"Model-CLAIX-2023-{self.use_quantile}.joblib"
        assert long_term_model_path.exists(), f"Model path {long_term_model_path} does not exist"
        
        short_term_model_path = base_model_path / "model-allocated.joblib"
        assert short_term_model_path.exists(), f"Model path {short_term_model_path} does not exist"
        
        spline_path = base_model_path / "interpolation-known.pickle"
        assert spline_path.exists(), f"Spline path {spline_path} does not exist"
        
        self.short_term_model = cast(LinearRegression, joblib.load(short_term_model_path))
        self.long_term_model = cast(LinearRegression, joblib.load(long_term_model_path))
        
        # Needed for the pickle load
        from . import extra  # noqa: F401
        import sys
        sys.modules['extra'] = extra
        
        with open(spline_path, "rb") as f:
            self.spline = pickle.load(f)
            
            
    def do_step(self, input_data: dict) -> dict:
        pred_df = pd.DataFrame({
            "num_cores_allocated": [input_data["num_allocated_cores//value"]],
            "num_gpus_allocated": [input_data["num_allocated_gpus//value"]],
        })
        

        short_term_predictions = self.short_term_model.predict(pred_df)
        
        res_dict = {
            "claix_2023_power//value_pred": short_term_predictions[0],
            "claix_2018_power//value_pred": 0
        }
        self.logger.debug("Do stepped")
        return {**input_data, **res_dict}
        
    def predict(self, input_data: pl.DataFrame):
        short_term_predictions = self.short_term_model.predict(
            input_data.select(
                pl.col("num_allocated_cores//value").alias("num_cores_allocated"),
                pl.col("num_allocated_gpus//value").alias("num_gpus_allocated"),
            ).to_pandas()
        )

        long_term_predictions = self.long_term_model.predict(
            input_data.with_columns(
                pl.col("prediction_timestamps").dt.convert_time_zone("Europe/Berlin"),
            )
            .select(
                weekday=pl.col("prediction_timestamps").dt.weekday().cast(pl.Int64),
                hour=pl.col("prediction_timestamps").dt.hour().cast(pl.Int64),
                minute=pl.col("prediction_timestamps").dt.minute().cast(pl.Int64),
            )
            .to_pandas()
        )

        forecast = (
            input_data.with_columns(
                short_term=short_term_predictions,
                long_term=long_term_predictions,
            )
            .with_columns(
                duration=pl.col("prediction_timestamps") - pl.col("prediction_timestamps").first(),
            )
            .with_columns(
                duration_hours=pl.col("duration").dt.total_seconds() / 60 / 60,
            )
            .with_columns(
                long_term_coefficient=pl.col("duration_hours").map_batches(self.spline),
            )
            .with_columns(
                combined=pl.col("long_term") * pl.col("long_term_coefficient")
                + pl.col("short_term") * (1 - pl.col("long_term_coefficient")),
            )
        )
        
        return input_data.with_columns(
            forecast.select("combined").to_series().alias("claix_2023_power//value_pred"),
            pl.lit(0).alias("claix_2018_power//value_pred"),
        )