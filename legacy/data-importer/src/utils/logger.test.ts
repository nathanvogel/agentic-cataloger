import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { info, warn, error } from "./logger";

describe("logger", () => {
  let consoleLogSpy: ReturnType<typeof vi.spyOn>;
  let consoleWarnSpy: ReturnType<typeof vi.spyOn>;
  let consoleErrorSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    // Spy on console methods
    consoleLogSpy = vi.spyOn(console, "log").mockImplementation(() => {});
    consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    // Restore console methods
    consoleLogSpy.mockRestore();
    consoleWarnSpy.mockRestore();
    consoleErrorSpy.mockRestore();
  });

  describe("info", () => {
    it("should log info message with timestamp and level", () => {
      info("Test info message");

      expect(consoleLogSpy).toHaveBeenCalledOnce();
      const loggedMessage = consoleLogSpy.mock.calls[0][0];

      // Check format: [timestamp] [INFO] message
      expect(loggedMessage).toMatch(
        /^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z\] \[INFO\] Test info message$/
      );
    });

    it("should include ISO timestamp", () => {
      info("Test message");

      const loggedMessage = consoleLogSpy.mock.calls[0][0] as string;
      const timestampMatch = loggedMessage.match(
        /\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)\]/
      );

      expect(timestampMatch).toBeTruthy();
      expect(() => new Date(timestampMatch![1])).not.toThrow();
    });
  });

  describe("warn", () => {
    it("should log warning message with timestamp and level", () => {
      warn("Test warning message");

      expect(consoleWarnSpy).toHaveBeenCalledOnce();
      const loggedMessage = consoleWarnSpy.mock.calls[0][0];

      // Check format: [timestamp] [WARN] message
      expect(loggedMessage).toMatch(
        /^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z\] \[WARN\] Test warning message$/
      );
    });

    it("should include ISO timestamp", () => {
      warn("Test message");

      const loggedMessage = consoleWarnSpy.mock.calls[0][0] as string;
      const timestampMatch = loggedMessage.match(
        /\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)\]/
      );

      expect(timestampMatch).toBeTruthy();
      expect(() => new Date(timestampMatch![1])).not.toThrow();
    });
  });

  describe("error", () => {
    it("should log error message with timestamp and level", () => {
      error("Test error message");

      expect(consoleErrorSpy).toHaveBeenCalledOnce();
      const loggedMessage = consoleErrorSpy.mock.calls[0][0];

      // Check format: [timestamp] [ERROR] message
      expect(loggedMessage).toMatch(
        /^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z\] \[ERROR\] Test error message$/
      );
    });

    it("should include error details when Error object provided", () => {
      const testError = new Error("Something went wrong");
      error("Test error message", testError);

      expect(consoleErrorSpy).toHaveBeenCalledTimes(2);

      const loggedMessage = consoleErrorSpy.mock.calls[0][0];
      expect(loggedMessage).toMatch(
        /^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z\] \[ERROR\] Test error message: Something went wrong$/
      );
    });

    it("should log stack trace when Error object provided", () => {
      const testError = new Error("Something went wrong");
      error("Test error message", testError);

      expect(consoleErrorSpy).toHaveBeenCalledTimes(2);

      const stackTrace = consoleErrorSpy.mock.calls[1][0];
      expect(stackTrace).toContain("Error: Something went wrong");
      expect(stackTrace).toContain("at ");
    });

    it("should handle error without stack trace", () => {
      const testError = new Error("Something went wrong");
      delete testError.stack;

      error("Test error message", testError);

      // Should only log the message, not the stack
      expect(consoleErrorSpy).toHaveBeenCalledOnce();
    });

    it("should include ISO timestamp", () => {
      error("Test message");

      const loggedMessage = consoleErrorSpy.mock.calls[0][0] as string;
      const timestampMatch = loggedMessage.match(
        /\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)\]/
      );

      expect(timestampMatch).toBeTruthy();
      expect(() => new Date(timestampMatch![1])).not.toThrow();
    });
  });

  describe("timestamp format", () => {
    it("should use consistent timestamp format across all log levels", () => {
      info("Info message");
      warn("Warn message");
      error("Error message");

      const infoTimestamp = (consoleLogSpy.mock.calls[0][0] as string).match(
        /\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)\]/
      )?.[1];
      const warnTimestamp = (consoleWarnSpy.mock.calls[0][0] as string).match(
        /\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)\]/
      )?.[1];
      const errorTimestamp = (consoleErrorSpy.mock.calls[0][0] as string).match(
        /\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)\]/
      )?.[1];

      // All should be valid ISO timestamps
      expect(() => new Date(infoTimestamp!)).not.toThrow();
      expect(() => new Date(warnTimestamp!)).not.toThrow();
      expect(() => new Date(errorTimestamp!)).not.toThrow();
    });
  });
});
