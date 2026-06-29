import time
from pathlib import Path
from it_zauber_digital_twin.utils.fiware_utils import EntityValueNoneError

import polars as pl
from it_zauber_digital_twin.base_agents.base_model_agent import BaseModelAgent
from it_zauber_digital_twin.utils.fiware_utils import get_values_from_fiware
from it_zauber_digital_twin.utils.mqtt_utils import get_mqtt_broker


class PreprocessingAgent(BaseModelAgent):
    def __init__(
        self,
        timestep: int = 5,
        log_level: str = "DEBUG",
    ) -> None:
        """
        Initializes the PreprocessingAgent. This agent is only used for the preprocessing of the data during live operation and not for the prediction.
        """

        super().__init__(
            name="PreprocessingAgent",
            log_level=log_level,
            config_path=Path(__file__).parent / "config.json",
        )

        self.timestep = timestep
        self.mqtt_broker = get_mqtt_broker()

    def run(self):
        self.logger.info("Starting Preprocessing Agent")

        start_time = time.perf_counter()
        interval = self.timestep
        deadline = start_time + interval
        while True:
            try:
                input_data, timestamp = get_values_from_fiware(self.get_from_fiware)

                input_data_df = pl.DataFrame(input_data)

                result = self.do_step(input_data=input_data_df)
                self.logger.debug(f"Do stepped for time {timestamp}")
                to_push = result.select(self.push_to_fiware).to_dicts()[0]
                self.mqtt_broker.res_dict_to_iot_agent(to_push, timestamp, self.push_to_fiware)
            except EntityValueNoneError as e:
                self.logger.warning(f"Skipping timestep due to missing data: {e}")
                

            sleep_time = deadline - time.perf_counter()
            deadline += interval
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                self.logger.warning(
                    f"PreprocessingAgent is lagging behind by {-sleep_time:.2f} seconds"
                )

    def do_step(self, input_data: pl.DataFrame) -> dict | pl.DataFrame:
        input_data = self.to_si(input_data)
        result = self._calc_m_flows(input_data=input_data)
        result = self._calc_rkw_is_ons(input_data=result)
        result = self._calc_pump_status(input_data=result)
        result = self._calc_powers(input_data=result)
        result = self._calc_claix_2023_power(input_data=result)
        result = self._calc_pue(input_data=result)
        result = self.from_si(result)
        return result

    def _calc_pue(self, input_data: pl.DataFrame) -> pl.DataFrame:
        p_cluster = pl.col("claix_2018_power//value") + pl.col(
            "claix_2023_power//value"
        )
        fernkaelte_q_flow = pl.col("fernkaelte_q_flow//value")
        rkw_and_pump_power = pl.col("rkw_and_pumps_power//value")
        claix2023_cdu_sc_power = pl.col("claix_2023_cdu_sc_power//value")
        claix2018_sc_power = pl.col("claix_2018_sc_power//value")
        e_total = (
            0.4 * fernkaelte_q_flow
            + rkw_and_pump_power
            + claix2023_cdu_sc_power
            + claix2018_sc_power
            + p_cluster
        )
        pue = (e_total / p_cluster).alias("pue//value")

        return input_data.with_columns(pue)

    def _calc_claix_2023_power(self, input_data: pl.DataFrame) -> pl.DataFrame:
        pow_cols = [
            "pow-kop6-mh-100-1//value",
            "pow-kop6-mh-100-2//value",
            "pow-kop6-mh-143-1//value",
            "pow-kop6-mh-143-2//value",
            "pow-kop6-mh-144-1//value",
            "pow-kop6-mh-144-2//value",
            "pow-kop6-mh-145-1//value",
            "pow-kop6-mh-145-2//value",
            "pow-kop6-mh-146-1//value",
            "pow-kop6-mh-146-2//value",
            "pow-kop6-mh-147-1//value",
            "pow-kop6-mh-147-2//value",
            "pow-kop6-mh-148-1//value",
            "pow-kop6-mh-148-2//value",
            "pow-kop6-mh-149-1//value",
            "pow-kop6-mh-149-2//value",
            "pow-kop6-mh-200-1//value",
            "pow-kop6-mh-200-2//value",
            "pow-kop6-mh-243-1//value",
            "pow-kop6-mh-243-2//value",
            "pow-kop6-mh-244-1//value",
            "pow-kop6-mh-244-2//value",
            "pow-kop6-mh-245-1//value",
            "pow-kop6-mh-245-2//value",
            "pow-kop6-mh-246-1//value",
            "pow-kop6-mh-246-2//value",
            "pow-kop6-mh-247-1//value",
            "pow-kop6-mh-247-2//value",
            "pow-kop6-mh-248-1//value",
            "pow-kop6-mh-248-2//value",
            "pow-kop6-mh-249-1//value",
            "pow-kop6-mh-249-2//value",
        ]

        sc_cdu_pow_cols = ["pow-kop6-mh-100-3//value", "pow-kop6-mh-200-3//value"]

        claix_2023_power = pl.sum_horizontal([pl.col(col) for col in pow_cols]).alias(
            "claix_2023_power//value"
        )

        claix_2023_cdu_sc_power = pl.sum_horizontal(
            [pl.col(col) for col in sc_cdu_pow_cols]
        ).alias("claix_2023_cdu_sc_power//value")

        df = input_data.with_columns(
            [
                claix_2023_power,
                claix_2023_cdu_sc_power,
                pl.lit(0).alias("claix_2018_power//value"),
                pl.lit(0).alias("claix_2018_sc_power//value"),
            ]
        )
        return df

    def _calc_powers(self, input_data: pl.DataFrame) -> dict:
        ULK_SW23_pumps = [
            "wt07_pump14_power//value",
            "wt07_pump15_power//value",
            "pump24_power//value",
            "pump25_power//value",
            "pump16_power//value",
            "pump17_power//value",
            "pump18_power//value",
            "pump19_power//value",
            "pump20_power//value",
            "pump21_power//value",
            "pump22_power//value",
            "pump23_power//value",
        ]
        rkw_and_pumps_power = (
            pl.col("klima_kaelte_power//value")
            - pl.sum_horizontal([pl.col(col) for col in ULK_SW23_pumps])
            - 6000
        ).alias("rkw_and_pumps_power//value")

        pumps_cols_inf = [
            "rkw_pump7_power//value",
            "rkw_pump8_power//value",
            "rkw_pump9_power//value",
        ]

        pumps_cols_kop6 = [
            "cluster_kop6_rack_groups_pump10_power//value",
            "cluster_kop6_rack_groups_pump11_power//value",
        ]

        pumps_cols_sw23 = [
            "cluster_sw23_rack_groups_pump12_power//value",
            "cluster_sw23_rack_groups_pump13_power//value",
        ]

        pumps_cols_rkw1 = [
            "rkw01_pump1_power//value",
            "rkw01_pump2_power//value",
        ]

        pumps_cols_rkw2 = [
            "rkw02_pump3_power//value",
            "rkw02_pump4_power//value",
        ]

        pumps_cols_rkw3 = [
            "rkw03_pump5_power//value",
            "rkw03_pump6_power//value",
        ]

        pumps_inf_power = pl.sum_horizontal([pl.col(col) for col in pumps_cols_inf])

        pumps_kop6_power = pl.sum_horizontal([pl.col(col) for col in pumps_cols_kop6])

        pumps_sw23_power = pl.sum_horizontal([pl.col(col) for col in pumps_cols_sw23])

        pumps_rkw1_power = pl.sum_horizontal([pl.col(col) for col in pumps_cols_rkw1])

        pumps_rkw2_power = pl.sum_horizontal([pl.col(col) for col in pumps_cols_rkw2])

        pumps_rkw3_power = pl.sum_horizontal([pl.col(col) for col in pumps_cols_rkw3])

        rkw_no_pump_power = (
            rkw_and_pumps_power
            - pumps_inf_power
            - pumps_kop6_power
            - pumps_sw23_power
            - pumps_rkw1_power
            - pumps_rkw2_power
            - pumps_rkw3_power
        )

        total_rkw_power = (
            rkw_no_pump_power + pumps_rkw1_power + pumps_rkw2_power + pumps_rkw3_power
        )

        total_pumps_inf_power = pumps_inf_power + pumps_kop6_power + pumps_sw23_power

        result = input_data.with_columns(
            [
                rkw_and_pumps_power,
                pumps_inf_power.alias("pumps_inf_power//value"),
                pumps_kop6_power.alias("pumps_kop6_power//value"),
                pumps_sw23_power.alias("pumps_sw23_power//value"),
                pumps_rkw1_power.alias("pumps_rkw01_power//value"),
                pumps_rkw2_power.alias("pumps_rkw02_power//value"),
                pumps_rkw3_power.alias("pumps_rkw03_power//value"),
                rkw_no_pump_power.alias("rkw_no_pump_power//value"),
                total_rkw_power.alias("total_rkw_power//value"),
                total_pumps_inf_power.alias("total_pumps_inf_power//value"),
            ]
        )

        return result

    def _calc_m_flows(self, input_data: pl.DataFrame) -> pl.DataFrame:
        t_out_kop6 = input_data["kop6_coolant_temperature_warm//value"]
        t_out_sw23 = input_data["sw23_coolant_temperature_warm//value"]
        sc_sw23_vol_flow_primary = input_data["sw23_coolant_flow//value"]
        kop6_vol_flow_primary = input_data["kop6_coolant_flow//value"]

        vol_flow_primary = kop6_vol_flow_primary + sc_sw23_vol_flow_primary
        t_out_inf = (
            t_out_kop6 * kop6_vol_flow_primary + t_out_sw23 * sc_sw23_vol_flow_primary
        ) / vol_flow_primary

        result = input_data.with_columns(
            [
                t_out_inf.alias("t_water_warm_inf//value"),
                vol_flow_primary.alias("vol_flow_inf//value"),
            ]
        )

        return result

    def _calc_rkw_is_ons(self, input_data: pl.DataFrame) -> dict:
        rkw01_vents_rpm = input_data["rkw01_vents_rpm//value"]
        rkw02_vents_rpm = input_data["rkw02_vents_rpm//value"]
        rkw03_vents_rpm = input_data["rkw03_vents_rpm//value"]

        rkw01_is_on = rkw01_vents_rpm > 1
        rkw02_is_on = rkw02_vents_rpm > 1
        rkw03_is_on = rkw03_vents_rpm > 1

        result = input_data.with_columns(
            [
                rkw01_is_on.alias("rkw01_is_on//value"),
                rkw02_is_on.alias("rkw02_is_on//value"),
                rkw03_is_on.alias("rkw03_is_on//value"),
            ]
        )

        return result

    def _calc_pump_status(self, input_data: pl.DataFrame) -> dict:
        """
        Eigentlich von Svenne so berechnet:
            df["rkw01_pump1_pump2_status"] = df["rkw01_pump1_status"].combine(df["rkw01_pump2_status"], func=max).rolling(window=10).mean()

            df["rkw02_pump3_pump4_status"] = df["rkw02_pump3_status"].combine(df["rkw02_pump4_status"], func=max).rolling(window=10).mean()

            df["rkw03_pump5_pump6_status"] = df["rkw03_pump5_status"].combine(df["rkw03_pump6_status"], func=max).rolling(window=10).mean()

        mit rolling window 10. Hier jetzt einfach nur max Entscheidung.
        """

        pump_pairs = [
            (
                "rkw01_pump1_status//value",
                "rkw01_pump2_status//value",
                "rkw01_pump1_pump2_status//value",
            ),
            (
                "rkw02_pump3_status//value",
                "rkw02_pump4_status//value",
                "rkw02_pump3_pump4_status//value",
            ),
            (
                "rkw03_pump5_status//value",
                "rkw03_pump6_status//value",
                "rkw03_pump5_pump6_status//value",
            ),
        ]

        columns = []
        for pump1, pump2, result_key in pump_pairs:
            new_column = pl.max_horizontal(
                [input_data[pump1], input_data[pump2]]
            ).alias(result_key)
            columns.append(new_column)

        result = input_data.with_columns(columns)

        rkw01pump_is_on = result["rkw01_pump1_pump2_status//value"] > 0.1
        rkw02pump_is_on = result["rkw02_pump3_pump4_status//value"] > 0.1
        rkw03pump_is_on = result["rkw03_pump5_pump6_status//value"] > 0.1

        result = result.with_columns(
            [
                rkw01pump_is_on.alias("rkw01pump_is_on//value"),
                rkw02pump_is_on.alias("rkw02pump_is_on//value"),
                rkw03pump_is_on.alias("rkw03pump_is_on//value"),
            ]
        )

        return result


if __name__ == "__main__":
    agent = PreprocessingAgent()
    agent.run()
