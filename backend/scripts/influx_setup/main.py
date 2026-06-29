from it_zauber_digital_twin.influx_agent.influx_agent import InfluxAgent
from pathlib import Path
import polars as pl
from tqdm import tqdm
from datetime import timedelta


def clean_database():
    ia = InfluxAgent()
    ia.clean_database()
    
def write_offline_results_to_influx():
    df = pl.read_parquet(Path(__file__).parents[1] / "examples" / "offline_results_with_learning.parquet")

    ia = InfluxAgent()

    columns = [i for i in df.columns if i not in ["time", "fmu_timestamp"]]
    for n, c in tqdm(enumerate(columns), total=len(columns)):
        if "_pred" in c:
            continue
        
        pred_col = c + "_pred"
        if pred_col in df.columns:
            this_df = df.select(
                pl.col("time").cast(pl.Datetime),
                pl.col(c).cast(pl.Float64).alias("value"),
                pl.col(pred_col).cast(pl.Float64).alias("value_pred")
            )
        else:
            this_df = df.select(
                pl.col("time").cast(pl.Datetime),
                pl.col(c).cast(pl.Float64).alias("value")
            )
    
        this_df = this_df.to_pandas().set_index("time")
        this_df.index = this_df.index.tz_localize("UTC")
        ia.client.write_points(
            this_df,
            measurement=f"urn:ngsi-ld:{c}"
        )
        print(this_df)
        
def write_dummy_prediction_to_influx():
    ia = InfluxAgent()
    df = pl.read_parquet(Path(__file__).parents[1] / "examples" / "offline_results_with_learning.parquet")
    
    pred_columns = [i for i in df.columns if "_pred" in i]
    pred_columns = ["claix_2018_power_pred"]  # For testing, only one column

    df_use = df.select(["time"] + pred_columns)


    # Get the last row
    last_row = df_use.tail(1)

    # Get the last timestamp
    last_time = last_row.select("time").item()

    # Create time series for one week ahead with 2-minute intervals
    end_time = last_time + timedelta(weeks=1)
    time_range = pl.datetime_range(
        start=last_time + timedelta(minutes=2),  # Start 2 minutes after last entry
        end=end_time,
        interval="2m",
        eager=True
    )

    # Get all columns except 'time' and multiply their last values by 1.05
    last_values = {}
    for col in df_use.columns:
        if col != "time":
            last_value = last_row.select(col).item()
            last_values[col] = last_value * 1.05

    # Create the new dataframe
    new_df = pl.DataFrame({
        "time": time_range,
        **{col: [value] * len(time_range) for col, value in last_values.items()}
    })
    
   
    columns = [i for i in new_df.columns if i not in ["time", "fmu_timestamp"]]
    for n in tqdm(columns, total=len(columns)):
        
        
        this_df = new_df.select(
            pl.col("time").cast(pl.Datetime),
            pl.col(n).cast(pl.Float64).alias("value_test_template"),
            pl.lit("test_template").alias("template_name")
            )

        this_df = this_df.to_pandas().set_index("time")
        this_df.index = this_df.index.tz_localize("UTC")
        ia.client.write_points(
            this_df,
            measurement=f"urn:ngsi-ld:{n.replace('_pred', '')}",
            tag_columns=["template_name"],
        )
    
    
def read_measurements():
    ia = InfluxAgent()
    # names = ia.get_all_influx_table_names() 

    
    # entities = ia.get_all_entitys_from_influx()
    
    data = ia.read_influx_table(
        entity_names="claix_2023_power",
        start_time="2025-02-18T21:56:00Z")
    # print(data["value_id"].unique())
    # 
    this_data = data.loc[data["value_id"] == "value_hallo"].copy()
    this_data = this_data.iloc[:5].copy()

    this_data["value_id"] = "value_test5"
    # print(this_data)
    
    p = Path(r"D:\Repos\IT_Zauber\AP3-Digitaler_Zwilling\temp.pkl")
    
    with open(p, "rb") as f:
        import pickle
        data = pickle.load(f)
    
    data["value_id"] = "value_test5"
    data = data.loc[data["entity_id"] == "claix_2023_power"].copy()
    data = data.iloc[:5].copy()
    # print(data)
    
    # this_data = data.copy(deep=True).reset_index()
    # this_data["value_id"] = "value_hallo2"
    # this_data.rename(columns={"index": "prediction_timestamps"}, inplace=True)
    # this_data.set_index("prediction_timestamps", inplace=True)
    # print(this_data)
    # print(this_data.index)
    
    
    # data["entity_id"] = this_data["entity_id"].to_list()
    # data["value_id"] = this_data["value_id"].to_list()
    # data["number"] = this_data["number"].to_list()
    
    # this_data.index = data.index.to_list()
    this_data.index = data.index
    this_data.index = this_data.index.to_list()
    
    print(data.index)
    # data.index = this_data.index
    # print(data.index)
    
    ia.client.write_points(
        this_data,
        measurement="data",
        tag_columns=["entity_id", "value_id"],
    )
    
    data = ia.read_influx_table(
        entity_names="claix_2023_power",
        start_time="2025-02-18T21:56:00Z"
        )
    
    print(data["value_id"].unique())
    
    # data = data.pivot(
    #     index="index",
    #     columns="entity_id",
    #     values=["value", "value_pred"]
    # )

    
    
if __name__ == "__main__":
    clean_database()
    # read_measurements()
    #  write_offline_results_to_influx()
    # write_dummy_prediction_to_influx()
    # read_measurements()
    #read_measurements()
    