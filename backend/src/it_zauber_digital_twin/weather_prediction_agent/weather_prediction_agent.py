from datetime import datetime, timedelta, timezone
from typing import Optional, Union

import polars as pl
from wetterdienst import Settings
from wetterdienst.provider.dwd.mosmix import DwdForecastDate, DwdMosmixRequest
from wetterdienst.provider.dwd.observation import DwdObservationRequest

from it_zauber_digital_twin.utils.utils import setup_logger


class WeatherForecastAgent:
    """
    Weather forecast tool for HPC digital twin applications.

    Provides unified interface for both real forecasts (current dates) and
    historical observations as pseudo-forecasts (past dates) for backtesting.
    """

    def __init__(
        self,
        station_id_forecast: str = "10505",
        station_id_historical: str = "15000",
        location: str = "aachen",
    ):
        """
        Initialize the weather forecast tool.

        Args:
            station_location: Location name (default: "aachen")
            station_id: Specific DWD station ID (if None, will find closest to location)
        """
        self.station_id_forecast = station_id_forecast
        self.station_id_historical = station_id_historical
        self.forecast_threshold_days = (
            7  # Days back from today to switch to observations
        )
        self.logger = setup_logger(name="WeatherForecastTool", level="INFO")
        
        if location is not None and location in ["aachen", "dresden"]:
            self.logger.info("Using location: %s", location)
            
            if location == "aachen":
                self.station_id_forecast = "10505"  # Aachen-Merzbrück
                self.station_id_historical = "15000"  # Aachen
            elif location == "dresden":
                self.station_id_forecast = "10488"  # Dresden-Klotzsche
                self.station_id_historical = "01048"

        self.settings = Settings(
            ts_shape="wide",
            ts_humanize=True,
            ts_convert_units=False,
            cache_disable=True,
        )
        self.logger.info(
            f"Initialized WeatherForecastTool with station_id_forecast={self.station_id_forecast} "
            f"and station_id_historical={self.station_id_historical}"
        )

    @staticmethod
    def calculate_relative_humidity(
        df: pl.DataFrame, temp_col: str, dew_point_col: str
    ) -> pl.DataFrame:
        """
        Calculate relative humidity from temperature and dew point columns (in Kelvin).

        Args:
            df: Input dataframe
            temp_col: Column name for temperature in Kelvin
            dew_point_col: Column name for dew point in Kelvin

        Returns:
            DataFrame with added relative_humidity column
        """
        return df.with_columns(
            [
                (
                    (
                        (
                            (17.625 * (pl.col(dew_point_col)))
                            / (243.04 + (pl.col(dew_point_col)))
                        ).exp()
                        / (
                            (17.625 * (pl.col(temp_col)))
                            / (243.04 + (pl.col(temp_col)))
                        ).exp()
                    )
                    * 100
                ).alias("relative_humidity")
            ]
        )

    def _get_forecast_data(self, days: int, timestamp: datetime) -> pl.DataFrame:
        buffer_start = timestamp - timedelta(hours=1)
        buffer_stop = timestamp + timedelta(days=days, hours=1)

        actual_start = timestamp
        actual_stop = timestamp + timedelta(days=days)

        request = DwdMosmixRequest(
            parameters=[
                ("hourly", "large", "temperature_air_mean_2m"),
                ("hourly", "large", "temperature_dew_point_mean_2m"),
                ("hourly", "large", "pressure_air_site_reduced"),
            ],
            issue=DwdForecastDate.LATEST,  # automatically set if left empty
            settings=self.settings,
        )

        stations = request.filter_by_station_id(
            station_id=[self.station_id_forecast],
        )
        df = stations.values.all().df

        if df.is_empty():
            raise ValueError(
                f"No forecast data available for station {self.station_id_forecast} "
            )

        too_early = df["date"].min() - buffer_start
        too_late = buffer_stop - df["date"].max()

        if too_early.total_seconds() > 3600:
            raise ValueError(
                f"Requested forecast data starting at {buffer_start} "
                f"but available data starts at {df['date'].min()}"
            )

        if too_late.total_seconds() > 3600:
            raise ValueError(
                f"Requested forecast data ending at {buffer_stop} "
                f"but available data ends at {df['date'].max()}"
            )

        df = df.select(
            pl.col("date").alias("time"),
            (pl.col("temperature_air_mean_2m") - 273.15).alias("temperature"),
            (pl.col("temperature_dew_point_mean_2m") - 273.15).alias(
                "dew_point_temperature"
            ),
            (pl.col("pressure_air_site_reduced") / 100).alias("pressure"),
        )

        df = self.calculate_relative_humidity(
            df, temp_col="temperature", dew_point_col="dew_point_temperature"
        ).drop(["dew_point_temperature"])

        df = df.filter(
            (pl.col("time") >= buffer_start) & (pl.col("time") <= buffer_stop)
        )

        df = self.reshape_polars_df(
            source_df=df, start_time=actual_start, end_time=actual_stop, interval="2m"
        )

        return df

    @staticmethod
    def reshape_polars_df(
        source_df: pl.DataFrame,
        start_time: datetime,
        end_time: datetime,
        interval: str = "2m",
    ) -> pl.DataFrame:
        data_columns = [col for col in source_df.columns if col != "time"]
        time_range = pl.datetime_range(
            start=start_time, end=end_time, interval=interval, eager=True
        )

        existing_times = source_df.select("time").to_series()
        new_times = pl.Series("time", time_range).filter(
            ~pl.Series("time", time_range).is_in(existing_times)
        )

        target_df = pl.DataFrame({"time": new_times})

        target_df = target_df.with_columns(
            [pl.lit(None, dtype=pl.Float64).alias(col) for col in data_columns]
        )

        df = pl.concat([source_df, target_df]).sort("time")

        df = df.with_columns(
            [
                pl.col(col).interpolate(method="linear").alias(col)
                for col in data_columns
            ]
        )

        df = df.filter(pl.col("time").is_in(time_range))

        return df

    def _get_historical_data(self, days: int, timestamp: datetime) -> pl.DataFrame:
        """Get historical observation data as pseudo-forecast."""

        buffer_start = timestamp - timedelta(hours=1)
        buffer_stop = timestamp + timedelta(days=days, hours=1)

        actual_start = timestamp
        actual_stop = timestamp + timedelta(days=days)
        request = DwdObservationRequest(
            parameters=[("hourly", "moisture")],
            start_date=buffer_start,
            end_date=buffer_stop,
            settings=self.settings,
        )
        df = (
            request.filter_by_station_id(station_id=[self.station_id_historical])
            .values.all()
            .df
        )
        df = df.select(
            pl.col("date").alias("time"),
            pl.col("temperature_air_mean_2m").alias("temperature"),
            pl.col("pressure_air_site").alias("pressure"),
            pl.col("humidity").alias("relative_humidity"),
        )

        df = df.filter(
            (pl.col("time") >= buffer_start) & (pl.col("time") <= buffer_stop)
        )

        df = self.reshape_polars_df(
            source_df=df, start_time=actual_start, end_time=actual_stop, interval="2m"
        )

        return df

    def predict(
        self, days: int = 3, timestamp: Optional[Union[datetime, str]] = None
    ) -> pl.DataFrame:
        """
        Get weather prediction for the specified period.

        Args:
            days: Number of days to forecast
            timestamp: Reference timestamp. If None, uses current time.
                      If more than 7 days in the past, uses historical observations.
            interpolate: Whether to interpolate to 2-minute intervals

        Returns:
            Polars DataFrame with weather predictions
        """

        timestamp_now = datetime.now(timezone.utc).replace(microsecond=0)
        if timestamp is None:
            return self._get_forecast_data(timestamp=timestamp_now, days=days)

        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError as e:
                raise ValueError(f"Invalid timestamp format: {timestamp}") from e

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        if (timestamp_now - timestamp) < timedelta(hours=2):
            # If timestamp is within 2 hours of now, use current forecast
            self.logger.info(
                f"Using current forecast data for timestamp {timestamp.isoformat()}"
            )
            return self._get_forecast_data(timestamp=timestamp, days=days)

        elif (timestamp_now - timestamp) > timedelta(days=7):
            # If timestamp is more than 7 days in the past, use historical data
            self.logger.info(
                f"Using historical data as pseudo-forecast for {timestamp.isoformat()}"
            )
            return self._get_historical_data(timestamp=timestamp, days=days)

        else:
            raise ValueError(
                f"Timestamp {timestamp.isoformat()} must be either within 2 hours of now or more than 7 days in the past. Everything else doenst make sense."
            )
