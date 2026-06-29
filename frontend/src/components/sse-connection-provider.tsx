"use client";

import { useSSEConnection } from "@/hooks/useSSEConnection";

const SSEConnectionProvider = ({ children }: { children: React.ReactNode }) => {
  useSSEConnection();

  return <>{children}</>;
};

export default SSEConnectionProvider;
