import { useState } from "react";
import { Link, useParams } from "react-router";
import { api } from "../api";
import { capitalize, formatDate } from "../format";
import { usePalette } from "../palette";
import {
  CARD_POSITION_LABELS,
  CREW_ROLES,
  FOOTAGE_STATUSES,
  type Bout,
  type CardPosition,
  type CrewMember,
  type CrewRole,
  type EventDetail,
  type Fighter,
  type FootageStatus,
} from "../types";
import { useApi } from "../useApi";

export function EventDetailPage() {
  const eventId = Number(useParams().id);
  const { data, error, setData } = useApi(
    () => Promise.all([api.getEvent(eventId), api.listCrew()]),
    [eventId],
  );

  if (error) return <p className="error">Could not load event: {error}</p>;
  if (!data) return <p className="muted">Loading…</p>;

  const [event, crew] = data;
  // Child components send their changes up through this, so the page re-renders.
  const updateEvent = (change: (event: EventDetail) => EventDetail) =>
    setData((current) => current && [change(current[0]), current[1]]);

  const delivered = event.bouts.filter((b) => b.footage?.status === "delivered").length;

  return (
    <>
      <Link to="/" className="back">
        ← All events
      </Link>
      <header className="event-header">
        <h1>{event.name}</h1>
        <p className="muted">
          {formatDate(event.date)}
          {event.location && ` · ${event.location}`} ·{" "}
          <a href={event.source_url} target="_blank" rel="noreferrer">
            Wikipedia
          </a>
        </p>
        <p>
          <strong>{delivered}</strong> of {event.bouts.length} bouts delivered
        </p>
      </header>

      <CrewSection event={event} crew={crew} updateEvent={updateEvent} />
      <FightCard event={event} updateEvent={updateEvent} />
    </>
  );
}

type UpdateEvent = (change: (event: EventDetail) => EventDetail) => void;

