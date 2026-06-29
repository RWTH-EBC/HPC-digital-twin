from importlib import import_module
from pathlib import Path

import pandas as pd
import polars as pl

from it_zauber_digital_twin.base_agents.base_model_agent import BaseModelAgent
from it_zauber_digital_twin.utils.utils_zih import calc_KPIs


class InfrastructureAgent(BaseModelAgent):
    def __init__(
        self,
        name: str = "InfrastructureAgent",
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

        self.model = None
        self.prob = None
        self.op = None
        self.jl_imported = False
        
        # self.logger.debug("Initializing model. This might take a while...")
        # self._pre_do_step()

    def import_juliacall(self):
        if self.jl_imported:
            return
        
        # Import juliacall after starting the coordinator process.
        # (https://github.com/JuliaPy/PythonCall.jl/issues/628)
        self.logger.debug("Importing juliacall...")
        juliacall = import_module("juliacall")
        self.jl = juliacall.Main
        self.jl.seval("import ZIHsim")
        self.jl_imported = True
        self.logger.debug("Importing juliacall done.")
        
        
    def _pre_do_step(self):
        df = pl.read_parquet(Path(__file__).parent / "one-step-data.parquet")
        self.do_step(df)

    def do_step(self, input_data: dict | pl.DataFrame) -> dict:
        if not self.jl_imported:
            # Import here to ensure julicall is imported in the run_thread
            self.import_juliacall()
            self.logger.debug("Initializing model before first do_step. This might take a while...")
        if not isinstance(input_data, pl.DataFrame):
            input_data = pl.DataFrame(input_data)
        # print(input_data)
        # input_data.write_parquet("do-offline-with-me.parquet")
        # raise ValueError("Stopping here to check the data.")
        input_data = self.to_si(input_data)
        result = self._simulate(input_data=input_data, hp_predict=False)
        result = self.from_si(result)
        self.logger.debug("Do stepped")
        
        if len(result) == 1:
            return result.row(0, named=True)
        
        return result.to_dict(as_series=False)

    def predict(self, input_data: dict | pl.DataFrame) -> pl.DataFrame:
        if not self.jl_imported:
            # Import here to ensure julicall is imported in the run_thread
            self.import_juliacall()
            self.logger.debug("Initializing model before predict. This might take a while...")
        is_polars = isinstance(input_data, pl.DataFrame)
        if not is_polars:
            input_data = pl.DataFrame(input_data)
        input_data = self.to_si(input_data)
        result = self._simulate(input_data=input_data, hp_predict=True)
        result = self.from_si(result)
        if not is_polars:
            if len(result) == 1:
                return result.row(0, named=True)
            
            return result.to_dict(as_series=False)
        return result

    def _init_model(self, df: pd.DataFrame) -> None:
        model, prob, op = self.jl.ZIHsim.init_model(df)
        self.model = model
        self.prob = prob
        self.op = op

    def _simulate(self, input_data: pl.DataFrame, hp_predict: bool) -> pl.DataFrame:
        df = input_data.rename({col: col.split("//")[0] for col in self.inputs})
        
        time_column = (
            "time" if "time" in input_data.columns else "prediction_timestamps"
        )
        
        if isinstance(df[time_column].dtype, pl.String):
            df = df.with_columns(df[time_column].str.to_datetime())
        t = ((df[time_column] - df[time_column][0]).dt.total_seconds()).alias("t")
        df = df.with_columns(t)
        if time_column != "t":
            # necessary because otherwise julia interpolation doesnt work
            df = df.drop(time_column)
        df = self.jl.ZIHsim.DataFrame(df.to_pandas())

        if self.model is None:
            self._init_model(df)

        model, prob, sol = self.jl.ZIHsim.simulate(
            self.model, self.prob, df, hp_predict=hp_predict
        )
        self.model = model
        self.prob = prob

        zeros = pl.zeros(input_data.height, eager=True)
        result = input_data.with_columns(
            # pumps
            ## KKR01
            pl.Series("LZR.E64.ABG10.B83.W//value_pred", sol(sol.t, idxs=model.kkr01.P_pump)),
            pl.Series("LZR.E69.ABG03.B83.W//value_pred", zeros),
            ## KKR02
            pl.Series("LZR.E64.ABG11.B83.W//value_pred", sol(sol.t, idxs=model.kkr02.P_pump)),
            pl.Series("LZR.E69.ABG01.B83.W//value_pred", zeros),
            ## KKR03
            pl.Series("LZR.E64.ABG12.B83.W//value_pred", sol(sol.t, idxs=model.kkr03.P_pump)),
            pl.Series("LZR.E69.ABG02.B83.W//value_pred", zeros),
            ## KKR04
            pl.Series("LZR.E64.ABG13.B83.W//value_pred", sol(sol.t, idxs=model.kkr04.P_pump)),
            pl.Series("LZR.E69.ABG04.B83.W//value_pred", zeros),
            ## H01.WUE
            pl.Series("LZR.E74.EIN01.B83.W//value_pred", sol(sol.t, idxs=model.h01.P_pump_wue)),
            ## H01.HKR01/02/ABG01
            pl.Series("LZR.E72.EIN01.B83.W//value_pred", sol(sol.t, idxs=model.h01.P_pump_hkr)),
            ## K02
            pl.Series("LZR.E60.ABG10.B83.W//value_pred", sol(sol.t, idxs=model.k02.P_pump)),
            pl.Series("LZR.E60.ABG11.B83.W//value_pred", zeros),
            pl.Series("LZR.E60.ABG12.B83.W//value_pred", zeros),
            pl.Series("LZR.E60.ABG07.B83.W//value_pred", zeros),
            pl.Series("LZR.E60.ABG08.B83.W//value_pred", zeros),
            pl.Series("LZR.E60.ABG09.B83.W//value_pred", zeros),
            # RKW
            pl.Series("LZR.E12.ABG02.B83.W//value_pred", sol(sol.t, idxs=model.k02.P_rkw)),
            pl.Series("LZR.E15.ABG03.B83.W//value_pred", zeros),
            # Heat pumps
            pl.Series("WPG.H01.WPA01.B83//value_pred", sol(sol.t, idxs=model.wpg.wpa.P)),
            pl.Series("WPG.H01.WPA02.B83//value_pred", zeros),
            pl.Series("WPG.H01.WPA03.B83//value_pred", zeros),
            # Heating
            ## LZR
            pl.Series("LZR.H01.HKR01.B29.LN//value_pred", sol(sol.t, idxs=model.h01.hkr01.Q̇)),
            pl.Series("LZR.H01.HKR02.B29.LN//value_pred", sol(sol.t, idxs=model.h01.hkr02.Q̇)),
            ## KRO
            pl.Series("LZR.H01.ABG01.B29.MB//value_pred", sol(sol.t, idxs=model.h01.abg01.Q̇)),
            ## DLR
            pl.Series("DLR.H01.WUE01.B29.MB//value_pred", zeros),
            ## Heat pumps district heating
            pl.Series("WPG.H01.ABG01.B29//value_pred", sol(sol.t, idxs=model.wpg.wpa.Q̇_H)),
        )
        
        PUE, ERF, ERE = calc_KPIs(input_data=result, attr="//value_pred")
        result = result.with_columns(PUE, ERF, ERE)

        return result
