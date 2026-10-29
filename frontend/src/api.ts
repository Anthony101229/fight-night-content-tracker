// Small typed wrapper around the FastAPI endpoints. Vite proxies /api to the backend.

import type {
  CrewAssignment,
  CrewMember,
  CrewRole,
  Event,
  EventDetail,
  Footage,
  FootageStatus,
  FootageSummary,
} from "./types";

export interface EventFilters {
  when?: "upcoming" | "past";
  q?: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    // FastAPI puts a readable message in "detail" for 404/409 errors.
    const detail = typeof body?.detail === "string" ? body.detail : null;
    throw new Error(detail ?? `Request failed (${response.status})`);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

function queryString(filters: EventFilters): string {
  const params = new URLSearchParams();
  if (filters.when) params.set("when", filters.when);
  if (filters.q) params.set("q", filters.q);
  const text = params.toString();
  return text ? `?${text}` : "";
}

export const api = {
  listEvents: (filters: EventFilters) => request<Event[]>(`/events${queryString(filters)}`),

  footageSummary: (filters: EventFilters) =>
    request<FootageSummary[]>(`/footage/summary${queryString(filters)}`),

  getEvent: (id: number) => request<EventDetail>(`/events/${id}`),

  listCrew: () => request<CrewMember[]>("/crew-members"),

  assignCrew: (eventId: number, crewMemberId: number, role: CrewRole) =>
    request<CrewAssignment>(`/events/${eventId}/crew`, {
      method: "POST",
      body: JSON.stringify({ crew_member_id: crewMemberId, role }),
    }),

  unassignCrew: (eventId: number, crewMemberId: number) =>
    request<void>(`/events/${eventId}/crew/${crewMemberId}`, { method: "DELETE" }),

  updateFootageStatus: (boutId: number, status: FootageStatus) =>
    request<Footage>(`/bouts/${boutId}/footage`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
};
