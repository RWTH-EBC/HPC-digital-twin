import { useEffect } from 'react';
import { useDashboardStore } from '@/stores/store';

/**
 * Hook to manage SSE connection lifecycle
 * Automatically connects on mount and disconnects on unmount
 */
export const useSSEConnection = () => {
    const { connectToSSE, disconnectSSE, sseConnected } = useDashboardStore();

    useEffect(() => {
        // Connect to SSE on mount
        connectToSSE();

        // Cleanup: disconnect on unmount
        return () => {
            disconnectSSE();
        };
    }, [connectToSSE, disconnectSSE]);

    return { sseConnected };
};
