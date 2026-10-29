// TypeScript mirrors of the API's Pydantic schemas (backend/app/schemas.py).

export type FootageStatus = "planned" | "shot" | "edited" | "delivered";
export type CardPosition = "main" | "co_main" | "main_card" | "prelim";
export type CrewRole = "camera" | "producer" | "editor";

export const FOOTAGE_STATUSES: FootageStatus[] = ["planned", "shot", "edited", "delivered"];
export const CREW_ROLES: CrewRole[] = ["camera", "producer", "editor"];

export const CARD_POSITION_LABELS: Record<CardPosition, string> = {
  main: "Main event",
  co_main: "Co-main event",
  main_card: "Main card",
  prelim: "Prelims",
};

export interface Fighter {
  id: number;
  name: string;
  nickname: string | null;
  record: string | null;
  weight_class: string | null;
}

export interface Footage {
  bout_id: number;
  status: FootageStatus;
  notes: string | null;
  updated_at: string;
}

export interface Bout {
  id: number;
  weight_class: string | null;
  card_position: CardPosition;
  red_fighter: Fighter;
  blue_fighter: Fighter;
  result: "red" | "blue" | "draw" | "no_contest" | null;
  method: string | null;
  round: number | null;
  footage: Footage | null;
}

export interface CrewMember {
  id: number;
  name: string;
  role: CrewRole;
}

export interface CrewAssignment {
  id: number;
  role: CrewRole;
  crew_member: CrewMember;
}

export interface Event {
  id: number;
  name: string;
  date: string; // "YYYY-MM-DD"
  location: string | null;
  source_url: string;
}

export interface EventDetail extends Event {
  bouts: Bout[];
  crew_assignments: CrewAssignment[];
}

export interface FootageSummary {
  event_id: number;
  event_name: string;
  event_date: string;
  total: number;
  planned: number;
  shot: number;
  edited: number;
  delivered: number;
  pending: number;
}
