import { NextRequest, NextResponse } from "next/server";
import { getBackendUrl } from "./backend-url";

/** Single attempt — client retries in separate invocations to avoid Vercel timeout. */
export async function proxyToBackend(
  request: NextRequest,
  backendPath: string
): Promise<NextResponse> {
  const backend = getBackendUrl();
  if (!backend) {
    return NextResponse.json(
      {
        detail:
          "BILLGUARD_API_URL not set on Vercel. Add your Railway URL in Environment Variables.",
      },
      { status: 503 }
    );
  }
  const url = `${backend}${backendPath}${request.nextUrl.search}`;

  const headers = new Headers();
  const requestContentType = request.headers.get("content-type");
  if (requestContentType) headers.set("Content-Type", requestContentType);
  const accept = request.headers.get("accept");
  if (accept) headers.set("Accept", accept);

  const init: RequestInit = { method: request.method, headers };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.arrayBuffer();
  }

  try {
    const upstream = await fetch(url, {
      ...init,
      signal: AbortSignal.timeout(55_000),
    });

    const upstreamContentType = upstream.headers.get("content-type") || "";
    if (upstreamContentType.includes("text/html")) {
      return NextResponse.json(
        {
          detail: "Backend returned an error page. Check Railway deployment logs.",
          waking: true,
        },
        { status: 502 }
      );
    }

    const responseHeaders = new Headers();
    if (upstreamContentType) responseHeaders.set("Content-Type", upstreamContentType);
    responseHeaders.set("Cache-Control", "no-cache");

    return new NextResponse(upstream.body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch {
    return NextResponse.json(
      {
        detail: "Server is waking up — retrying automatically…",
        waking: true,
      },
      { status: 503 }
    );
  }
}
