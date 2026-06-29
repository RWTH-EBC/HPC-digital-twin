from pathlib import Path

import polars as pl
from fmpy.fmi1 import FMICallException
from tqdm import tqdm

from it_zauber_digital_twin.agents_itc.infrastructure_agent.fmu_handler import (
    FMUHandler,
)
from it_zauber_digital_twin.base_agents.base_model_agent import BaseModelAgent


class InfrastructureAgent(BaseModelAgent):
    def __init__(
        self,
        name: str = "InfrastructureAgent",
        log_level: str = "DEBUG",
    ) -> None:
        config_path = Path(__file__).parent / "config.json"
        super().__init__(name=name, config_path=config_path, log_level=log_level)

        self.get_from_modelica = list(self.config["output_translation"].values())
        self.input_translation = self.config["input_translation"]
        self.output_translation = self.config["output_translation"]
        self.inv_output_translation = {v: k for k, v in self.output_translation.items()}

        self._previous_results = (None, None)

        self._init_fmu()

    def _init_fmu(self):
        this_path = Path(__file__).parent

        fmu_path = this_path / Path(self.config["fmu_setup"]["fmu_path"])
        step_size = self.config["fmu_setup"]["step_size"]
        parameters = self.config["fmu_setup"].get("parameters", None)
        init_values = self.config["fmu_setup"].get("init_values", None)

        assert fmu_path.exists(), f"FMU path {fmu_path} does not exist"

        self.fmu_handler = FMUHandler(
            fmu_path=fmu_path,
            step_size=step_size,
            parameters=parameters,
            init_values=init_values,
        )

        self.fmu_handler.initialize()

        state_dir = Path(__file__).parent / "fmu_states"
        if self.fmu_handler.load_state_from_file(state_dir):
            self.logger.info(f"Loaded FMU state from {state_dir}")
        else:
            self.logger.info("No FMU state found, started from scratch")

    def save_state(self):
        state_dir = Path(__file__).parent / "fmu_states"
        self.fmu_handler.save_state_to_file(state_dir)
        self.logger.info(f"Saved FMU state to {state_dir}")

    def do_step(self, input_data: dict) -> dict:
        multiple_steps, _ = self._validate_input(input_data)
        input_data = self.to_si(input_data)
        if multiple_steps:
            raise ValueError("Input data must contain only one step for do_step.")

        # This has only the input values for the modelica model
        _input_dict = self._translate_input(input_data=input_data)

        result, fmu_timestamp = self._do_step(
            input_dict=_input_dict,
            input_timestamp=input_data.get("time", None),
        )

        result["fmu_timestamp"] = fmu_timestamp
        self.logger.debug("Do stepped")
        result = self._translate_output(result=result)
        self._log_memory()
        input_data.update(result)
        input_data = self.calc_pue(input_data)
        input_data = self.from_si(input_data)

        return input_data

    def _do_step(
        self,
        input_dict: dict,
        input_timestamp: str = None,
        after_do_step_timestamp: str = None,
    ) -> dict:
        try:
            res_dict, fmu_timestamp = self.fmu_handler.do_step(
                input_dict,
                input_timestamp=input_timestamp,
                after_do_step_timestamp=after_do_step_timestamp,
                read_var_list=self.get_from_modelica,
            )

            self._previous_results = (res_dict, fmu_timestamp)
        except FMICallException as e:
            self.logger.error(f"FMU call failed: {e}")
            self.logger.error("Using previous results")

            res_dict, fmu_timestamp = self._previous_results
        return res_dict, fmu_timestamp

    def calc_pue(self, res_dict: dict) -> dict:
        p_cluster = (
            res_dict["claix_2023_power//value_pred"]
            + res_dict["claix_2018_power//value_pred"]
        )

        fernkaelte_q_flow = res_dict["fernkaelte_q_flow//value_pred"]

        p_el_columns = [
            "rkw01_pump_sek_p//value_pred",
            "rkw02_pump_sek_p//value_pred",
            "rkw03_pump_sek_p//value_pred",
            "rkw01_p_el//value_pred",
            "rkw02_p_el//value_pred",
            "rkw03_p_el//value_pred",
            "kop6_cluster_pump_p//value_pred",
            "sw23_cluster_pump_p//value_pred",
            "infrastructure_pump_p//value_pred",
            "kop6_sc_cdu_p//value_pred",
            "sw23_sc_p//value_pred",
        ]

        p_el = sum([res_dict[col] for col in p_el_columns])

        e_total = 0.4 * fernkaelte_q_flow + p_el + p_cluster
        pue_pred = e_total / p_cluster

        res_dict["pue//value_pred"] = pue_pred
        return res_dict

    def calc_pue_polars(self, res_df: pl.DataFrame) -> pl.DataFrame:
        p_cluster = (
            res_df["claix_2023_power//value_pred"]
            + res_df["claix_2018_power//value_pred"]
        )

        fernkaelte_q_flow = res_df["fernkaelte_q_flow//value_pred"]

        p_el_columns = [
            "rkw01_pump_sek_p//value_pred",
            "rkw02_pump_sek_p//value_pred",
            "rkw03_pump_sek_p//value_pred",
            "rkw01_p_el//value_pred",
            "rkw02_p_el//value_pred",
            "rkw03_p_el//value_pred",
            "kop6_cluster_pump_p//value_pred",
            "sw23_cluster_pump_p//value_pred",
            "infrastructure_pump_p//value_pred",
            "kop6_sc_cdu_p//value_pred",
            "sw23_sc_p//value_pred",
        ]

        p_el = sum([res_df[col] for col in p_el_columns])

        e_total = 0.4 * fernkaelte_q_flow + p_el + p_cluster
        pue_pred = e_total / p_cluster

        return res_df.with_columns(pue_pred.alias("pue//value_pred"))

    def predict(
        self, input_data: dict | pl.DataFrame, with_progress_bar: bool = False
    ) -> pl.DataFrame:
        multiple_steps, is_polars = self._validate_input(input_data)

        if not is_polars:
            input_data = pl.DataFrame(input_data)

        if not multiple_steps:
            raise ValueError("Input data must contain multiple steps for prediction.")

        input_data = self.to_si(input_data)
        input_dict = self._translate_input(input_data=input_data)

        if "prediction_timestamps" in input_data:
            prediction_timestamps = input_data["prediction_timestamps"]

        else:
            prediction_timestamps = None

        if "time" in input_data:
            input_timestamps = input_data["time"]

        else:
            input_timestamps = None

        if prediction_timestamps is None and input_timestamps is None:
            raise ValueError(
                'Either "prediction_timestamps" or "time" must be provided in input_data.'
            )

        n_steps = (
            len(prediction_timestamps)
            if prediction_timestamps is not None
            else len(input_timestamps)
        )

        iterator = (
            range(n_steps)
            if not with_progress_bar
            else tqdm(range(n_steps), desc="Predicting steps")
        )
        res_collector = []
        for n in iterator:
            input_dict_step = {key: val[n] for key, val in input_dict.items()}
            if input_timestamps is not None:
                input_timestamp = input_timestamps[n]
            else:
                input_timestamp = None

            if prediction_timestamps is not None:
                after_do_step_timestamp = prediction_timestamps[n]
            else:
                after_do_step_timestamp = None

            res_dict, fmu_timestamp = self._do_step(
                input_dict=input_dict_step,
                input_timestamp=input_timestamp,
                after_do_step_timestamp=after_do_step_timestamp,
            )
            res_dict["fmu_timestamp"] = fmu_timestamp
            res_collector.append(res_dict)

        result = pl.DataFrame(res_collector)
        result = self._translate_output(result=result)
        result = pl.concat([input_data, result], how="horizontal")
        result = self.calc_pue_polars(result)
        result = self.from_si(result)

        self.logger.debug(f"Predicted {n_steps} steps")
        return result

    def _translate_input(self, input_data: dict | pl.DataFrame) -> dict:
        use_input_dict = {}
        if isinstance(input_data, pl.DataFrame):
            input_dict = input_data.to_dict(as_series=True)
        else:
            input_dict = input_data
        for inp in self.inputs:
            translation = self.input_translation.get(inp, inp)
            use_input_dict[translation] = input_dict[inp]

        return use_input_dict

    def _translate_output(self, result: dict | pl.DataFrame) -> dict | pl.DataFrame:
        return_dict = False
        if isinstance(result, dict):
            return_dict = True
            result = pl.DataFrame(result)

        result = result.rename(self.inv_output_translation)
        result = result.with_columns(pl.col("fernkaelte_q_flow//value_pred") * -1)

        if return_dict:
            if len(result) == 1:
                # If only one row, convert to dict
                result = result.row(0, named=True)
            else:
                result = result.to_dict(as_series=False)

        return result