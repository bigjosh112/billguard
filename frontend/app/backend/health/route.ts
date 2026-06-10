import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/proxy";

export const maxDuration = 60;

export async function GET(request: NextRequest) {
  return proxyToBackend(request, "/health");
}
