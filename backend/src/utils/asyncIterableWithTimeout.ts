/**
 * Wraps an async iterable and throws an error if the time between iterations
 * exceeds the specified timeout.
 *
 * @param iterable The async iterable to wrap.
 * @param timeoutMs The timeout in milliseconds.
 * @returns A new async iterable that will throw an error on timeout.
 */
export async function* withTimeout<T>(
  iterable: AsyncIterable<T>,
  timeoutMs: number,
): AsyncGenerator<T, void, unknown> {
  const iterator = iterable[Symbol.asyncIterator]();

  while (true) {
    let timeoutId: NodeJS.Timeout;

    const timeoutPromise = new Promise<never>((_, reject) => {
      timeoutId = setTimeout(() => {
        reject(new Error(`Async iteration timed out after ${timeoutMs}ms`));
      }, timeoutMs);
    });

    try {
      const result = await Promise.race([iterator.next(), timeoutPromise]);

      if (result.done) {
        return;
      }

      yield result.value;
    } finally {
      clearTimeout(timeoutId!);
    }
  }
}
