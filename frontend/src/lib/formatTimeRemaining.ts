export function formatTimeRemaining(seconds: number): string {
  if (seconds <= 0) return "0 sec";

  const days = Math.floor(seconds / 86400);
  seconds %= 86400;

  const hours = Math.floor(seconds / 3600);
  seconds %= 3600;

  const minutes = Math.floor(seconds / 60);
  seconds %= 60;

  const parts: string[] = [];

  if (days > 0) parts.push(`${days} day${days !== 1 ? "s" : ""}`);
  if (hours > 0) parts.push(`${hours} hr${hours !== 1 ? "s" : ""}`);
  if (minutes > 0) parts.push(`${minutes} min${minutes !== 1 ? "s" : ""}`);
  if (seconds > 0) parts.push(`${seconds} sec${seconds !== 1 ? "s" : ""}`);

  return parts.join(" ");
}
