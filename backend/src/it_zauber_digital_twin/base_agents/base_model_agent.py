import json
import os
from pathlib import Path

import polars as pl
import psutil

from it_zauber_digital_twin.utils.utils import setup_logger
from it_zauber_digital_twin.unit_conversion.unit_conversion import (
    get_unit_conversion_expressions,
)
from it_zauber_digital_twin.utils.fiware_utils import (
    validate_devices,
    validate_entities,
)


class BaseModelAgent:
    """
    Base class for model agents.
    """

    def __init__(
        self,
        name: str,
        config_path: Path,
        log_level: str = "DEBUG",
        dont_validate: bool = False,
    ) -> None:
        with open(config_path, "r") as f:
            self.config = json.load(f)
            # Initialize logger

        self.logger = setup_logger(name, level=log_level)
        inputs = []

        units = {}
        inputs = []
        get_from_fiware = []
        push_to_fiware = []

        for identifier, entity_list in self.config.items():
            if "get_from_fiware" in identifier:
                self._update_inputs_and_units(
                    entity_list,
                    [
                        inputs,
                        get_from_fiware,
                    ],  # This adds to inputs and get_from_fiware
                    units,
                )

            elif "get_from_previous_agent" in identifier:
                self._update_inputs_and_units(
                    entity_list, inputs, units
                )  # This only adds to inputs

            elif "push_to_fiware" in identifier:
                self._update_inputs_and_units(
                    entity_list,
                    [push_to_fiware],  # This only adds to push_to_fiware
                    units,
                )

        self.inputs = inputs
        self.units = units

        self.get_from_fiware = get_from_fiware
        self.push_to_fiware = push_to_fiware

        if not dont_validate:
            validate_entities(get_from_fiware, check_attributes=True)
            validate_devices(push_to_fiware)
            validate_entities(push_to_fiware, check_attributes=False)
        self.to_si_expressions, self.from_si_expressions = (
            get_unit_conversion_expressions(units)
        )
        self.config_path = config_path
        self.logger.debug(f"{name} initialized")
        self.process = psutil.Process(os.getpid())

    def to_si(self, df: pl.DataFrame | dict) -> pl.DataFrame:
        """
        Convert input DataFrame to SI units.

        Args:
            df: Input Polars DataFrame

        Returns:
            Polars DataFrame with values converted to SI units
        """
        if not self.to_si_expressions:
            return df

        is_dict = False
        if isinstance(df, dict):
            is_dict = True
            df = pl.DataFrame(df)
        
        use_expressions = {
            k: v for k, v in self.to_si_expressions.items() if k in df.columns
        }
        
        df = df.with_columns(use_expressions.values())
        
        if is_dict:
            if df.shape[0] == 1:
                df = df.to_dicts()[0]
            else:
                df = df.to_dict(as_series=False)
        return df

    def from_si(self, df: pl.DataFrame | dict) -> pl.DataFrame | dict:
        """
        Convert input DataFrame from SI units to original units.

        Args:
            df: Input Polars DataFrame

        Returns:

            Polars DataFrame with values converted from SI units to original units
        """
        if not self.from_si_expressions:
            return df
        is_dict = False
        if isinstance(df, dict):
            is_dict = True
            df = pl.DataFrame(df)
        
        use_expressions = {
            k: v for k, v in self.from_si_expressions.items() if k in df.columns
        }
        df = df.with_columns(use_expressions.values())

        if is_dict:
            if df.shape[0] == 1:
                df = df.to_dicts()[0]
            else:
                df = df.to_dict(as_series=False)
        return df
    
    def _update_inputs_and_units(
        self,
        value_unit_list: list[list[str, str]],
        input_list: list | list[list],
        unit_dict: dict,
    ):
        if isinstance(input_list, list) and all(
            isinstance(i, list) for i in input_list
        ):
            pass

        elif isinstance(input_list, list) and not any(
            isinstance(i, list) for i in input_list
        ):
            input_list = [input_list]

        else:
            raise ValueError("input_list must be a list or a list of lists")

        for value, unit in value_unit_list:
            if unit not in unit_dict:
                unit_dict[unit] = []
            unit_dict[unit].append(value)

            for lst in input_list:
                if value not in lst:
                    lst.append(value)

    def _validate_input(self, input_data: dict | pl.DataFrame) -> tuple[bool, bool]:
        if isinstance(input_data, pl.DataFrame):
            is_polars = True
            missing_inputs = set(self.inputs) - set(input_data.columns)
        else:
            is_polars = False
            missing_inputs = set(self.inputs) - set(input_data.keys())
        if missing_inputs:
            msg = "Missing inputs: \n"
            for col in missing_inputs:
                msg += f" - {col}\n"
            raise ValueError(msg)

        if isinstance(input_data, dict):
            to_check = {k: v for k, v in input_data.items() if k in self.inputs}
            iterables = [
                v
                for v in to_check.values()
                if hasattr(v, "__iter__") and not isinstance(v, str)
            ]

            if not iterables:
                return False, is_polars

            ref_len = len(iterables[0])
            assert all(
                len(v) == ref_len for v in iterables
            ), "All input arrays must have the same length when using iterables"

        return True, is_polars

    def write_config(self):
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=4)



    def _log_memory(self):
        self.logger.debug(f"Memory: {self.process.memory_info().rss / (1024 * 1024)}")
