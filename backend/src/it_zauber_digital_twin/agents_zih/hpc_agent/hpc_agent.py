from pathlib import Path

import polars as pl

from it_zauber_digital_twin.base_agents.base_model_agent import BaseModelAgent


class HPCAgent(BaseModelAgent):
    def __init__(
        self,
        name: str = "HPCAgent",
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

        self._init_model()

    def do_step(self, input_data: dict) -> dict:
        input_data = pl.DataFrame(input_data)
        result = self._simulate(input_data=input_data)
        self.logger.debug("Do stepped")
        if len(result) == 1:
            return result.row(0, named=True)
        return result.to_dict(as_series=False)

    def predict(self, input_data: dict | pl.DataFrame) -> pl.DataFrame:
        is_polars = isinstance(input_data, pl.DataFrame)
        if not is_polars:
            input_data = pl.DataFrame(input_data)
        result = self._simulate(input_data=input_data)
        if not is_polars:
            if len(result) == 1:
                return result.row(0, named=True)
            return result.to_dict(as_series=False)
        return result

    def _init_model(self):
        model_path = Path(__file__).parent / "model.csv"
        self.model = pl.read_csv(model_path)

    def _calc_with_models(
        self,
        input_data: pl.DataFrame,
    ) -> dict:
        # Perform the join
        result = input_data.join(self.model, on=["weekday", "hour"], how="left")

        return result.select(
            [
                "LZR.DLR.Racks-AK.HPC-Wirkleistung",
                "LZR.capella.Racks-E12.Wirkleistung",
                "LZR.alpha.Racks.HPC-Wirkleistung",
                "LZR.barnard.Racks-E12.Wirkleistung",
            ]
        )

    def _simulate(self, input_data: pl.DataFrame) -> pl.DataFrame:
        time_column = (
            "time" if "time" in input_data.columns else "prediction_timestamps"
        )
        time_expr = pl.col(time_column)
        if input_data.schema[time_column] in (pl.Utf8, pl.String):
            time_expr = time_expr.str.to_datetime()

        X = (
            input_data.with_columns(time_expr.dt.convert_time_zone("Europe/Berlin"))
            .with_columns(
                weekday=pl.col(time_column).dt.weekday().cast(pl.Int64),
                hour=pl.col(time_column).dt.hour().cast(pl.Int64),
            )
            .select(
                pl.col("weekday"),
                pl.col("hour"),
            )
        )

        y = self._calc_with_models(X)

        result = input_data.with_columns(
            pl.Series(
                "LZR.DLR.Racks-AK.HPC-Wirkleistung//value_pred",
                y["LZR.DLR.Racks-AK.HPC-Wirkleistung"],
            ),
            pl.Series(
                "LZR.capella.Racks-E12.Wirkleistung//value_pred",
                y["LZR.capella.Racks-E12.Wirkleistung"],
            ),
            pl.Series(
                "LZR.alpha.Racks.HPC-Wirkleistung//value_pred",
                y["LZR.alpha.Racks.HPC-Wirkleistung"],
            ),
            pl.Series(
                "LZR.barnard.Racks-E12.Wirkleistung//value_pred",
                y["LZR.barnard.Racks-E12.Wirkleistung"],
            ),
        )

        return result
