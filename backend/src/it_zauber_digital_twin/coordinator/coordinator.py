import json
import multiprocessing as mp
import os
import threading
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import requests

from it_zauber_digital_twin.influx_agent.influx_agent import InfluxAgent
from it_zauber_digital_twin.utils.fiware_utils import (
    get_values_from_fiware,
)
from it_zauber_digital_twin.utils.config_loader import get_iot_config
from it_zauber_digital_twin.utils.mqtt_utils import get_mqtt_broker
from it_zauber_digital_twin.utils.utils import (
    get_string_from_datetime,
    get_datetime_from_string,
    setup_logger,
)
from it_zauber_digital_twin.weather_prediction_agent.weather_prediction_agent import (
    WeatherForecastAgent,
)

from abc import ABC, abstractmethod


class Coordinator(ABC):
    def __init__(
        self,
        coordinated_agents: dict,
        name: str = "Coordinator",
        stepsize: int = 120,
        timestep: int = 5,
        use_for_prediction: bool = False,
        real_time: bool = False,
        location: str = "aachen",
    ) -> None:
        self.logger = setup_logger(name, level="DEBUG")

        self.coordinated_agents_dict = coordinated_agents
        self.run_order = list(
            sorted(
                self.coordinated_agents_dict.keys(),
                key=lambda x: self.coordinated_agents_dict[x]["position"],
            )
        )

        self.timestep = timestep
        self.stepsize = stepsize
        self.influx_agent = InfluxAgent()

        running_agents = {}
        for agent_name in self.run_order:
            agent_kwargs = self.coordinated_agents_dict[agent_name].get("kwargs", {})
            agent = self.coordinated_agents_dict[agent_name]["class"](**agent_kwargs)
            running_agents[agent_name] = agent

        self.coordinated_agents = running_agents
        self.prediction_lock_file = Path(__file__).parent / ".prediction.lock"
        self.optimization_lock_file = Path(__file__).parent / ".optimization.lock"

        if use_for_prediction:
            self.weather_prediction_agent = WeatherForecastAgent(location=location)
            return

        self.broker = get_mqtt_broker()
        self.get_from_fiware = []
        self.push_to_fiware = []
        for i in self.coordinated_agents.values():
            self.get_from_fiware.extend(i.get_from_fiware)
            self.push_to_fiware.extend(i.push_to_fiware)

        self.get_from_fiware = list(set(self.get_from_fiware))
        self.push_to_fiware = list(set(self.push_to_fiware))
        self.weather_prediction_agent = None
        self.logger.debug(f"Agents validated. Run order: {self.run_order}")

        # Set multiprocessing method for Docker compatibility
        try:
            mp.set_start_method("spawn")
        except RuntimeError:
            # Already set
            pass

        self.real_time = real_time
        if self.real_time:
            self.logger.debug("Running in real-time mode")

        self.manager = mp.Manager()
        self.optimization_status = self.manager.dict()
        self.optimization_process = None
        self._lock = threading.Lock()

        self.current_input_timestamp = None

    def _acquire_lock(self, prediction: bool = True) -> bool:
        """
        Attempt to acquire the prediction lock.

        Returns:
            True if lock was acquired, False if prediction is already running.
        """

        lock_file = (
            self.prediction_lock_file if prediction else self.optimization_lock_file
        )
        if lock_file.exists():
            # Check if lock is stale (older than 30 minutes)
            try:
                with open(lock_file, "r") as f:
                    lock_data = json.load(f)
                lock_time = datetime.fromisoformat(lock_data.get("started_at", ""))
                time_elapsed = datetime.now() - lock_time

                if time_elapsed.total_seconds() > 1800:  # 30 minutes
                    self.logger.warning(f"Removing stale lock (age: {time_elapsed})")
                    self._release_lock(prediction=prediction)
                else:
                    self.logger.warning(
                        f"{'Prediction' if prediction else 'Optimization'} already running (started at {lock_time})"
                    )
                    return False
            except Exception as e:
                self.logger.error(f"Error reading lock file: {e}. Removing lock.")
                self._release_lock(prediction=prediction)

        # Acquire lock
        try:
            lock_data = {
                "started_at": datetime.now().isoformat(),
                "pid": os.getpid(),
            }
            with open(lock_file, "w") as f:
                json.dump(lock_data, f)
            self.logger.debug(
                f"{'Prediction' if prediction else 'Optimization'} lock acquired"
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to acquire lock: {e}")
            return False

    def _release_lock(self, prediction: bool = True):
        """Release the prediction or optimization lock by removing the lock file."""
        try:
            lock_file = (
                self.prediction_lock_file if prediction else self.optimization_lock_file
            )
            if lock_file.exists():
                lock_file.unlink()
                self.logger.debug(
                    f"{'Prediction' if prediction else 'Optimization'} lock released"
                )
        except Exception as e:
            self.logger.error(f"Failed to release lock: {e}")

    def get_prediction_status(self) -> dict:
        """
        Get the current status of prediction execution.

        Returns:
            Dictionary with status information including whether a prediction is running
            and when it was started.
        """
        if not self.prediction_lock_file.exists():
            return {"is_running": False, "message": "No prediction currently running"}

        try:
            with open(self.prediction_lock_file, "r") as f:
                lock_data = json.load(f)
            lock_time = datetime.fromisoformat(lock_data.get("started_at", ""))
            time_elapsed = datetime.now() - lock_time

            if time_elapsed.total_seconds() > 1800:
                return {
                    "is_running": False,
                    "message": "Lock file is stale (will be cleaned on next prediction attempt)",
                    "started_at": lock_data.get("started_at"),
                    "elapsed_seconds": time_elapsed.total_seconds(),
                }

            return {
                "is_running": True,
                "started_at": lock_data.get("started_at"),
                "elapsed_seconds": time_elapsed.total_seconds(),
                "pid": lock_data.get("pid"),
            }
        except Exception as e:
            return {"is_running": False, "error": f"Error reading lock file: {e}"}

    def save_modelica_state(self):
        with self._lock:
            if (
                self.__class__.__name__ == "CoordinatorITC"
                and "infrastructure_agent" in self.coordinated_agents
            ):
                self.coordinated_agents["infrastructure_agent"].save_state()
                self.logger.info("Triggered save state for Infrastructure Agent")

            else:
                self.logger.warning("Modelica Agent not found, cannot save state")

    def do_step(self, input_data: dict) -> dict:
        with self._lock:
            my_res_dict = {}
            for agent_name in self.run_order:
                agent = self.coordinated_agents[agent_name]
                res_dict = agent.do_step(input_data=input_data)
                my_res_dict.update(res_dict)
                input_data.update(res_dict)

            return my_res_dict

    def push_to_influxdb(
        self,
        data: pl.DataFrame,
        template_name: str,
    ):
        # TODO Check all timestamps again for logic between timestamps and modelica timestamps
        df = data.to_pandas()

        pred_cols = [i for i in df.columns if "//value_pred" in i]
        no_pred_cols = [i.replace("//value_pred", "") for i in pred_cols]

        df = df[pred_cols + ["prediction_timestamps"]].copy()

        mapper = {i: j for i, j in zip(pred_cols, no_pred_cols)}
        df = df.rename(columns=mapper)
        df = df.melt(
            id_vars=["prediction_timestamps"], var_name="entity_id", value_name="number"
        )
        df.set_index("prediction_timestamps", inplace=True)

        # I have no idea why this is necessary. The indices look exactly the same before and after,
        # have the same type etc. But without this line, the points are not in the influx
        # afterwards.
        df.index = df.index.to_list()
        df["value_id"] = f"value_{template_name}"
        self.influx_agent.client.write_points(
            df,
            measurement="data",
            tag_columns=["entity_id", "value_id"],
        )
        self.logger.debug("Pushed to InfluxDB")

    @abstractmethod
    def _get_fmu_kwargs_for_prediction(self) -> dict:
        pass

    def optimize(self, optimizer_settings: dict):
        # Check and acquire lock
        if not self._acquire_lock(prediction=False):
            self.logger.warning("Cannot start optimization: another process is running")
            return

        try:
            input_dict, _ = get_values_from_fiware(
                get_from_fiware=self.get_from_fiware,
            )

            fmu_kwargs = self._get_fmu_kwargs_for_prediction()

            p = mp.Process(
                target=self._optimize,
                kwargs={
                    "coordinated_agents_dict": self.coordinated_agents_dict,
                    "input_dict": input_dict,
                    "optimizer_settings": optimizer_settings,
                    "fmu_kwargs": fmu_kwargs,
                    "lock_file_path": self.optimization_lock_file,
                    "status_dict": self.optimization_status,
                    "coordinator_class": self.__class__,
                },
            )
            self.optimization_process = p
            p.start()

            self.logger.debug("Started Optimization Process")
        except Exception as e:
            # Release lock if process creation fails
            self.logger.error(f"Failed to start optimization: {e}")
            self._release_lock(prediction=False)
            raise

    def stop_optimization(self):
        """
        Stop the running optimization process if it exists.
        """
        if self.optimization_process and self.optimization_process.is_alive():
            self.logger.info("Terminating optimization process...")
            self.optimization_process.terminate()
            self.optimization_process.join()
            self.optimization_process = None
            self._release_lock(prediction=False)
            self.logger.info("Optimization process terminated.")
            self.optimization_status.update(
                {
                    "is_running": False,
                }
            )
            return True
        else:
            self.optimization_status.update(
                {
                    "is_running": False,
                }
            )
            self.logger.warning("No running optimization process to stop.")
            return False

    @staticmethod
    def _optimize(
        coordinated_agents_dict: dict,
        input_dict: dict,
        optimizer_settings: dict,
        fmu_kwargs: dict,
        lock_file_path: Path,
        coordinator_class,
        status_dict: dict = None,
        actual_cluster_load_df: pl.DataFrame = None,
    ):
        try:
            from it_zauber_digital_twin.coordinator.optimization import (
                DigitalTwinProblem,
                init_worker,
                OptimizationCallback,
                ProgressParallelization,
            )
            from pymoo.optimize import minimize
            from pymoo.algorithms.soo.nonconvex.ga import GA
            from pymoo.termination import get_termination

            # Setup Coordinator
            coordinator = coordinator_class(
                coordinated_agents=coordinated_agents_dict,
                name="Optimizer",
                use_for_prediction=True,
            )

            # Update fmu_kwargs with settings
            fmu_kwargs.update(optimizer_settings["fmu_settings"])

            # Calculate n_steps
            sim_days = fmu_kwargs["sim_days"]
            stepsize = fmu_kwargs["stepsize"]
            n_steps = int((sim_days * 24 * 60 * 60) / stepsize)
            fmu_kwargs["n_steps"] = n_steps

            # Prepare base input
            base_input = coordinator.prepare_pred_df_with_weather(
                fmu_kwargs=fmu_kwargs,
                current_sim_timestamp=fmu_kwargs.get("current_sim_timestamp"),
            )

            # Prepare fixed inputs
            opt_vars = optimizer_settings["opt_variable_settings"]

            variable_names = []
            lower_bounds = []
            upper_bounds = []
            fixed_settings = {}

            bool_variables = []

            for key, value in opt_vars.items():
                if isinstance(value, list):
                    variable_names.append(key)
                    # Handle boolean bounds [True, False] or [False, True]
                    if isinstance(value[0], bool) or isinstance(value[1], bool):
                        bool_variables.append(key)
                        lower_bounds.append(0)
                        upper_bounds.append(1)
                    else:
                        lower_bounds.append(value[0])
                        upper_bounds.append(value[1])
                else:
                    fixed_settings[key] = value

            # Merge input_dict (current values) with fixed_settings
            combined_input_dict = input_dict.copy()
            combined_input_dict.update(fixed_settings)

            # Prepare static input dataframe
            static_input_df = coordinator.prepare_input_for_prediction(
                input_dict=combined_input_dict, pred_df_with_weather=base_input
            )

            if actual_cluster_load_df is not None:  # This is only for debugging
                static_input_df = static_input_df.hstack(
                    actual_cluster_load_df.select(
                        [
                            col
                            for col in actual_cluster_load_df.columns
                            if "claix" in col and col not in static_input_df.columns
                        ]
                    )
                )

            else:
                # Run HPC Agent
                hpc_agent = coordinator.coordinated_agents["hpc_agent"]
                static_input_df = hpc_agent.predict(input_data=static_input_df)

            # Setup Pool
            n_cores = optimizer_settings["optimization_settings"]["n_cores"]
            opt_time = optimizer_settings["optimization_settings"]["opt_time"]

            # Silence the agents in the workers
            agent_kwargs = coordinated_agents_dict["infrastructure_agent"].get(
                "kwargs", {}
            )
            agent_kwargs["log_level"] = "ERROR"

            pool = mp.Pool(
                n_cores,
                initializer=init_worker,
                initargs=(
                    coordinated_agents_dict["infrastructure_agent"]["class"],
                    agent_kwargs,
                    fmu_kwargs,
                ),
            )

            runner = ProgressParallelization(
                pool, coordinator.logger, status_dict=status_dict
            )

            is_zih = coordinator_class.__name__ == "CoordinatorZIH"

            problem = DigitalTwinProblem(
                fixed_input_df=static_input_df,
                variable_names=variable_names,
                lower_bounds=lower_bounds,
                upper_bounds=upper_bounds,
                elementwise_runner=runner,
                is_zih=is_zih,
            )

            algorithm = GA(pop_size=100)

            termination = get_termination("time", opt_time)
            callback = OptimizationCallback(
                opt_time=opt_time,
                logger=coordinator.logger,
                variable_names=variable_names,
                status_dict=status_dict,
            )

            res = minimize(
                problem,
                algorithm,
                termination,
                callback=callback,
                seed=1,
                verbose=False,
            )

            pool.close()
            pool.join()

            coordinator.logger.info(f"Optimization done. Best PUE: {res.F[0]}")
            coordinator.logger.info(f"Best parameters: {res.X}")

            status_dict["is_running"] = False
            status_dict["is_finished"] = True

        finally:
            try:
                if lock_file_path.exists():
                    lock_file_path.unlink()
            except Exception:
                pass

    def predict(self, scenario_dicts: list[dict]):
        # Check and acquire lock
        if not self._acquire_lock(prediction=True):
            self.logger.warning(
                "Cannot start prediction: another prediction is already running"
            )
            return

        try:
            input_dict, _ = get_values_from_fiware(
                get_from_fiware=self.get_from_fiware,
            )

            fmu_kwargs = self._get_fmu_kwargs_for_prediction()

            p = mp.Process(
                target=self._predict,
                kwargs={
                    "coordinated_agents_dict": self.coordinated_agents_dict,
                    "input_dict": input_dict,
                    "scenario_dicts": scenario_dicts,
                    "fmu_kwargs": fmu_kwargs,
                    "lock_file_path": self.prediction_lock_file,
                    "coordinator_class": self.__class__,
                },
            )
            p.start()

            self.logger.debug("Started Process")
        except Exception as e:
            # Release lock if process creation fails
            self.logger.error(f"Failed to start prediction: {e}")
            self._release_lock(prediction=True)
            raise

    @staticmethod
    def _predict(
        coordinated_agents_dict: dict,
        scenario_dicts: list[dict],
        input_dict: dict,
        fmu_kwargs: dict,
        lock_file_path: Path,
        coordinator_class,
        actual_cluster_load_df: pl.DataFrame = None,
    ):
        try:
            to_do_n_steps = {}
            for scenario_dict in scenario_dicts:
                sim_days = scenario_dict["fmu_settings"]["sim_days"]
                stepsize = scenario_dict["fmu_settings"]["stepsize"]
                n_steps = int((sim_days * 24 * 60 * 60) / stepsize)

                _identifier = (sim_days, stepsize, n_steps)
                if _identifier not in to_do_n_steps:
                    to_do_n_steps[_identifier] = []
                to_do_n_steps[_identifier].append(scenario_dict["templateName"])
                scenario_dict["fmu_settings"]["n_steps"] = n_steps

            predictor = coordinator_class(
                coordinated_agents=coordinated_agents_dict,
                name="Predictor",
                use_for_prediction=True,
            )

            collector = {}

            for scenario_dict in scenario_dicts:
                fmu_kwargs.update(scenario_dict["fmu_settings"])
                # This is just the prediction_timestamps and the weather forecast and num_cores_etc
                pred_df_with_weather = predictor.prepare_pred_df_with_weather(
                    fmu_kwargs=fmu_kwargs,
                    current_sim_timestamp=fmu_kwargs.get("current_sim_timestamp"),
                )

                if actual_cluster_load_df is not None:  # This is only for debugging
                    pred_df_with_weather = pred_df_with_weather.hstack(
                        actual_cluster_load_df.select(
                            [
                                col
                                for col in actual_cluster_load_df.columns
                                if "claix" in col
                            ]
                        )
                    )

                scenario_settings = scenario_dict["scenario_settings"]
                input_dict_scenario = input_dict.copy()
                input_dict_scenario.update(scenario_settings)

                input_data_scenario = predictor.prepare_input_for_prediction(
                    input_dict=input_dict_scenario,
                    pred_df_with_weather=pred_df_with_weather,
                )

                predictions = predictor._base_predict(
                    input_data=input_data_scenario,
                    fmu_kwargs=fmu_kwargs,
                )
                pue = np.mean(predictions["pue//value_pred"].to_numpy())
                collector[scenario_dict["templateName"]] = {
                    "predictions": predictions,
                    "pue_scenario": pue,
                }

            for (_, stepsize, n_steps), template_names in to_do_n_steps.items():
                fmu_kwargs.update(
                    {
                        "stepsize": stepsize,
                        "n_steps": n_steps,
                    }
                )

                pred_df_with_weather = predictor.prepare_pred_df_with_weather(
                    fmu_kwargs=fmu_kwargs,
                    current_sim_timestamp=fmu_kwargs.get("current_sim_timestamp"),
                )

                input_data_baseline = predictor.prepare_input_for_prediction(
                    input_dict=input_dict,
                    pred_df_with_weather=pred_df_with_weather,
                )

                baseline_predictions = predictor._base_predict(
                    input_data=input_data_baseline,
                    fmu_kwargs=fmu_kwargs,
                )

                pue_baseline = np.mean(
                    baseline_predictions["pue//value_pred"].to_numpy()
                )

                for template_name in template_names:
                    collector[template_name]["pue_baseline"] = pue_baseline

            predictor.logger.debug("Predictions done")

            predictor.send_predictions_to_dashboard(collector)

        finally:
            try:
                if lock_file_path.exists():
                    lock_file_path.unlink()
            except Exception as e:
                predictor.logger.error(f"Failed to release prediction lock: {e}")

    def send_predictions_to_dashboard(self, collector: dict):
        host = get_iot_config().get("HOST", "localhost")
        API_URL = f"http://{host}:3000/api/change_kpi_values"

        payload = {}
        for template_name, data in collector.items():
            self.influx_agent.delete_template_data(template_name=template_name)
            self.push_to_influxdb(
                data=data["predictions"],
                template_name=template_name,
            )

            payload[template_name] = {
                "pue_scenario": data["pue_scenario"],
                "pue_baseline": data["pue_baseline"],
            }

        try:
            response = requests.post(
                API_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            self.logger.debug("Sent predictions to dashboard")
        except Exception as e:
            self.logger.error(f"Error calling back to dashboard: {e}")

    def _base_predict(
        self,
        input_data: pl.DataFrame,
        fmu_kwargs: dict,
    ) -> dict:
        self._init_before_prediction(fmu_kwargs)

        for agent_name in self.run_order:
            agent = self.coordinated_agents[agent_name]
            input_data = agent.predict(input_data=input_data)

        # This holds all the predictions
        return input_data

    def _init_fmu(self, fmu_kwargs: dict):
        infrastructure_agent = self.coordinated_agents["infrastructure_agent"]
        infrastructure_agent.fmu_handler.set_state(fmu_kwargs.get("fmu_state"))
        infrastructure_agent.fmu_handler.current_time = fmu_kwargs.get(
            "current_sim_time"
        )
        infrastructure_agent.fmu_handler.current_timestamp = fmu_kwargs.get(
            "current_sim_timestamp"
        )

    @abstractmethod
    def prepare_input_for_prediction(
        self,
        input_dict: dict,
        pred_df_with_weather: pl.DataFrame,
    ):
        pass

    def prepare_pred_df_with_weather(
        self,
        fmu_kwargs: dict,
        current_sim_timestamp: datetime,
    ):
        n_steps = fmu_kwargs["n_steps"]
        step_size = fmu_kwargs["stepsize"]
        days_ahead = (n_steps * step_size // (24 * 3600)) + 1
        weather_forecast = self.weather_prediction_agent.predict(
            days=days_ahead,
            timestamp=current_sim_timestamp,
        ).slice(0, n_steps)

        prediction_timestamps = [
            current_sim_timestamp + (i + 1) * timedelta(seconds=step_size)
            for i in range(n_steps)
        ]

        input_data = weather_forecast.select(
            pl.col("temperature").alias("outside_temperature_celsius//value"),
            pl.col("pressure").alias("outside_pressure_mbar//value"),
            pl.col("relative_humidity").alias("outside_relative_humidity_pct//value"),
        ).with_columns(pl.Series("prediction_timestamps", prediction_timestamps))

        return input_data

    def run(self):
        start_time = time.perf_counter()
        interval = self.timestep
        deadline = start_time + interval

        while True:
            try:
                input_data, earliest_timestamp = get_values_from_fiware(
                    get_from_fiware=self.get_from_fiware,
                )

                if self.real_time:
                    input_data["time"] = get_string_from_datetime(datetime.now())
                else:
                    input_data["time"] = earliest_timestamp
                self.current_input_timestamp = get_datetime_from_string(
                    input_data["time"]
                )

            except Exception as e:
                error_msg = f"An error occurred: {e}."
                # Get full traceback information
                error_details = traceback.format_exc()
                self.logger.error(f"{error_msg}\nDetailed traceback:\n{error_details}")
                sleep_time = deadline - time.perf_counter()
                deadline += interval
                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    self.logger.warning("Missed deadline")

                continue
            res_dict = self.do_step(input_data=input_data)
            self.broker.res_dict_to_iot_agent(
                res_dict=res_dict,
                timestamp=earliest_timestamp,
                push_to_fiware=self.push_to_fiware,
            )

            sleep_time = deadline - time.perf_counter()
            deadline += interval
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                self.logger.warning("Missed deadline")
