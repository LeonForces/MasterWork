import { useEffect, useState } from "react";
import { API_BASE_URL, api } from "../api";

type Health = { status: string };

export function StatusPage() {
  const [live, setLive] = useState<Health | null>(null);
  const [ready, setReady] = useState<Health | null>(null);
  const serviceMap = [
    { label: "API", status: live?.status ?? "n/a", detail: "REST and health checks" },
    { label: "Analytics worker", status: ready?.status ? "watch" : "n/a", detail: "Inference queue consumer" },
    { label: "Integration worker", status: ready?.status ? "watch" : "n/a", detail: "Webhook delivery queue" },
    { label: "Prometheus", status: "external", detail: "Metrics scrape target" },
    { label: "Grafana", status: "external", detail: "Dashboards and alert views" }
  ];
  const observabilityLinks = [
    { label: "API metrics", href: `${API_BASE_URL}/metrics`, meta: "Prometheus format" },
    { label: "Prometheus", href: "http://localhost:9090", meta: "Query and targets" },
    { label: "Grafana", href: "http://localhost:3000", meta: "Dashboards" },
    { label: "RabbitMQ", href: "http://localhost:15672", meta: "Queue management" },
    { label: "Webhook mock", href: "http://localhost:1080", meta: "Delivery inspection" }
  ];

  useEffect(() => {
    async function load() {
      const [liveRes, readyRes] = await Promise.all([api.get<Health>("/health/live"), api.get<Health>("/health/ready")]);
      setLive(liveRes.data);
      setReady(readyRes.data);
    }
    load().catch(() => undefined);
  }, []);

  return (
    <>
      <div className="page-heading">
        <div>
          <h2>Admin & observability</h2>
          <p className="muted">Health checks, metrics endpoints and service console links for production operations.</p>
        </div>
      </div>
      <section className="observability-grid">
        <article className="card status-card">
          <span className={live?.status ? "status-dot online" : "status-dot"} />
          <h3>API live</h3>
          <strong>{live?.status ?? "n/a"}</strong>
          <p>Process heartbeat and request routing.</p>
        </article>
        <article className="card status-card">
          <span className={ready?.status ? "status-dot online" : "status-dot"} />
          <h3>API ready</h3>
          <strong>{ready?.status ?? "n/a"}</strong>
          <p>Database connectivity and service readiness.</p>
        </article>
        <article className="card observability-links">
          <h3>Observability links</h3>
          {observabilityLinks.map((link) => (
            <a href={link.href} key={link.href} target="_blank" rel="noreferrer">
              <span>{link.label}</span>
              <small>{link.meta}</small>
            </a>
          ))}
        </article>
        <article className="card admin-runbook">
          <h3>Runbook</h3>
          <div className="runbook-list">
            <span>Check API readiness before creating cameras.</span>
            <span>Use Prometheus for worker scrape health.</span>
            <span>Use Grafana for trend dashboards and alerts.</span>
          </div>
        </article>
        <article className="card service-map-panel">
          <div className="section-heading">
            <div>
              <h3>Service map</h3>
              <p>Operational surface for the video analytics stack</p>
            </div>
          </div>
          <div className="service-map">
            {serviceMap.map((service) => (
              <div className="service-node" key={service.label}>
                <span>{service.status}</span>
                <strong>{service.label}</strong>
                <small>{service.detail}</small>
              </div>
            ))}
          </div>
        </article>
      </section>
    </>
  );
}
