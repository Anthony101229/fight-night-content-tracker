import { useEffect, useState } from "react";
import { Link } from "react-router";
import { api, type EventFilters } from "../api";
import { FootageChart } from "../components/FootageChart";
import { formatDate } from "../format";
import { useApi } from "../useApi";

type When = "all" | "upcoming" | "past";
const TABS: { value: When; label: string }[] = [
  { value: "all", label: "All" },
  { value: "upcoming", label: "Upcoming" },
  { value: "past", label: "Past" },
];

export function EventsPage() {
  const [when, setWhen] = useState<When>("all");
  const [search, setSearch] = useState("");
  const q = useDebounced(search, 300);

  const filters: EventFilters = { when: when === "all" ? undefined : when, q: q || undefined };
  const { data, error } = useApi(
    () => Promise.all([api.listEvents(filters), api.footageSummary(filters)]),
    [when, q],
  );
  const [events, summary] = data ?? [[], []];
  const summaryById = new Map(summary.map((row) => [row.event_id, row]));

  return (
    <>
      <div className="toolbar">
        <div className="tabs" role="group" aria-label="Show events">
          {TABS.map((tab) => (
            <button
              key={tab.value}
              className={tab.value === when ? "active" : ""}
              aria-pressed={tab.value === when}
              onClick={() => setWhen(tab.value)}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <input
          type="search"
          placeholder="Search events"
          aria-label="Search events by name"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {error && <p className="error">Could not load events: {error}</p>}
      {!data && !error && <p className="muted">Loading…</p>}

      {data && (
        <>
          <section className="card">
            <h2>Footage status by event</h2>
            <FootageChart rows={summary} />
          </section>

          <section className="card">
            <h2>Events ({events.length})</h2>
            {events.length === 0 ? (
              <p className="muted">No events match these filters.</p>
            ) : (
              <div className="table-scroll">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Event</th>
                      <th className="hide-narrow">Location</th>
                      <th className="num">Delivered</th>
                    </tr>
                  </thead>
                  <tbody>
                    {events.map((event) => {
                      const row = summaryById.get(event.id);
                      return (
                        <tr key={event.id}>
                          <td className="nowrap">{formatDate(event.date)}</td>
                          <td>
                            <Link to={`/events/${event.id}`}>{event.name}</Link>
                          </td>
                          <td className="muted hide-narrow">{event.location ?? "—"}</td>
                          <td className="num nowrap">
                            {row && row.total > 0 ? `${row.delivered} / ${row.total}` : "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </>
  );
}

/** Wait until the user stops typing before searching, instead of one request per key. */
function useDebounced(value: string, delayMs: number): string {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value.trim()), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}
