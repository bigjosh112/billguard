import { NextRequest, NextResponse } from "next/server";
import { getBackendUrl } from "./backend-url";

export async function proxyToBackend(
  request: NextRequest,
  backendPath: string
): Promise<NextResponse> {
  const backend = getBackendUrl();
  const url = `${backend}${backendPath}${request.nextUrl.search}`;

  const headers = new Headers();
  const requestContentType = request.headers.get("content-type");
  if (requestContentType) headers.set("Content-Type", requestContentType);
  const accept = request.headers.get("accept");
  if (accept) headers.set("Accept", accept);

  const init: RequestInit = {
    method: request.method,
    headers,
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.arrayBuffer();
  }

  let upstream: Response;
  try {
    upstream = await fetch(url, {
      ...init,
      // Render free tier can take 30s+ to wake up
      signal: AbortSignal.timeout(120_000),
    });
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Backend unreachable";
    return NextResponse.json(
      {
        detail: `Cannot reach backend at ${backend}. ${message}. ` +
          "If Render was sleeping, wait 30s and try again.",
      },
      { status: 502 }
    );
  }

  const upstreamContentType = upstream.headers.get("content-type") || "";
  if (upstreamContentType.includes("text/html")) {
    const html = await upstream.text();
    const isWrongApp =
      html.includes("Cannot POST") ||
      html.includes("Cannot GET") ||
      upstream.status === 404;
    return NextResponse.json(
      {
        detail: isWrongApp
          ? "Render backend is the wrong app (not BillGuard FastAPI). " +
            "Render dashboard → Blueprint Billguard → Manual Sync. " +
            "Service must use Python runtime, rootDir=backend."
          : `Backend returned HTML error (${upstream.status}). Check Render logs.`,
      },
      { status: 502 }
    );
  }

  const responseHeaders = new Headers();
  const upstreamType = upstream.headers.get("content-type");
  if (upstreamType) responseHeaders.set("Content-Type", upstreamType);
  responseHeaders.set("Cache-Control", "no-cache");

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}
