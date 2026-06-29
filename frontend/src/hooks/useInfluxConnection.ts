import { useEffect } from "react";
import { useDashboardStore } from "@/stores/store";
import { influxService } from "@/services/influxdb";

export const useInfluxConnection = (checkInterval: number = 10000) => {
    const { setIsConnected } = useDashboardStore();

    useEffect(() => {
        const unsubscribe = influxService.onConnectionChange((connected) => {
            console.log("Connection status changed:", connected);
            setIsConnected(connected);
        });

        influxService.startPeriodicConnectionCheck(checkInterval);
        influxService.checkConnection().then((connected) => {
            console.log("Initial connection check result:", connected);
            setIsConnected(connected);
        });

        return () => {
            console.log("Cleaning up InfluxDB connection check.");
            unsubscribe();
            influxService.stopPeriodicConnectionCheck();

        }
}, [setIsConnected, checkInterval]);
};
// This hook manages the InfluxDB connection state and periodically checks the connection status.
// It updates the global state with the connection status and cleans up on unmount.
