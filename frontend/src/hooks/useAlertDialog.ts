/**
 * Custom hook for managing alert dialog state
 * Handles alert visibility, messages, countdown, and error states
 */

import { useState } from "react";

export const useAlertDialog = () => {
  const [alertBoxOpen, setAlertBoxOpen] = useState(false);
  const [templateCreationError, setTemplateCreationError] = useState(false);
  const [alertMessage, setAlertMessage] = useState<React.ReactNode>("");
  const [countdown, setCountdown] = useState(5);

  /**
   * Show error alert with custom message
   */
  const showError = (message: React.ReactNode) => {
    setAlertMessage(message);
    setTemplateCreationError(true);
    setAlertBoxOpen(true);
  };

  /**
   * Show success alert with countdown
   */
  const showSuccess = (message: React.ReactNode, countdownSeconds: number = 5) => {
    setAlertMessage(message);
    setTemplateCreationError(false);
    setAlertBoxOpen(true);

    let count = countdownSeconds;
    setCountdown(count);

    const intervalId = setInterval(() => {
      count--;
      setCountdown(count);
      if (count <= 0) {
        clearInterval(intervalId);
        setAlertBoxOpen(false);
      }
    }, 1000);
  };

  return {
    alertBoxOpen,
    setAlertBoxOpen,
    templateCreationError,
    setTemplateCreationError,
    alertMessage,
    setAlertMessage,
    countdown,
    setCountdown,
    showError,
    showSuccess,
  };
};
