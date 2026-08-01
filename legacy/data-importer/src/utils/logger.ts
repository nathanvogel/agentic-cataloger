/**
 * Simple console logger with timestamp and log level formatting
 */

type LogLevel = "INFO" | "WARN" | "ERROR";

/**
 * Formats a log message with timestamp and log level
 */
function formatMessage(level: LogLevel, message: string): string {
  const timestamp = new Date().toISOString();
  return `[${timestamp}] [${level}] ${message}`;
}

/**
 * Logs an informational message
 */
export function info(message: string): void {
  console.log(formatMessage("INFO", message));
}

/**
 * Logs a warning message
 */
export function warn(message: string): void {
  console.warn(formatMessage("WARN", message));
}

/**
 * Logs an error message
 */
export function error(message: string, err?: Error): void {
  const fullMessage = err ? `${message}: ${err.message}` : message;
  console.error(formatMessage("ERROR", fullMessage));

  // Log stack trace if available
  if (err?.stack) {
    console.error(err.stack);
  }
}
