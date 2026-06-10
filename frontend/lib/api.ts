import { getSessionId } from "./session";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Transaction {
  _id: string;
  date: string;
  description: string;
  amount: number;
  type: "debit" | "credit";
  balance: number;
  category: string;
  bank: string;
  currency: string;
  reference: string;
}

export interface Bill {
  _id: string;
  name: string;
  amount: number;
  due_date: string;
  category: string;
  currency: string;
  paid?: boolean;
  paid_at?: string;
}

export interface Salary {
  _id?: string;
  amount: number;
  pay_date: string;
  currency: string;
}

export interface CategorySpending {
  category: string;
  total: number;
  transactions: number;
}

export interface FinancialSummary {
  period: string;
  total_inflow: number;
  total_outflow: number;
  net: number;
  spending_by_category: CategorySpending[];
  upcoming_bills: Bill[];
  total_bills_due: number;
  salary: Salary | null;
  total_transactions_stored: number;
  generated_at: string;
}

export interface ChatStreamEvent {
  type: "status" | "tool_call" | "tool_result" | "text" | "done" | "error";
  phase?: string;
  message?: string;
  tool?: string;
  result_summary?: string;
  content?: string;
}

export interface BillInput {
  name: string;
  amount: number;
  due_date: string;
  category: string;
  currency?: string;
}

export interface SalaryInput {
  amount: number;
  pay_date: string;
  currency?: string;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || "Request failed");
  }
  return response.json();
}

export async function checkHealth(): Promise<{ status: string; service: string }> {
  const res = await fetch(`${API_URL}/health`);
  return handleResponse(res);
}

export async function uploadStatement(file: File): Promise<{
  success: boolean;
  transactions_imported: number;
  message: string;
}> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("session_id", getSessionId());
  const res = await fetch(`${API_URL}/api/upload-statement`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(res);
}

export async function getBills(includePaid = false): Promise<{ bills: Bill[] }> {
  const params = new URLSearchParams({ session_id: getSessionId() });
  if (includePaid) params.set("include_paid", "true");
  const res = await fetch(`${API_URL}/api/bills?${params}`);
  return handleResponse(res);
}

export async function markBillPaid(billId: string): Promise<{ success: boolean }> {
  const res = await fetch(
    `${API_URL}/api/bills/${billId}/paid?session_id=${getSessionId()}`,
    { method: "PATCH" }
  );
  return handleResponse(res);
}

export async function addBill(bill: BillInput): Promise<{ success: boolean; bill_id: string }> {
  const res = await fetch(`${API_URL}/api/bills`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ currency: "NGN", session_id: getSessionId(), ...bill }),
  });
  return handleResponse(res);
}

export async function deleteBill(billId: string): Promise<{ success: boolean }> {
  const res = await fetch(
    `${API_URL}/api/bills/${billId}?session_id=${getSessionId()}`,
    { method: "DELETE" }
  );
  return handleResponse(res);
}

export async function setSalary(salary: SalaryInput): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${API_URL}/api/salary`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ currency: "NGN", session_id: getSessionId(), ...salary }),
  });
  return handleResponse(res);
}

export async function getSummary(): Promise<FinancialSummary> {
  const res = await fetch(`${API_URL}/api/summary?session_id=${getSessionId()}`);
  return handleResponse(res);
}

export async function getTransactions(
  limit = 50,
  category?: string
): Promise<{ transactions: Transaction[]; count: number }> {
  const params = new URLSearchParams({
    limit: String(limit),
    session_id: getSessionId(),
  });
  if (category) params.set("category", category);
  const res = await fetch(`${API_URL}/api/transactions?${params}`);
  return handleResponse(res);
}

export async function streamChat(
  message: string,
  sessionId: string,
  onEvent: (event: ChatStreamEvent) => void
): Promise<void> {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });

  if (!res.ok) {
    throw new Error("Chat request failed");
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response stream");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6).trim();
        if (data === "[DONE]") return;
        try {
          const event = JSON.parse(data) as ChatStreamEvent;
          onEvent(event);
        } catch {
          // skip malformed lines
        }
      }
    }
  }
}

export function formatNaira(amount: number): string {
  return `₦${amount.toLocaleString("en-NG", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

export { getSessionId, clearSession } from "./session";
