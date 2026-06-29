import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

import pandas as pd


def get_datetime_from_string(timestamp: str) -> datetime:
    if isinstance(timestamp, datetime):
        return timestamp
        
    # Replace 'Z' with '+00:00' because Python 3.10 and below 
    # needs it for fromisoformat(), Python 3.11+ handles 'Z' automatically.
    # To be safe for all modern Python versions:
    ts_to_parse = timestamp.replace("Z", "+00:00") if timestamp.endswith("Z") else timestamp
    
    dt = datetime.fromisoformat(ts_to_parse)
    
    # If the string didn't have any TZ info, force it to UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
        
    return dt


def get_string_from_datetime(dt: datetime) -> str:
    if isinstance(dt, str):
        return dt
    
    # 1. If it has a timezone, convert it to UTC. 
    # 2. If it's naive, assume it's UTC (or change .utc to your local tz if needed)
    if dt.tzinfo is not None:
        dt_utc = dt.astimezone(timezone.utc)
    else:
        dt_utc = dt.replace(tzinfo=timezone.utc)
        
    # Format to 3 decimal places for milliseconds and add Z
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def frontfill_to_interval(
    data,
    minutes: int = 2,
):
    # Drop rows where all values are NaN
    data = data.dropna(how="all")
    # Calculate aligned start time
    start = data.index[0].ceil("min")
    to_full = start.minute % minutes
    if to_full != 0:
        start += pd.Timedelta(minutes=minutes - to_full)

    # Calculate stop time
    stop = data.index[-1].ceil("min")
    new_index = pd.date_range(start=start, end=stop, freq=f"{minutes}min")

    # Use reindex instead of combine_first for better performance
    reindexed = data.reindex(data.index.union(new_index))
    reindexed.ffill(inplace=True)
    # Select only the new index rows
    result = reindexed.loc[new_index]
    # This deletes only first rows now
    result = result.dropna(how="any")

    return result


def setup_logger(
    name: str, working_directory: Union[Path, str] = None, level=logging.DEBUG
):
    """
    Setup an class or module specific logger instance
    to ensure readable output for users.

    :param str name:
        The name of the logger instance
    :param str,Path working_directory:
        The path where to store the logfile.
        If None is given, logs are not stored.
    :param str level:
        The logging level, default is DEBUG

    .. versionadded:: 0.1.7
    """
    logger = logging.getLogger(name=name)
    # Set log-level
    logger.setLevel(level=level)
    # Check if logger was already instantiated. If so, return already.
    if logger.handlers:
        return logger
    # Add handlers if not set already by logging.basicConfig and if path is specified
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%d.%m.%Y-%H:%M:%S",
    )
    if not logging.getLogger().hasHandlers():
        console = logging.StreamHandler()
        console.setFormatter(fmt=formatter)
        logger.addHandler(hdlr=console)
    if working_directory is not None:
        os.makedirs(working_directory, exist_ok=True)
        file_handler = logging.FileHandler(
            filename=working_directory.joinpath(f"{name}.log")
        )
        file_handler.setFormatter(fmt=formatter)
        logger.addHandler(hdlr=file_handler)
    return logger
