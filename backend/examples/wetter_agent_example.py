from it_zauber_digital_twin.weather_prediction_agent.weather_prediction_agent import WeatherForecastAgent
from datetime import datetime, timezone, timedelta

def main():
    
    tool = WeatherForecastAgent(
        location="dresden",
    )
        
    # Example usage: Get current forecast for next 3 days
    print("Current forecast for next 3 days:")
    df = tool.predict(days=3)
    print(df)
    print("\n")
    
    
    timestamp = datetime(year=2025,
                         month=1,
                         day=1,
                         hour=0,
                         minute=0,
                         second=0,
                         tzinfo=timezone.utc)
    print(f"Pseudo-forecast for next 3 days starting on {timestamp.isoformat()} based on historical data")

    df = tool.predict(days=3,
                      timestamp=timestamp)
    print(df)
    
    print("\n")
    try:
        timestamp = datetime.now(timezone.utc) - timedelta(days=2)
        print(f"Error case: Wrong timestamp, using {timestamp.isoformat()}")
        df = tool.predict(days=3,
                          timestamp=timestamp)
        
        print(df)
    except ValueError as e:
        print(f"Error: {e}")
    
if __name__ == "__main__":
    main()