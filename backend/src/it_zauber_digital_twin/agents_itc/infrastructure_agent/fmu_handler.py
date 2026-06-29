import shutil
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import fmpy
import fmpy.fmi2
import numpy as np

from it_zauber_digital_twin.utils.utils import (
    get_datetime_from_string,
    get_string_from_datetime,
)


class FMUHandler:
    """
    The fmu handler class
    """

    def __init__(
        self,
        fmu_path,
        step_size,
        tolerance=0.0001,
        init_values=None,
        parameters: dict = None,
    ):
        self.fmu_path = fmu_path
        self.step_size = step_size
        self.tolerance = tolerance

        self.model_description = None
        self.variables = {}
        self.unzipdir = None
        self.fmu = None
        self.fmu_state = None

        self.current_time = 0
        self.current_timestamp = None
        self.init_values = init_values
        self.parameters = parameters

    def initialize(self):
        self.fmu_state = None
        if self.unzipdir is not None:
            self.terminate_and_free_instance()

        # read the model description
        self.model_description = fmpy.read_model_description(self.fmu_path)

        # Collect all variables
        self.variables = {}
        for variable in self.model_description.modelVariables:
            self.variables[variable.name] = variable

        # extract the FMU
        self.unzipdir = fmpy.extract(self.fmu_path)

        # create fmu obj
        self.fmu = fmpy.fmi2.FMU2Slave(
            guid=self.model_description.guid,
            unzipDirectory=self.unzipdir,
            modelIdentifier=self.model_description.coSimulation.modelIdentifier,
            instanceName=__name__,
        )

        # instantiate fmu
        self.fmu.instantiate()
        self.fmu.setupExperiment(startTime=0, tolerance=self.tolerance)

        if self.init_values is not None:
            self.set_values(self.init_values)

        self.fmu.enterInitializationMode()
        if self.parameters is not None:
            self.set_values(self.parameters)
            self.set_values(self.init_values)
        self.fmu.exitInitializationMode()

    def simulate(
        self,
        input_dict: dict,
        input_timestamps: list,
        read_var_list: list = None,
        start_time: float = None,
        stop_time: float = None,
        output_at_input_times: bool = True,
    ):
        """
        Simulate the FMU using fmpy.simulate with input trajectories.

        Args:
            input_dict: Dictionary with variable names as keys and lists of values
            input_timestamps: List of timestamp strings
            read_var_list: List of output variable names to read
            start_time: Start time in seconds (if None, uses 0)
            stop_time: Stop time in seconds (if None, calculated from timestamps)
            output_at_input_times: If True, ensures output at input time points

        Returns:
            tuple: (results_dict, output_timestamps)
        """
        if len(input_timestamps) <= 0:
            raise ValueError("input_timestamps cannot be empty")

        # Convert timestamps to simulation time
        start_datetime = get_datetime_from_string(input_timestamps[0])
        if start_time is None:
            start_time = 0.0

        sim_times = []
        for ts in input_timestamps:
            dt = get_datetime_from_string(ts)
            sim_time = (dt - start_datetime).total_seconds() + start_time
            sim_times.append(sim_time)

        if stop_time is None:
            stop_time = sim_times[-1]

        # Prepare input signals for fmpy.simulate
        input_signals = None
        if input_dict:
            # Create structured array for input
            n_points = len(input_timestamps)
            input_vars = list(input_dict.keys())

            # Create dtype for structured array
            dtype_list = [("time", "f8")]
            for var in input_vars:
                dtype_list.append((var, "f8"))

            input_signals = np.zeros(n_points, dtype=dtype_list)
            input_signals["time"] = sim_times

            for var in input_vars:
                input_signals[var] = input_dict[var]

        # Prepare start values (combine init_values and parameters)
        start_values = {}
        if self.init_values:
            start_values.update(self.init_values)
        if self.parameters:
            start_values.update(self.parameters)

        # Prepare output variable list
        if read_var_list is None:
            read_var_list = []

        # Determine output interval to ensure we get outputs at input times
        if output_at_input_times and len(sim_times) > 1:
            # Use the minimum time difference as output interval to ensure we don't miss any input points
            time_diffs = np.diff(sim_times)
            min_time_diff = np.min(time_diffs)
            output_interval = min(min_time_diff, self.step_size)
        else:
            output_interval = self.step_size

        # Run simulation
        import time

        start = time.perf_counter()
        result = fmpy.simulate_fmu(
            filename=self.fmu_path,
            start_time=start_time,
            stop_time=stop_time,
            step_size=self.step_size,
            relative_tolerance=self.tolerance,
            input=input_signals,
            output=read_var_list,
            start_values=start_values,
            apply_default_start_values=True,
            output_interval=output_interval,
        )

        stop = time.perf_counter()
        print(f"Time to simulate: {(stop - start):2f}")

        if output_at_input_times:
            # Interpolate results to match exactly the input time points
            results_dict = {}
            for var in read_var_list:
                if var in result.dtype.names:
                    # Interpolate to get values at exact input times
                    interpolated_values = np.interp(
                        sim_times, result["time"], result[var]
                    )
                    results_dict[var] = interpolated_values.tolist()

            # Use original input timestamps as output timestamps
            output_timestamps = input_timestamps.copy()
        else:
            # Convert results back to your format (original behavior)
            results_dict = {}
            for var in read_var_list:
                if var in result.dtype.names:
                    results_dict[var] = result[var].tolist()

            # Create output timestamps
            output_times = result["time"]
            output_timestamps = []
            for t in output_times:
                dt = start_datetime + timedelta(seconds=t - start_time)
                output_timestamps.append(get_string_from_datetime(dt))

        return results_dict, output_timestamps

    def find_vars(self, find_str: str | list, exclude_str: str | list = None):
        """
        Retruns all variables with given substring
        """
        if isinstance(find_str, str):
            find_str = [find_str]

        if exclude_str is None:
            exclude_str = []

        if isinstance(exclude_str, str):
            exclude_str = [exclude_str]
        key = list(self.variables.keys())
        key_list = []
        for i in range(len(key)):
            all_included = all(j in key[i] for j in find_str)
            any_excluded = any(j in key[i] for j in exclude_str)
            if all_included and not any_excluded:
                key_list.append(key[i])

        return key_list

    def find_vars_end(self, end_str: str):
        """
        Retruns all variables ending with start_str
        """
        key = list(self.variables.keys())
        key_list = []
        for i in range(len(key)):
            if key[i].endswith(end_str):
                key_list.append(key[i])
        return key_list

    def get_value(self, var_name: str):
        """
        Get a single variable.
        """

        variable = self.variables[var_name]
        vr = [variable.valueReference]

        if variable.type == "Real":
            return self.fmu.getReal(vr)[0]
        elif variable.type in ["Integer", "Enumeration"]:
            return self.fmu.getInteger(vr)[0]
        elif variable.type == "Boolean":
            value = self.fmu.getBoolean(vr)[0]
            return value != 0
        else:
            raise Exception("Unsupported type: %s" % variable.type)

    def set_values(self, var_val_dict):
        if var_val_dict is None:
            return
        for var, val in var_val_dict.items():
            self.set_value(var, val)

    def set_value(self, var_name, value):
        """
        Set a single variable.
        var_name: str
        """
        if value is None:
            return
        variable = self.variables[var_name]
        vr = [variable.valueReference]

        if variable.type == "Real":
            self.fmu.setReal(vr, [float(value)])
        elif variable.type in ["Integer", "Enumeration"]:
            self.fmu.setInteger(vr, [int(value)])
        elif variable.type == "Boolean":
            self.fmu.setBoolean(vr, [value == 1.0 or value or value == "True"])
        else:
            raise Exception("Unsupported type: %s" % variable.type)

    def _manage_step_size(self, input_timestamp: str, after_do_step_timestamp: str):
        if input_timestamp is None and after_do_step_timestamp is None:
            return self.step_size, None

        if input_timestamp is not None and after_do_step_timestamp is not None:
            warnings.warn(
                "Both input_timestamp and after_do_step_timestamp are given. Using after_do_step_timestamp."
            )
            input_timestamp = None

        if input_timestamp is not None:
            if self.current_timestamp is None:
                self.current_timestamp = get_datetime_from_string(input_timestamp)
            dt_input = get_datetime_from_string(input_timestamp)
            after_do_step_timestamp = dt_input + timedelta(seconds=self.step_size)

        elif after_do_step_timestamp is not None:
            if self.current_timestamp is None:
                self.current_timestamp = get_datetime_from_string(
                    after_do_step_timestamp
                ) - timedelta(seconds=self.step_size)

            after_do_step_timestamp = get_datetime_from_string(after_do_step_timestamp)

        step_size = (after_do_step_timestamp - self.current_timestamp).total_seconds()
        step_size = int(round(step_size, 0))

        return step_size, after_do_step_timestamp

    def do_step(
        self,
        set_var_dict: dict,
        read_var_list: list = None,
        input_timestamp: str = None,
        after_do_step_timestamp: str = None,
    ):
        step_size, after_do_step_timestamp = self._manage_step_size(
            input_timestamp=input_timestamp,
            after_do_step_timestamp=after_do_step_timestamp,
        )

        if step_size > 0:
            self.set_values(set_var_dict)
            self.fmu.doStep(
                currentCommunicationPoint=self.current_time,
                communicationStepSize=step_size,
            )
            # augment current time step

            self.current_time += step_size
            self.current_timestamp = after_do_step_timestamp

        if read_var_list is None:
            return {}, get_string_from_datetime(self.current_timestamp)

        res_dict = self.read_variables(vrs_list=read_var_list)
        return res_dict, get_string_from_datetime(self.current_timestamp)

    def set_state(self, state):
        """
        Sets the FMU state from a serialized byte string.

        Deserializes the state, sets it in the FMU, and then frees the temporary
        state object to prevent memory leaks as per FMI standard.
        """
        fmu_state = self.fmu.deserializeFMUState(state)
        self.fmu.setFMUState(fmu_state)
        self.fmu.freeFMUState(fmu_state)

    def get_state(self):
        """
        Gets the current FMU state as a serialized byte string.

        Retrieves the state object, serializes it, and then frees the state
        object to prevent memory leaks as per FMI standard.
        """
        state = self.fmu.getFMUState()
        serialize_state = self.fmu.serializeFMUState(state)
        self.fmu.freeFMUState(state)
        return serialize_state

    def save_state_to_file(self, directory: Path):
        if not directory.exists():
            directory.mkdir(parents=True)

        # Remove old state files
        for file in directory.glob("state_*.bin"):
            file.unlink()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = directory / f"state_{timestamp}.bin"

        state = self.get_state()
        with open(filename, "wb") as f:
            f.write(state)

    def load_state_from_file(self, directory: Path) -> bool:
        if not directory.exists():
            return False

        files = list(directory.glob("state_*.bin"))
        if not files:
            return False

        # Sort by name (timestamp) and take the last one
        files.sort()
        latest_file = files[-1]

        with open(latest_file, "rb") as f:
            state = f.read()

        self.set_state(state)
        return True

    def terminate_and_free_instance(self):
        self.fmu.terminate()
        self.fmu.freeInstance()
        shutil.rmtree(self.unzipdir, ignore_errors=True)

    def read_variables(self, vrs_list: list, with_sim_time: bool = False):
        """
        Reads multiple variable values of FMU.
        vrs_list as list of strings
        Method retruns a dict with FMU variable names as key
        """
        res = {}
        # read current variable values ans store in dict
        for var in vrs_list:
            res[var] = self.get_value(var)

        if with_sim_time:
            # add current time to results
            res["SimTime"] = self.current_time

        return res

    def set_variables(self, var_dict: dict):
        """
        Sets multiple variables.
        var_dict is a dict with variable names in keys.
        """

        for key in var_dict:
            self.set_value(key, var_dict[key])
        return "Variable set!!"

    def __enter__(self):
        self.fmu.terminate()
        self.fmu.freeInstance()
