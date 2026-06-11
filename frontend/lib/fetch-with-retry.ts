/** Retry fetch when backend is cold-starting (can take 30–90s). */
export async function fetchWithRetry(
  url: string,
  init?: RequestInit,
  options?: { attempts?: number; timeoutMs?: number; onRetry?: (n: number) => void }
): Promise<Response> {
  const attempts = options?.attempts ?? 4;
  const timeoutMs = options?.timeoutMs ?? 90_000;

  let lastError: Error | null = null;

  for (let i = 0; i < attempts; i++) {
    if (i > 0) options?.onRetry?.(i);

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const res = await fetch(url, { ...init, signal: controller.signal });
      clearTimeout(timer);
      // Retry on 502/503/504 from our proxy (backend still waking)
      if (res.status >= 502 && res.status <= 504 && i < attempts - 1) {
        await sleep(10_000);
        continue;
      }
      return res;
    } catch (err) {
      clearTimeout(timer);
      lastError = err instanceof Error ? err : new Error("Request failed");
      if (i < attempts - 1) await sleep(10_000);
    }
  }

  throw lastError ?? new Error("Request failed after retries");
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

/** Ping backend until awake. Call on page load before user interacts. */
export async function wakeBackend(
  onProgress?: (msg: string) => void
): Promise<boolean> {
  if (typeof window === "undefined") return true;
  if (window.location.hostname === "localhost") return true;

  onProgress?.("Starting server…");

  for (let i = 0; i < 4; i++) {
    try {
      const res = await fetchWithRetry("/backend/health", undefined, {
        attempts: 1,
        timeoutMs: 60_000,
      });
      const data = await res.json().catch(() => ({}));
      if (data.service === "BillGuard") return true;
      onProgress?.(`Connecting… (${i + 1}/4)`);
    } catch {
      onProgress?.(`Starting server… (${i + 1}/4)`);
    }
    if (i < 3) await sleep(8000);
  }
  return false;
}

export function isWakeError(message: string): boolean {
  const m = message.toLowerCase();
  return (
    m.includes("timeout") ||
    m.includes("aborted") ||
    m.includes("cannot reach backend") ||
    m.includes("502") ||
    m.includes("503")
  );
}
