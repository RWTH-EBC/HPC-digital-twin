import { InfluxDB } from "influx";
import { influxConfig } from "@/config/influx-config";

class InfluxService {
  private client: InfluxDB;
  private connected: boolean = false;
  private connectionCallbacks: Array<(connected: boolean) => void> = [];
  private isPeriodicCheckActive: boolean = false;
  private connectionCheckInterval: NodeJS.Timeout | null = null;
  private measurementsCache: string[] | null = null;
  private measurementsCacheTime: number = 0;
  private readonly MEASUREMENTS_CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

  constructor() {
    this.client = new InfluxDB({
      host: influxConfig.HOST,
      port: influxConfig.INFLUX_PORT,
      database: influxConfig.INFLUX_DB_NAME,
      protocol: "http",
    });
    console.log("InfluxService initialized");
    this.checkConnection();
  }

  async checkConnection(): Promise<boolean> {
    try {
      await this.client.query("SHOW DATABASES"); // Ping doesnt work because of CORS OPTIONS ISSUES
      const wasConnected = this.connected;
      this.connected = true;

      if (!wasConnected) {
        console.log("✅ InfluxDB connection established!");
        this.notifyConnectionChange(true);
      }
      return true;
    } catch (error) {
      const wasConnected = this.connected;
      this.connected = false;
      if (wasConnected) {
        console.log("❌ InfluxDB connection lost!");
        this.notifyConnectionChange(false);
      }
      return false;
    }
  }

  private notifyConnectionChange(connected: boolean): void {
    this.connectionCallbacks.forEach((callback) => {
      try {
        callback(connected);
      } catch (error) {
        console.error("Error in connection callback:", error);
      }
    });
  }

  async getMeasurements(): Promise<string[]> {
    const currentTime = Date.now();
    if (
      this.measurementsCache &&
      currentTime - this.measurementsCacheTime <
        this.MEASUREMENTS_CACHE_DURATION
    ) {
      return this.measurementsCache;
    }

    try {
      // Query for distinct entity_id values from the "data" measurement
      const query = 'SHOW TAG VALUES FROM "data" WITH KEY = "entity_id"';
      const result = await this.client.query(query);

      // Extract the entity_id values from the result
      const measurements = result.map((row: any) => row.value);

      // Update cache
      this.measurementsCache = measurements;
      this.measurementsCacheTime = currentTime;
      return measurements;
    } catch (error) {
      console.error("Failed to fetch measurements:", error);
      // Return cached data if available, even if expired
      return this.measurementsCache || [];
    }
  }

  async getEntityData(
    entityId: string,
    timeInterval: string = "1h",
    includePue: boolean = false,
    startDate?: string,
    endDate?: string,
  ): Promise<any[]> {
    try {
      const entityFilter = includePue
        ? `entity_id =~ /^(?:${entityId}|pue)$/`
        : `entity_id = '${entityId}'`;

      // Add time filter if startDate is provided
      const timeFilter = startDate
        ? `AND time >= '${startDate}T00:00:00Z'`
        : "";

      const endTimeFilter = endDate ? `AND time <= '${endDate}'` : "";
      const query = `
      SELECT mean(number) as mean_value
      FROM data
      WHERE ${entityFilter} ${timeFilter} ${endTimeFilter}
      GROUP BY time(${timeInterval}), entity_id, value_id
      FILL(none)
      `;

      console.log(query);
      const result = await this.client.query(query);
      return result;
    } catch (error) {
      console.error("Failed to fetch entity data:", error);
      return [];
    }
  }

  // Get the latest timestamp
  async getLatestTime(): Promise<Date | null> {
    try {
      const query = `
      SELECT LAST("number") AS last_value
      FROM data
    `;

      console.log(query);

      const result = await this.client.query(query);

      if (result && result.length > 0 && result[0].time) {
        return new Date(result[0].time);
      }

      console.warn("No latest timestamp found in InfluxDB.");
      return null;
    } catch (error) {
      console.error("Failed to fetch latest timestamp:", error);
      return null;
    }
  }

  // Function kriegt einen callback als input und returned direkt die Funktion,
  // mit der man disen callback dann wieder entfernt. Clever
  onConnectionChange(callback: (connected: boolean) => void): () => void {
    this.connectionCallbacks.push(callback);
    return () => {
      const index = this.connectionCallbacks.indexOf(callback);
      if (index > -1) {
        this.connectionCallbacks.splice(index, 1);
      }
    };
  }

  startPeriodicConnectionCheck(interval: number = 10000): void {
    if (this.isPeriodicCheckActive) {
      console.log("Periodic connection check is already active.");
      return;
    }
    console.log(
      `Starting periodic connection check every ${interval / 1000} s`,
    );
    this.isPeriodicCheckActive = true;
    if (this.connectionCheckInterval) {
      clearInterval(this.connectionCheckInterval);
    }
    this.connectionCheckInterval = setInterval(async () => {
      await this.checkConnection();
    }, interval);
  }

  stopPeriodicConnectionCheck(): void {
    if (this.connectionCheckInterval) {
      clearInterval(this.connectionCheckInterval);
      this.connectionCheckInterval = null;
      this.isPeriodicCheckActive = false;
      console.log("Stopped periodic connection check.");
    }
    this.isPeriodicCheckActive = false;
  }

  destroy(): void {
    this.stopPeriodicConnectionCheck();
    this.connectionCallbacks = [];
  }
}

export const influxService = new InfluxService();
