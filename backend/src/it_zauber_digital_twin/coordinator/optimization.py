import polars as pl
import numpy as np
from datetime import datetime
import time
from pymoo.core.problem import ElementwiseProblem
from pymoo.core.callback import Callback

# Global variables for worker
_agent = None
_fmu_kwargs = None

def init_worker(agent_class, agent_kwargs, fmu_kwargs):
    global _agent, _fmu_kwargs
    _agent = agent_class(**agent_kwargs)
    _fmu_kwargs = fmu_kwargs

class OptimizationCallback(Callback):
    def __init__(self, opt_time, logger, variable_names, status_dict):
        super().__init__()
        self.opt_time = opt_time
        self.start_time = time.time()
        self.logger = logger
        self.best_pue = float("inf")
        self.variable_names = variable_names
        self.status_dict = status_dict

    def notify(self, algorithm):
        elapsed = time.time() - self.start_time
        
        # Get current best
        if algorithm.opt:
            best_ind = algorithm.opt[0]
            current_pue = best_ind.F[0]
            
            rewrite = False
            if current_pue < self.best_pue:
                self.best_pue = current_pue
                self.logger.info(f"New best found in Gen {algorithm.n_gen}: PUE={self.best_pue:.4f}")
                
                param_dict = dict(zip(self.variable_names, best_ind.X))
                
                for key, val in param_dict.items():
                    if "is_on" in key:
                        param_dict[key] = bool(val > 0.5)
                        
                rewrite = True
                
                with open("temp_params.json", "w") as f:
                    import json

                    json.dump(param_dict, f, indent=4)
                self.logger.debug(f"Parameters: {param_dict}")

        

        self.status_dict["current_gen"] = algorithm.n_gen
        self.status_dict["elapsed_time"] = elapsed
        self.status_dict["best_pue"] = self.best_pue
        if rewrite:
            self.status_dict["optimized_values"] = param_dict


        self.logger.info(f"Gen {algorithm.n_gen} completed. Time elapsed: {elapsed:.2f}s / {self.opt_time}s")

        if elapsed >= self.opt_time:
            self.logger.info("Optimization time limit reached. Terminating.")
            self.status_dict["progress"] = 100
            self.status_dict["remaining_time"] = 0
            algorithm.termination.force_termination = True

class ProgressParallelization:
    def __init__(self, pool, logger, status_dict):
        self.pool = pool
        self.logger = logger
        self.status_dict = status_dict
        self.start_time_global = datetime.fromisoformat(status_dict["started_at"]).timestamp()
        self.expected_end_time = datetime.fromisoformat(status_dict["expected_end_time"]).timestamp()

    def __getstate__(self):
        # Exclude the pool from being pickled
        state = self.__dict__.copy()
        del state['pool']
        return state

    def __call__(self, func, iterable):
        tasks = list(iterable)
        n_tasks = len(tasks)
        start_time = time.time()
        last_log_time = start_time
        
        results = []
        # imap returns results in order as they complete
        # We wrap tasks in tuples because our func expects a single argument (the array x)
        # but imap unpacks arguments by default if we don't be careful.
        # Actually, imap passes the item from iterable directly to func.
        # Since our items are numpy arrays (x), func(x) is called.
        # But wait, earlier we had to wrap in (x,) for apply_async because apply_async unpacks args.
        # imap does NOT unpack args. It calls func(item).
        # So if item is x, it calls func(x). This matches _evaluate(x).
        
        for i, res in enumerate(self.pool.imap(func, tasks)):
            results.append(res)
            
            current_time = time.time()
            elapsed = current_time - start_time
            elapsed_total = current_time - self.start_time_global
            
            remaining_tasks = n_tasks - (i + 1)
            done_tasks = i + 1
            
            remaining_time = (elapsed / done_tasks) * remaining_tasks if done_tasks > 0 else 0
            projected_finish_after_this_gen = start_time + elapsed + remaining_time
            if current_time - last_log_time >= 20:
                self.logger.info(f"Evaluated {i+1}/{n_tasks} ({elapsed:.2f}s)")
                last_log_time = current_time
            self.status_dict["n_evals"] += 1
            
            if projected_finish_after_this_gen > self.expected_end_time:
                
                n_evals = self.status_dict["n_evals"]
                progress = n_evals / (n_evals + remaining_tasks) * 100 if (n_evals + remaining_tasks) > 0 else 100
                
                self.status_dict["progress"] = np.floor(progress)
                self.status_dict["remaining_time"] = int(remaining_time)
                self.status_dict["expected_end_time"] = datetime.fromtimestamp(projected_finish_after_this_gen).isoformat()
            else:
                remaining_time = self.expected_end_time - current_time
                self.status_dict["remaining_time"] = int(remaining_time)
                self.status_dict["progress"] = np.floor(elapsed_total / self.status_dict["opt_time"] * 100)
                    
                
        return results

class DigitalTwinProblem(ElementwiseProblem):
    def __init__(self, 
                 fixed_input_df: pl.DataFrame,
                 variable_names: list,
                 lower_bounds: list,
                 upper_bounds: list,
                 is_zih: bool = False,
                 **kwargs):
        
        self.fixed_input_df = fixed_input_df
        self.variable_names = variable_names
        self.is_zih = is_zih

                
        super().__init__(
            n_var=len(variable_names),
            n_obj=1,
            n_ieq_constr=0,
            xl=np.array(lower_bounds),
            xu=np.array(upper_bounds),
            **kwargs
        )

    def _evaluate(self, x, out, *args, **kwargs):
        global _agent, _fmu_kwargs
        
        # Create dict of variables
        var_dict = {}
        for name, val in zip(self.variable_names, x):
            # Check if the variable name implies a boolean (e.g., "is_on")
            if "is_on" in name:
                # Convert float 0.0-1.0 to boolean
                # > 0.5 is True, <= 0.5 is False
                var_dict[name] = bool(val > 0.5)
            else:
                var_dict[name] = val
                
        # Update dataframe
        # We use with_columns to add/overwrite columns
        # Since x values are scalars for the whole horizon
        input_df = self.fixed_input_df.with_columns([
            pl.lit(var_dict[name]).alias(name) for name in self.variable_names
        ])
        
        
        if not self.is_zih:
            for pump_is_on_key, rkw_is_on_key in [
                ("rkw01pump_is_on//value", "rkw01_is_on//value"),
                ("rkw02pump_is_on//value", "rkw02_is_on//value"),
                ("rkw03pump_is_on//value", "rkw03_is_on//value"),
            ]:
                if rkw_is_on_key not in input_df.columns:
                    continue
                input_df = input_df.with_columns(
                    pl.col(rkw_is_on_key).alias(pump_is_on_key)
                )
                    
            # Reset FMU state
            _agent.fmu_handler.set_state(_fmu_kwargs.get("fmu_state"))
            _agent.fmu_handler.current_time = _fmu_kwargs.get("current_sim_time")
            _agent.fmu_handler.current_timestamp = _fmu_kwargs.get("current_sim_timestamp")
                
        # Run prediction
        try:
            results = _agent.predict(input_data=input_df)
            # Calculate PUE
            pue = results["pue//value_pred"].mean()
        except Exception:
            # Handle simulation failure
            pue = 100.0 # High penalty
            
        out["F"] = [pue]
