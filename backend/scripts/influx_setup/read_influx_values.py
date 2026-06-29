from it_zauber_digital_twin.influx_agent.influx_agent import InfluxAgent
from datetime import datetime

def delete_data_before_date():
    ia = InfluxAgent()
    
    # Prompt user for date input
    print("Enter the date (data before this date will be deleted)")
    print("Format: YYYY-MM-DD HH:MM:SS (time is optional, defaults to 00:00:00)")
    print("Example: 2025-08-28 or 2025-08-28 15:30:00")
    
    date_input = input("Date: ").strip()
    
    try:
        # Try to parse the date
        if ' ' in date_input:
            # Date and time provided
            parsed_date = datetime.strptime(date_input, "%Y-%m-%d %H:%M:%S")
        else:
            # Only date provided, default to start of day
            parsed_date = datetime.strptime(date_input, "%Y-%m-%d")
        
        # Convert to ISO format for InfluxDB
        iso_date = parsed_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Construct the delete query
        delete_query = f"""
        DELETE FROM data
        WHERE time < '{iso_date}'
        """
        
        print("\nQuery to be executed:")
        print(delete_query)
        
        # Ask for confirmation
        confirm = input(f"\nThis will delete ALL data before {iso_date}. Are you sure? (yes/no): ").strip().lower()
        
        if confirm == 'yes':
            # Execute the delete query
            result = ia.client.query(delete_query)
            print("Delete operation completed.")
            return result
        else:
            print("Delete operation cancelled.")
            return None
            
    except ValueError as e:
        print(f"Invalid date format: {e}")
        print("Please use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS format")
        return None
    except Exception as e:
        print(f"Error executing delete query: {e}")
        return None

def main():
    ia = InfluxAgent()
    value_ids = ia.get_all_influx_table_names()
    print(value_ids)


    
    # query = """
    # SELECT mean(number) as mean_value
    # FROM data
    # WHERE entity_id = 'claix_2023_power'
    # AND time <= '2025-08-28T10:00:00Z'
    # GROUP BY time(1h), value_id
    # FILL(none)
    # """
    
    # res = ia.client.query(query)
    
    # for key in res.keys():
    #     print(key)
    #     print(res[key])

    # df.index.name = "time"
    # df = df.reset_index()
    # print(df)
    # df = df.pivot(
    #         index="time",
    #         columns=["entity_id", "value_id"],
    #         values="number"
    #     )
    # print(df)
if __name__ == "__main__":
    #main()
    main()
    
