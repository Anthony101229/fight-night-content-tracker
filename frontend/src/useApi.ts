import { useEffect, useState } from "react";

/**
 * Load data when the component mounts (and again whenever `deps` change).
 * Ignores late responses from an earlier request, so fast filter changes can't
 * show stale results.
 */
export function useApi<T>(load: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    load()
      .then((result) => !cancelled && setData(result))
      .catch((err: Error) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, deps);

  return { data, error, setData };
}
