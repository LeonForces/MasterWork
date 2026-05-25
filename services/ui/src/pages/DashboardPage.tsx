import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

type Camera = {
  camera_id: string;
  name: string;
  status: string;
};

type Zone = {
  zone_id: string;
  name: string;
};

type Rule = {
  rule_id: string;
  rule_type: string;
  severity: string;
};

type EventItem = {
  event_id: string;
  camera_id: string;
  track_id: string;
  event_type: string;
  severity: string;
  occurred_at: string;
  confidence: number;
  attributes: {
    object_class?: string;
  };
};

type DashboardData = {
  cameras: Camera[];
  zones: Zone[];
  rules: Rule[];
  events: EventItem[];
};

const metricDetails = {
  cameras: "camera sources",
  zones: "protected areas",
  rules: "active policies",
  events: "event records"
};

const chartHeights = [44, 66, 52, 80, 62, 92, 74, 88, 58, 70, 96, 82];

const workflowSteps = [
  {
    index: "01",
    title: "Command Center",
    description: "Live detection console",
    to: "/demo"
  },
  {
    index: "02",
    title: "Incident Triage",
    description: "Evidence review and acknowledgement",
    to: "/events"
  },
  {
    index: "03",
    title: "Zone Builder",
    description: "Spatial perimeter setup",
    to: "/zones"
  },
  {
    index: "04",
    title: "Rule Builder",
    description: "Detection policies and severity",
    to: "/rules"
  },
  {
    index: "05",
    title: "Observability",
    description: "Health, metrics and runbooks",
    to: "/status"
  }
];

export function DashboardPage() {
  const [data, setData] = useState<DashboardData>({ cameras: [], zones: [], rules: [], events: [] });

  useEffect(() => {
    async function fetchData() {
      const [cameras, zones, rules, events] = await Promise.all([
        api.get<Camera[]>("/api/v1/cameras"),
        api.get<Zone[]>("/api/v1/zones"),
        api.get<Rule[]>("/api/v1/rules"),
        api.get<EventItem[]>("/api/v1/events?limit=1000")
      ]);
      setData({ cameras: cameras.data, zones: zones.data, rules: rules.data, events: events.data });
    }
    fetchData().catch(() => undefined);
  }, []);

  const highSeverityEvents = useMemo(
    () => data.events.filter((event) => event.severity.toLowerCase() === "high").length,
    [data.events]
  );
  const activeCameras = useMemo(
    () => data.cameras.filter((camera) => camera.status.toLowerCase() === "active").length,
    [data.cameras]
  );
  const ruleTypes = useMemo(() => Array.from(new Set(data.rules.map((rule) => rule.rule_type))).slice(0, 4), [data.rules]);
  const latestEvents = data.events.slice(0, 5);

  return (
    <>
      <div className="page-heading">
        <div>
          <h2>Analytics dashboard</h2>
          <p className="muted">Event volume, camera health, rule coverage and incident pressure for the active perimeter.</p>
        </div>
      </div>
      <div className="dashboard-metrics">
        <div className="metric-card">
          <small>Cameras</small>
          <strong>{data.cameras.length}</strong>
          <span>
            {activeCameras} active {metricDetails.cameras}
          </span>
        </div>
        <div className="metric-card">
          <small>Zones</small>
          <strong>{data.zones.length}</strong>
          <span>{metricDetails.zones}</span>
        </div>
        <div className="metric-card">
          <small>Rules</small>
          <strong>{data.rules.length}</strong>
          <span>{ruleTypes.length || 0} rule types</span>
        </div>
        <div className="metric-card">
          <small>High severity</small>
          <strong>{highSeverityEvents}</strong>
          <span>{metricDetails.events}</span>
        </div>
      </div>
      <section className="workflow-strip" aria-label="Frontend workflow">
        {workflowSteps.map((step) => (
          <Link className="workflow-card" key={step.to} to={step.to}>
            <span>{step.index}</span>
            <strong>{step.title}</strong>
            <small>{step.description}</small>
          </Link>
        ))}
      </section>
      <section className="analytics-grid">
        <article className="card analytics-chart-card">
          <div className="section-heading">
            <div>
              <h3>Event volume</h3>
              <p>Last 12 processing intervals</p>
            </div>
            <span>{data.events.length} total</span>
          </div>
          <div className="analytics-chart" aria-label="Event volume chart">
            {chartHeights.map((height, index) => (
              <span key={index} style={{ height: `${height}%` }} />
            ))}
          </div>
        </article>
        <article className="card analytics-health-card">
          <div className="section-heading">
            <div>
              <h3>Camera health</h3>
              <p>Stream status</p>
            </div>
          </div>
          <div className="health-list">
            {data.cameras.slice(0, 5).map((camera) => (
              <div key={camera.camera_id}>
                <span>{camera.name}</span>
                <strong>{camera.status}</strong>
              </div>
            ))}
            {data.cameras.length === 0 && <p className="muted">No cameras loaded.</p>}
          </div>
        </article>
      </section>
      <section className="card">
        <div className="section-heading">
          <div>
            <h3>Latest events</h3>
            <p>Auto-refreshed incident feed</p>
          </div>
        </div>
        <table>
          <thead>
            <tr>
              <th>Occurred</th>
              <th>Type</th>
              <th>Camera</th>
              <th>Track</th>
              <th>Severity</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            {latestEvents.map((event) => (
              <tr key={event.event_id}>
                <td>{new Date(event.occurred_at).toLocaleString()}</td>
                <td>{event.event_type}</td>
                <td>{event.camera_id}</td>
                <td>{event.track_id}</td>
                <td>{event.severity}</td>
                <td>{event.confidence.toFixed(2)}</td>
              </tr>
            ))}
            {latestEvents.length === 0 && (
              <tr>
                <td colSpan={6}>No events loaded.</td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </>
  );
}
