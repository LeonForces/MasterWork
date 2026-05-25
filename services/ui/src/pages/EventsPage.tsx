import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

type EventItem = {
  event_id: string;
  camera_id: string;
  track_id: string;
  rule_id: string | null;
  event_type: string;
  severity: string;
  occurred_at: string;
  confidence: number;
  snapshot_path: string | null;
  dedup_key: string;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  attributes: {
    object_class?: string;
    bbox?: number[];
    track_confidence?: number;
  };
};

export function EventsPage() {
  const navigate = useNavigate();
  const [events, setEvents] = useState<EventItem[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [acknowledging, setAcknowledging] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  async function load() {
    const response = await api.get<EventItem[]>("/api/v1/events?limit=200");
    setEvents(response.data);
    setSelectedEventId((current) => current ?? response.data[0]?.event_id ?? null);
  }

  useEffect(() => {
    load().catch(() => undefined);
    const timer = setInterval(() => {
      load().catch(() => undefined);
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  const selectedEvent = useMemo(
    () => events.find((event) => event.event_id === selectedEventId) ?? events[0],
    [events, selectedEventId]
  );
  const isAcknowledged = Boolean(selectedEvent?.acknowledged_at);

  function replaceEvent(nextEvent: EventItem) {
    setEvents((current) => current.map((event) => (event.event_id === nextEvent.event_id ? nextEvent : event)));
  }

  function getFilename(contentDisposition: string | undefined, fallback: string) {
    if (!contentDisposition) {
      return fallback;
    }
    const match = /filename="?([^";]+)"?/i.exec(contentDisposition);
    return match?.[1] ?? fallback;
  }

  async function acknowledgeSelected() {
    if (!selectedEvent || isAcknowledged || acknowledging) {
      return;
    }
    setAcknowledging(true);
    setActionError(null);
    try {
      const response = await api.patch<EventItem>(`/api/v1/events/${selectedEvent.event_id}/ack`, {});
      replaceEvent(response.data);
    } catch {
      setActionError("Could not acknowledge the event. Check API availability and permissions.");
    } finally {
      setAcknowledging(false);
    }
  }

  async function exportSelectedEvidence() {
    if (!selectedEvent || exporting) {
      return;
    }
    setExporting(true);
    setActionError(null);
    try {
      const response = await api.get<Blob>(`/api/v1/events/${selectedEvent.event_id}/evidence`, {
        responseType: "blob"
      });
      const blob = response.data;
      const fallback = `event-${selectedEvent.event_id}.json`;
      const filename = getFilename(response.headers["content-disposition"], fallback);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      setActionError("Could not export evidence from the API.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <h2>Incident triage</h2>
          <p className="muted">Prioritize events, inspect evidence, and mark operator acknowledgement.</p>
        </div>
      </div>
      <section className="triage-layout">
        <aside className="card triage-queue-panel">
          <div className="section-heading">
            <div>
              <h3>Incident queue</h3>
              <p>{events.length} events loaded</p>
            </div>
          </div>
          <div className="incident-list">
            {events.map((event) => (
              <button
                className={[
                  "incident-item",
                  event.event_id === selectedEvent?.event_id ? "active" : "",
                  event.acknowledged_at ? "acknowledged" : ""
                ]
                  .filter(Boolean)
                  .join(" ")}
                key={event.event_id}
                onClick={() => setSelectedEventId(event.event_id)}
                type="button"
              >
                <span>{new Date(event.occurred_at).toLocaleTimeString()}</span>
                <strong>{event.event_type}</strong>
                <small>{event.camera_id}</small>
                {event.acknowledged_at && <em>Ack</em>}
              </button>
            ))}
            {events.length === 0 && <p className="muted">No incidents loaded.</p>}
          </div>
        </aside>
        <main className="card triage-detail-panel">
          {selectedEvent ? (
            <>
              <div className="triage-title">
                <div>
                  <h3>{selectedEvent.event_type} confirmed</h3>
                  <p>
                    Track {selectedEvent.track_id} on {selectedEvent.camera_id} with{" "}
                    {selectedEvent.confidence.toFixed(2)} model confidence.
                  </p>
                </div>
                <span className={`severity-pill severity-${selectedEvent.severity.toLowerCase()}`}>
                  {selectedEvent.severity}
                </span>
              </div>
              <div className="evidence-canvas">
                <div className="evidence-grid" />
                <div className="evidence-band" />
                <div className="evidence-bbox">
                  <span>{selectedEvent.attributes.object_class ?? "object"} {Math.round(selectedEvent.confidence * 100)}%</span>
                </div>
              </div>
              <div className="triage-actions">
                <button disabled={isAcknowledged || acknowledging} onClick={acknowledgeSelected} type="button">
                  {isAcknowledged ? "Acknowledged" : acknowledging ? "Acknowledging..." : "Acknowledge"}
                </button>
                <button className="secondary" onClick={() => navigate("/rules")} type="button">
                  Create rule
                </button>
                <button className="secondary" disabled={exporting} onClick={exportSelectedEvidence} type="button">
                  {exporting ? "Exporting..." : "Export evidence"}
                </button>
              </div>
              {actionError && <p className="action-error">{actionError}</p>}
            </>
          ) : (
            <p className="muted">Select an incident to inspect evidence.</p>
          )}
        </main>
        <aside className="card evidence-panel">
          <h3>Evidence</h3>
          <div className="evidence-kv">
            <div>
              <span>Object</span>
              <strong>{selectedEvent?.attributes.object_class ?? "-"}</strong>
            </div>
            <div>
              <span>Track</span>
              <strong>{selectedEvent?.track_id ?? "-"}</strong>
            </div>
            <div>
              <span>Dedup key</span>
              <strong>{selectedEvent?.dedup_key ?? "-"}</strong>
            </div>
            <div>
              <span>Status</span>
              <strong>{isAcknowledged ? "acknowledged" : "open"}</strong>
            </div>
          </div>
        </aside>
      </section>
    </>
  );
}
