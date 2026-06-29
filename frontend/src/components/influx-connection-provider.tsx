"use client";

import { useInfluxConnection } from "@/hooks/useInfluxConnection";

const InfluxConnectionProvider = ({ children }: { children: React.ReactNode }) => {
  useInfluxConnection();

  return <>{children}</>;
};

export default InfluxConnectionProvider;
