import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { Input } from "@/components/ui/input";
import { useDashboardStore } from "@/stores/store";
import {
  ChevronLeft,
  ChevronRight,
  Check,
  ChevronsUpDown,
  TrendingUp,
} from "lucide-react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  XAxis,
  YAxis,
  ReferenceArea,
} from "recharts";

import { Button } from "@/components/ui/button";
import { ChartContainer } from "@/components/ui/chart";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { influxService } from "@/services/influxdb";
import React, {
  useEffect,
  useState,
  useRef,
  useMemo,
  useCallback,
} from "react";
import { throttle } from "lodash";

import { ProcessedPoint } from "@/types";

// Configuration for the chart lines
const chartConfig = {
  value: {
    label: "Measurement",
    color: "hsl(var(--chart-1))",
  },
  value_pred: {
    label: "Live Prediction",
    color: "hsl(var(--chart-2))",
  },
};

export function LineChartCard() {
  const {
    isConnected,
    startDate,
    selectedMeasurement,
    selectedTemplates,
    allMeasurements,
    appliedSettings,
    setMeanPue,
    setStartDate,
    setSelectedMeasurement,
    setSelectedTemplates,
    setAllMeasurements,
  } = useDashboardStore();
  // Track changes in selected template objects to trigger data refetch
  const selectedTemplateObjects = useDashboardStore(
    (state) => state.selectedTemplateObjects
  );
  // For the dropdown menu of measurements
  const [measurementDropdownOpen, setMeasurementDropdownOpen] = useState(false);
  // For zooming and selecting area on the chart
  const [refAreaLeft, setRefAreaLeft] = useState<number | null>(null);
  const [refAreaRight, setRefAreaRight] = useState<number | null>(null);
  const [isSelecting, setIsSelecting] = useState(false);
  const [startTime, setStartTime] = useState<number | null>(null);
  const [endTime, setEndTime] = useState<number | null>(null);
  const startRef = useRef<number | null>(null);
  const endRef = useRef<number | null>(null);
  const lastZoomRange = useRef<number | null>(null);
  const influxDBEndRef = useRef<number>(Date.now());

  // For fetching the measurements for the dropdown menu
  useEffect(() => {
    // Fetch all measurements when the component mounts
    const fetchMeasurements = async () => {
      if (isConnected) {
        const measurementsList = await influxService.getMeasurements();
        setAllMeasurements(measurementsList);
      }
    };
    // Fetch measurements initially and set up periodic updates
    console.log("Fetching measurements on mount.");
    fetchMeasurements();
    const interval = setInterval(fetchMeasurements, 30000);
    return () => clearInterval(interval);
  }, [isConnected, setAllMeasurements]);

  const transformedInfluxData = (influxData: any[]): ProcessedPoint[] => {
    console.log(selectedTemplates);
    const groupedByTime = new Map<number, Partial<ProcessedPoint>>();
    influxData.forEach((row) => {
      const timeKey = row.time.getTime();

      if (!groupedByTime.has(timeKey)) {
        const initialPoint: Partial<ProcessedPoint> = {
          time: row.time,
          time_as_number: timeKey,
          value: null,
          value_pred: null,
        };

        selectedTemplates.forEach((template) => {
          initialPoint[`value_${template}`] = null;
        });

        groupedByTime.set(timeKey, initialPoint);
      }

      const point = groupedByTime.get(timeKey)!;

      if (row.value_id === "value") {
        point.value = row.mean_value;
      } else if (row.value_id == "value_pred") {
        point.value_pred = row.mean_value;
      } else {
        selectedTemplates.forEach((template) => {
          if (row.value_id === `value_${template}`) {
            point[`value_${template}`] = row.mean_value;
          }
        });
      }
    });

    return Array.from(groupedByTime.values())
      .filter((point) => {
        if (point.value !== null || point.value_pred !== null) return true;

        return selectedTemplates.some(
          (template) => point[`value_${template}`] !== null
        );
      })
      .sort(
        (a, b) => a.time_as_number! - b.time_as_number!
      ) as ProcessedPoint[];
  };

  // Replace the test influx code with proper async data fetching
  const [realData, setRealData] = useState<ProcessedPoint[]>([]);

  // Function to fetch real data from InfluxDB with different modes
  const fetchRealData = useCallback(
    async (
      mode: "force" | "zoom" | "interval" = "interval",
      latestStartTime?: number,
      latestEndTime?: number
    ) => {
      if (!isConnected || !selectedMeasurement) return;

      try {
        // Get the last timestamp in the entire dataset to calculate % zoom
        const latestTime = await influxService.getLatestTime();
        if (latestTime) {
          influxDBEndRef.current = latestTime.getTime();
        } else {
          console.warn("No latest data found in InfluxDB");
          return;
        }

        // Determine global start and end times
        const globalStart = new Date(startDate).getTime();
        const globalEnd = influxDBEndRef.current;

        // Fetch always in "force" or "interval" mode, otherwise check zoom thresholds
        let shouldFetch = mode === "force" || mode === "interval";

        // Use latest times if provided (based on zoom level), otherwise use component state
        const zoomStartTime = latestStartTime ?? startTime;
        const zoomEndTime = latestEndTime ?? endTime;

        // Threshold-based logic only when in "threshold" mode
        if (mode === "zoom" && zoomStartTime && zoomEndTime) {
          // Calculate zoom ratio based on visible ranges
          // Calculate current vsible range
          const newZoomRange = zoomEndTime - zoomStartTime; // in ms
          // If no previous zoom range recorded, assume full range
          const previousZoomRange =
            lastZoomRange.current ?? globalEnd - globalStart;

          // Calculate zoom ratio of current visible range relative to previous range
          const zoomRatio = newZoomRange / previousZoomRange;
          // Only fetch if zoom level changed significantly (±30%)
          if (zoomRatio < 0.7 || zoomRatio > 1.3) {
            shouldFetch = true;
            console.log("Significant zoom level change detected → fetching");
            lastZoomRange.current = newZoomRange;
          }

          // Additionally, if user is near full range (within 1 day), fetch to ensure full data
          // Handle edge case where zoom ratio is <30% but user is near full range
          const isNearFullRange =
            globalEnd - globalStart - newZoomRange < 24 * 60 * 60 * 1000;
          if (isNearFullRange) {
            shouldFetch = true;
            console.log("User is near full range → fetching");
            // If user is near full range, reset lastZoomRange
            lastZoomRange.current = null;
          }
        }

        // If zoom change is less than 30%, skip fetching data from InfluxDB
        if (!shouldFetch) {
          console.log("Skipping fetch, no significant change detected.");
          return;
        }

        console.log(`Fetching due to ${mode} mode`);

        // Determine time range and query interval
        // Calculate diffMs based on zoomed or full range
        const diffMs =
          zoomStartTime != null && zoomEndTime != null
            ? zoomEndTime - zoomStartTime
            : globalEnd - globalStart;

        // Calculate difference of visible range in minutes
        const diffMinutes = diffMs / (1000 * 60);
        // Number of data points to display in the chart
        const targetPoints = 1000;
        // Calculate raw interval between points in minutes
        const rawIntervalMinutes = Math.max(diffMinutes / targetPoints, 1);

        // Set query interval for influx query based on calculated raw interval
        let queryInterval: string;
        if (rawIntervalMinutes <= 2) queryInterval = "2m";
        else if (rawIntervalMinutes <= 10) queryInterval = "10m";
        else if (rawIntervalMinutes <= 30) queryInterval = "30m";
        else if (rawIntervalMinutes <= 60) queryInterval = "1h";
        else if (rawIntervalMinutes <= 180) queryInterval = "3h";
        else if (rawIntervalMinutes <= 360) queryInterval = "6h";
        else if (rawIntervalMinutes <= 720) queryInterval = "12h";
        else if (rawIntervalMinutes <= 1440) queryInterval = "1d";
        else if (rawIntervalMinutes <= 4320) queryInterval = "3d";
        else if (rawIntervalMinutes <= 10080) queryInterval = "7d";
        else if (rawIntervalMinutes <= 20160) queryInterval = "14d";
        else queryInterval = "14d";

        // Determine start date for InfluxDB query
        // If zoomed, use zoom start date, otherwise use global start date
        const startDateForInfluxQuery =
          zoomStartTime && zoomEndTime
            ? new Date(zoomStartTime).toISOString().split("T")[0]
            : startDate;

        let endDateForInfluxQuery;
        console.log(
          "appliedSettings?.simulationTimeInDays",
          appliedSettings?.simulationTimeInDays
        );
        // Determine end date for InfluxDB query
        if (zoomStartTime && zoomEndTime) {
          endDateForInfluxQuery = new Date(zoomEndTime).toISOString();
        } else if (appliedSettings?.simulationTimeInDays) {
          const offsetMs =
            appliedSettings.simulationTimeInDays * 24 * 60 * 60 * 1000;
          endDateForInfluxQuery = new Date(Date.now() + offsetMs).toISOString();
        }

        // Fetch from InfluxDB
        const influxData = await influxService.getEntityData(
          selectedMeasurement,
          queryInterval,
          true,
          startDateForInfluxQuery,
          endDateForInfluxQuery
        );
        console.log(influxData);

        const pueData = influxData.filter(
          (row) =>
            row.entity_id === "pue" &&
            row.value_id === "value" &&
            row.mean_value !== null
        );
        const measurementData = influxData.filter(
          (row) => row.entity_id === selectedMeasurement
        );
        console.log("PUE Data:", pueData);
        console.log("Measurement Data:", measurementData);

        const transformedData = transformedInfluxData(measurementData);

        const pueMean =
          pueData.length > 0
            ? pueData.reduce((sum, row) => sum + row.mean_value, 0) /
              pueData.length
            : null;

        console.log("PUE Mean:", pueMean);
        setMeanPue(pueMean);
        console.log("Fetched and transformed real data:", transformedData);
        setRealData(transformedData);
      } catch (error) {
        console.error("Error fetching real data:", error);
      }
    },
    [
      isConnected,
      selectedMeasurement,
      selectedTemplates,
      startDate,
      startTime,
      endTime,
    ]
  );

  // Keep reference values updated with latest start/end times
  // Used in interval fetching to get latest zoom range
  useEffect(() => {
    startRef.current = startTime;
    endRef.current = endTime;
  }, [startTime, endTime]);

  // Fetch real data when key dependencies change and set up periodic interval fetching
  useEffect(() => {
    let intervalId: NodeJS.Timeout;
    // Fetch data immediately when dependencies change
    fetchRealData("force");

    // Set up interval to fetch data every 20 seconds
    if (isConnected && selectedMeasurement) {
      intervalId = setInterval(() => {
        const currentStart = startRef.current;
        const currentEnd = endRef.current;
        console.log("Interval fetch triggered.");
        if (currentStart && currentEnd) {
          // refresh zoomed data when user has zoomed in to not lose high resolution data on refetch
          fetchRealData("zoom", currentStart, currentEnd);
        } else {
          // refresh full data when user is at full view
          fetchRealData("interval");
        }
      }, 20000);
    }
    return () => clearInterval(intervalId);
  }, [isConnected, selectedMeasurement, selectedTemplates, startDate]);

  // Fetch data when zoom range changes
  useEffect(() => {
    if (startTime != null && endTime != null) {
      fetchRealData("zoom", startTime, endTime);
    } else {
      fetchRealData("force"); // fetch full range upon reset
    }
  }, [startTime, endTime, selectedTemplateObjects]);

  // Smart date formatter that adapts to data range (compact version)
  const getSmartDateFormatter = (data: ProcessedPoint[]) => {
    if (data.length === 0) {
      return (value: number) =>
        new Date(value).toLocaleTimeString("de-DE", {
          hour: "2-digit",
          minute: "2-digit",
        });
    }

    // Calculate time span of data
    const times = data.map((d) => d.time_as_number).sort((a, b) => a - b);
    const startTime = times[0];
    const endTime = times[times.length - 1];
    const timeSpanHours = (endTime - startTime) / (1000 * 60 * 60);

    return (value: number) => {
      const date = new Date(value);

      if (timeSpanHours <= 6) {
        // Less than 6 hours: show only time (HH:MM)
        return date.toLocaleTimeString("de-DE", {
          day: "2-digit",
          month: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
        });
      } else if (timeSpanHours <= 24) {
        // Less than 24 hours: show compact time (HH:MM)
        return date.toLocaleTimeString("de-DE", {
          day: "2-digit",
          month: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
        });
      } else if (timeSpanHours <= 168) {
        // 1 week
        // Up to 1 week: show compact date (DD.MM)
        return date.toLocaleDateString("de-DE", {
          day: "2-digit",
          month: "2-digit",
          hour: "2-digit",
        });
      } else {
        // More than 1 week: show month/day (MM/DD)
        return date.toLocaleDateString("de-DE", {
          day: "2-digit",
          month: "2-digit",
          hour: "2-digit",
        });
      }
    };
  };

  // Fewer ticks for cleaner look
  const getOptimalTickCount = (data: ProcessedPoint[]) => {
    if (data.length === 0) return 3;

    const dataPoints = data.length;

    if (dataPoints <= 10) return 3;
    if (dataPoints <= 50) return 4;
    if (dataPoints <= 200) return 5;
    return 6; // Max 6 ticks for clean appearance
  };

  const chartRef = useRef<HTMLDivElement>(null);

  // Calculate dynamic Y domain based on actual data
  const yDomain: [number, number] = useMemo(() => {
    if (realData.length === 0) return [0, 100];

    const values = realData
      .map((d) => d.value)
      .filter((v) => v !== null) as number[];
    if (values.length === 0) return [0, 100];

    const min = Math.min(...values);
    const max = Math.max(...values);
    const padding = (max - min) * 0.1; // 10% padding

    return [min - padding, max + padding];
  }, [realData]);

  // On mouse down (click and hold), start selection
  const handleMouseClickHold = (e: any) => {
    if (e && e.activeLabel) {
      setRefAreaLeft(e.activeLabel);
      setIsSelecting(true);
    }
  };

  // On mouse move, update selection area
  const handleMouseMove = useCallback(
    throttle((e: any) => {
      if (isSelecting && e && e.activeLabel) {
        setRefAreaRight(e.activeLabel);
      }
    }, 50), // max once every 50ms
    [isSelecting]
  );

  // On mouse release, finalize selection and zoom
  const handleMouseClickRelease = () => {
    if (isSelecting && refAreaLeft !== null && refAreaRight !== null) {
      const [left, right] = [refAreaLeft, refAreaRight].sort((a, b) => a - b);
      setStartTime(left);
      setEndTime(right);
    }
    setRefAreaLeft(null);
    setRefAreaRight(null);
    setIsSelecting(false);
  };

  // Shift view left by one day
  const handleShiftLeft = useCallback(
    throttle(() => {
      if (!realData.length) return;

      const globalStart = new Date(startDate).getTime();
      const first = realData[0].time_as_number;
      const last = influxDBEndRef.current;

      const currentStart = startTime ?? first;
      const currentEnd = endTime ?? last;
      const oneDayMs = 24 * 60 * 60 * 1000;

      // Prevent shifting beyond selected start date
      const newStart = Math.max(currentStart - oneDayMs, globalStart);
      const newEnd = Math.max(currentEnd - oneDayMs, newStart);

      setStartTime(newStart);
      setEndTime(newEnd);

      fetchRealData("force", newStart, newEnd);
    }, 300), // max once every 300ms
    [realData, startTime, endTime, fetchRealData, startDate]
  );

  // Shift view right by one day
  const handleShiftRight = useCallback(
    throttle(() => {
      if (!realData.length) return;

      const first = realData[0].time_as_number;
      const last = influxDBEndRef.current;

      const currentStart = startTime ?? first;
      const currentEnd = endTime ?? last;
      const oneDayMs = 24 * 60 * 60 * 1000;

      const newEnd = Math.min(currentEnd + oneDayMs, last);
      const newStart = Math.min(currentStart + oneDayMs, newEnd);

      setStartTime(newStart);
      setEndTime(newEnd);

      fetchRealData("force", newStart, newEnd);
    }, 300), // max once every 300ms
    [realData, startTime, endTime, fetchRealData]
  );

  // Zooming with mouse wheel handler
  const handleZoom = useCallback(
    throttle((e: React.WheelEvent<HTMLDivElement>) => {
      e.preventDefault();
      if (!realData.length) return;

      const first = realData[0].time_as_number;
      const last = influxDBEndRef.current;

      const zoomFactor = 0.2;
      const direction = e.deltaY < 0 ? 1 : -1;

      const currentStart = startTime ?? first;
      const currentEnd = endTime ?? last;
      const range = currentEnd - currentStart;
      const zoomAmount = range * zoomFactor * direction;

      const chartRect = chartRef.current?.getBoundingClientRect();
      const mouseX = e.clientX - (chartRect?.left ?? 0);
      const width = chartRect?.width ?? 1;
      const ratio = mouseX / width;

      const mouseWheelInputStart = currentStart + zoomAmount * ratio;
      const mouseWheelInputEnd = currentEnd - zoomAmount * (1 - ratio);

      // Calculate how many points would be visible after zoom
      const pointsInNewRange = realData.filter(
        (d) =>
          d.time_as_number >= mouseWheelInputStart &&
          d.time_as_number <= mouseWheelInputEnd
      ).length;

      if (pointsInNewRange < 3) {
        // Prevent zoom if fewer than 3 points would be visible
        return;
      }

      // Limit zoom to data bounds
      let newStart: number;
      const mouseWheelInputStartDate = new Date(mouseWheelInputStart)
        .toISOString()
        .split("T")[0];
      // Prevent zooming out beyond user selected start date
      if (mouseWheelInputStartDate < startDate) {
        newStart = new Date(startDate).getTime();
      } else {
        newStart = mouseWheelInputStart;
      }

      let newEnd: number;
      const mouseWheelInputEndDate = new Date(mouseWheelInputEnd)
        .toISOString()
        .split("T")[0];
      // Prevent zooming out beyond last available data point
      if (mouseWheelInputEndDate > new Date(last).toISOString().split("T")[0]) {
        newEnd = last;
      } else {
        newEnd = mouseWheelInputEnd;
      }

      setStartTime(newStart);
      setEndTime(newEnd);
    }, 100), // max once every 100ms
    [realData, startTime, endTime]
  );

  // Wheel event listener for zooming on chart
  useEffect(() => {
    const el = chartRef.current;
    if (!el) return;

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault(); // cancel default scrolling
      handleZoom(e);
    };

    el.addEventListener("wheel", handleWheel, { passive: false });

    return () => {
      el.removeEventListener("wheel", handleWheel);
    };
  }, [realData, startTime, endTime]);

  // Reset zoom to show all data
  const resetZoom = () => {
    setStartTime(null);
    setEndTime(null);
    lastZoomRange.current = null;
  };

  // Filter data based on zoom range
  const zoomedData = useMemo(() => {
    if (!startTime || !endTime) return realData;
    return realData.filter(
      (d) => d.time_as_number >= startTime && d.time_as_number <= endTime
    );
  }, [realData, startTime, endTime]);

  if (!isConnected) {
    return (
      <Card className="md:col-span-4 h-full flex-grow">
        <CardHeader>
          <CardTitle className="text-red-500">NO INFLUX CONNECTION</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="md:col-span-4 h-full flex-grow">
      <CardHeader className="flex items-center gap-2 space-y-0 pb-1 sm:flex-row">
        <div className="grid flex-1 gap-1 min-w-0">
          <CardTitle className="flex items-center gap-2">
            <TrendingUp />
            Plot
          </CardTitle>
          <CardDescription>Real-time measurement data</CardDescription>
        </div>

        <div className="flex-shrink-0">
          <label className="block text-sm font-medium text-gray-700">
            Start Date
          </label>
          <Input
            type="date"
            value={startDate}
            onChange={(e) => {
              setStartDate(e.target.value);
            }}
            max={new Date().toISOString().split("T")[0]} // Prevent future dates
          />
        </div>

        <div className="flex-grow min-w-0 max-w-md">
          <label className="block text-sm font-medium text-gray-700">
            Measurement
          </label>
          <Popover
            open={measurementDropdownOpen}
            onOpenChange={setMeasurementDropdownOpen}
          >
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                role="combobox"
                aria-expanded={measurementDropdownOpen}
                className="w-full justify-between overflow-hidden text-ellipsis whitespace-nowrap"
              >
                {selectedMeasurement
                  ? allMeasurements
                      .find((m: string) => m === selectedMeasurement)
                      ?.replace("urn:ngsi-ld:", "")
                  : "Select measurement..."}
                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto min-w-[240px] max-w-md p-0">
              <Command>
                <CommandInput placeholder="Search measurement..." />
                <CommandList>
                  <CommandEmpty>No measurement found.</CommandEmpty>
                  <CommandGroup>
                    {allMeasurements.map((measurement: string) => (
                      <CommandItem
                        key={measurement}
                        value={measurement}
                        onSelect={(currentValue) => {
                          setSelectedMeasurement(
                            currentValue === selectedMeasurement
                              ? ""
                              : currentValue
                          );
                          setMeasurementDropdownOpen(false);
                        }}
                      >
                        <Check
                          className={cn(
                            "mr-2 h-4 w-4",
                            selectedMeasurement === measurement
                              ? "opacity-100"
                              : "opacity-0"
                          )}
                        />
                        <span className="block overflow-hidden text-ellipsis whitespace-nowrap">
                          {measurement.replace("urn:ngsi-ld:", "")}
                        </span>
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>
        </div>
        <div>
          <Button
            className="mt-4"
            onClick={handleShiftLeft}
            variant="outline"
            size="icon"
          >
            <ChevronLeft />
          </Button>
          <Button
            className="mt-4"
            onClick={handleShiftRight}
            variant="outline"
            size="icon"
          >
            <ChevronRight />
          </Button>
        </div>
        <div>
          <Button className="mt-4" onClick={resetZoom} disabled={false}>
            Reset
          </Button>
        </div>
      </CardHeader>

      <CardContent className="p-4 pl-0">
        <ChartContainer
          className="h-[400px] w-full"
          config={chartConfig}
          ref={chartRef}
          style={{ touchAction: "none" }}
        >
          <LineChart
            data={zoomedData}
            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            onMouseDown={handleMouseClickHold}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseClickRelease}
            onMouseLeave={handleMouseClickRelease}
          >
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="time_as_number"
              scale="time"
              domain={["dataMin", "dataMax"]}
              type="number"
              tickCount={getOptimalTickCount(zoomedData)}
              minTickGap={50} // More space between ticks
              tickFormatter={getSmartDateFormatter(zoomedData)}
              xAxisId="0"
            />
            <YAxis domain={yDomain} allowDataOverflow={false} scale="linear" />

            <ChartTooltip
              content={
                <ChartTooltipContent
                  labelFormatter={(value, payload) => {
                    const dataPoint = payload?.[0]?.payload;
                    if (dataPoint?.time_as_number) {
                      return new Date(dataPoint.time_as_number).toLocaleString(
                        "de-DE",
                        {
                          day: "2-digit",
                          month: "short",
                          year: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        }
                      );
                    }
                    return "Invalid Date";
                  }}
                />
              }
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="value"
              stroke={chartConfig.value.color}
              strokeWidth={2}
              dot={false}
              name={chartConfig.value.label}
              xAxisId="0"
            />
            {zoomedData.some((point) => "value_pred" in point) && (
              <Line
                type="monotone"
                dataKey="value_pred"
                stroke={chartConfig.value_pred.color}
                strokeWidth={2}
                dot={false}
                name={chartConfig.value_pred.label}
                xAxisId="0"
              />
            )}
            {selectedTemplates.map((template, idx) => (
              <Line
                key={template}
                type="monotone"
                dataKey={`value_${template}`}
                stroke={`hsl(var(--chart-${idx + 3}))`}
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
                name={template}
                xAxisId="0"
              />
            ))}
            {refAreaLeft && refAreaRight && (
              <ReferenceArea
                x1={refAreaLeft}
                x2={refAreaRight}
                strokeOpacity={0.3}
                fillOpacity={0.5}
              />
            )}
          </LineChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}

export default LineChartCard;