function CrewSection({
  event,
  crew,
  updateEvent,
}: {
  event: EventDetail;
  crew: CrewMember[];
  updateEvent: UpdateEvent;
}) {
  const assignedIds = new Set(event.crew_assignments.map((a) => a.crew_member.id));
  const available = crew.filter((member) => !assignedIds.has(member.id));
  const [memberId, setMemberId] = useState("");
  const [role, setRole] = useState<CrewRole>("camera");
  const [error, setError] = useState<string | null>(null);

  function chooseMember(id: string) {
    setMemberId(id);
    const member = crew.find((m) => m.id === Number(id));
    if (member) setRole(member.role); // default to their usual role
  }

  async function assign() {
    setError(null);
    try {
      const assignment = await api.assignCrew(event.id, Number(memberId), role);
      updateEvent((e) => ({ ...e, crew_assignments: [...e.crew_assignments, assignment] }));
      setMemberId("");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function unassign(crewMemberId: number) {
    setError(null);
    try {
      await api.unassignCrew(event.id, crewMemberId);
      updateEvent((e) => ({
        ...e,
        crew_assignments: e.crew_assignments.filter((a) => a.crew_member.id !== crewMemberId),
      }));
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <section className="card">
      <h2>Crew</h2>
      {event.crew_assignments.length === 0 ? (
        <p className="muted">No crew assigned yet.</p>
      ) : (
        <ul className="crew-list">
          {event.crew_assignments.map((a) => (
            <li key={a.id}>
              <span>
                {a.crew_member.name} <span className="muted">· {a.role}</span>
              </span>
              <button className="link-button" onClick={() => unassign(a.crew_member.id)}>
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}

      {available.length > 0 && (
        <div className="assign-form">
          <select
            aria-label="Crew member"
            value={memberId}
            onChange={(e) => chooseMember(e.target.value)}
          >
            <option value="">Choose crew member…</option>
            {available.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name} ({m.role})
              </option>
            ))}
          </select>
          <select
            aria-label="Role at this event"
            value={role}
            onChange={(e) => setRole(e.target.value as CrewRole)}
          >
            {CREW_ROLES.map((r) => (
              <option key={r} value={r}>
                {capitalize(r)}
              </option>
            ))}
          </select>
          <button onClick={assign} disabled={!memberId}>
            Assign
          </button>
        </div>
      )}
      {error && <p className="error">{error}</p>}
    </section>
  );
}

function FightCard({ event, updateEvent }: { event: EventDetail; updateEvent: UpdateEvent }) {
  const [error, setError] = useState<string | null>(null);
  const positions = Object.keys(CARD_POSITION_LABELS) as CardPosition[];

  async function changeStatus(bout: Bout, status: FootageStatus) {
    const previous = bout.footage?.status ?? "planned";
    const setStatus = (value: FootageStatus) =>
      updateEvent((e) => ({
        ...e,
        bouts: e.bouts.map((b) =>
          b.id === bout.id && b.footage ? { ...b, footage: { ...b.footage, status: value } } : b,
        ),
      }));

    // Show the change immediately; put it back if the save fails.
    setError(null);
    setStatus(status);
    try {
      await api.updateFootageStatus(bout.id, status);
    } catch (err) {
      setStatus(previous);
      setError(`Could not save status: ${(err as Error).message}`);
    }
  }

  if (event.bouts.length === 0) {
    return (
      <section className="card">
        <h2>Fight card</h2>
        <p className="muted">No bouts announced yet.</p>
      </section>
    );
  }

  return (
    <section className="card">
      <h2>Fight card</h2>
      {error && <p className="error">{error}</p>}
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th className="hide-narrow">Weight class</th>
              <th>Bout</th>
              <th>Footage</th>
            </tr>
          </thead>
          {positions.map((position) => {
            const bouts = event.bouts.filter((b) => b.card_position === position);
            if (bouts.length === 0) return null;
            return (
              <tbody key={position}>
                <tr className="group-row">
                  <th colSpan={3}>{CARD_POSITION_LABELS[position]}</th>
                </tr>
                {bouts.map((bout) => (
                  <BoutRow key={bout.id} bout={bout} onStatusChange={changeStatus} />
                ))}
              </tbody>
            );
          })}
        </table>
      </div>
    </section>
  );
}

function BoutRow({
  bout,
  onStatusChange,
}: {
  bout: Bout;
  onStatusChange: (bout: Bout, status: FootageStatus) => void;
}) {
  const palette = usePalette();
  const status = bout.footage?.status ?? "planned";
  const { red_fighter: red, blue_fighter: blue } = bout;

  return (
    <tr>
      <td className="muted nowrap hide-narrow">{bout.weight_class ?? "—"}</td>
      <td>
        <FighterName fighter={red} />
        <span className="vs"> vs </span>
        <FighterName fighter={blue} />
        {bout.result && <div className="result">{describeResult(bout)}</div>}
      </td>
      <td className="nowrap">
        <span className="swatch" style={{ background: palette.stages[status] }} />
        <select
          aria-label={`Footage status for ${red.name} vs ${blue.name}`}
          value={status}
          onChange={(e) => onStatusChange(bout, e.target.value as FootageStatus)}
        >
          {FOOTAGE_STATUSES.map((s) => (
            <option key={s} value={s}>
              {capitalize(s)}
            </option>
          ))}
        </select>
      </td>
    </tr>
  );
}

/** The record never splits across lines, e.g. "(21-" / "6-0)". */
function FighterName({ fighter }: { fighter: Fighter }) {
  return (
    <>
      {fighter.name}
      {fighter.record && <span className="muted nowrap"> ({fighter.record})</span>}
    </>
  );
}

function describeResult(bout: Bout): string {
  const detail = [bout.method, bout.round && `R${bout.round}`].filter(Boolean).join(", ");
  switch (bout.result) {
    case "red":
      return `${bout.red_fighter.name} won${detail && ` · ${detail}`}`;
    case "blue":
      return `${bout.blue_fighter.name} won${detail && ` · ${detail}`}`;
    case "draw":
      return detail || "Draw";
    default:
      return "No contest";
  }
}
