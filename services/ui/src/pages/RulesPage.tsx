import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";

type Camera = { camera_id: string; name: string };
type Zone = { zone_id: string; camera_id: string; name: string };
type Rule = { rule_id: string; camera_id: string; name: string; rule_type: string; severity: string };

export function RulesPage() {
  const { user } = useAuth();
  const canEdit = !!user && (user.roles.includes("admin") || user.roles.includes("operator"));

  const [cameras, setCameras] = useState<Camera[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [rules, setRules] = useState<Rule[]>([]);
  const [cameraId, setCameraId] = useState("");
  const [zoneId, setZoneId] = useState("");
  const [ruleType, setRuleType] = useState("zone_enter");
  const [selectedRuleId, setSelectedRuleId] = useState<string | null>(null);

  async function load() {
    const [camerasRes, zonesRes, rulesRes] = await Promise.all([
      api.get<Camera[]>("/api/v1/cameras"),
      api.get<Zone[]>("/api/v1/zones"),
      api.get<Rule[]>("/api/v1/rules")
    ]);
    setCameras(camerasRes.data);
    setZones(zonesRes.data);
    setRules(rulesRes.data);
    if (!cameraId && camerasRes.data.length > 0) {
      setCameraId(camerasRes.data[0].camera_id);
    }
    if (!zoneId && zonesRes.data.length > 0) {
      setZoneId(zonesRes.data[0].zone_id);
    }
    setSelectedRuleId((current) => current ?? rulesRes.data[0]?.rule_id ?? null);
  }

  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    const params =
      ruleType === "line_cross"
        ? { line: [[100, 200], [500, 200]], zone_id: zoneId }
        : ruleType === "dwell_time"
          ? { zone_id: zoneId, seconds: 5 }
          : { zone_id: zoneId };
    await api.post("/api/v1/rules", {
      camera_id: cameraId,
      name: `${ruleType}-${Date.now()}`,
      rule_type: ruleType,
      params,
      severity: "high",
      enabled: true
    });
    await load();
  }

  const selectedRule = useMemo(
    () => rules.find((rule) => rule.rule_id === selectedRuleId) ?? rules[0],
    [rules, selectedRuleId]
  );
  const zonesForCamera = useMemo(() => zones.filter((zone) => zone.camera_id === cameraId), [cameraId, zones]);
  const ruleStats = useMemo(
    () => ({
      high: rules.filter((rule) => rule.severity.toLowerCase() === "high").length,
      zoneEnter: rules.filter((rule) => rule.rule_type === "zone_enter").length,
      lineCross: rules.filter((rule) => rule.rule_type === "line_cross").length,
      dwellTime: rules.filter((rule) => rule.rule_type === "dwell_time").length
    }),
    [rules]
  );

  return (
    <>
      <div className="page-heading">
        <div>
          <h2>Rule builder</h2>
          <p className="muted">Compose perimeter policies from camera, zone, event type and severity settings.</p>
        </div>
      </div>
      <section className="rule-builder-grid">
        <article className="card rule-composer">
          <div className="section-heading">
            <div>
              <h3>Composer</h3>
              <p>Build a rule from a camera source and spatial target.</p>
            </div>
          </div>
          {canEdit ? (
            <form className="composer-form" onSubmit={onCreate}>
              <label>
                Camera
                <select value={cameraId} onChange={(e) => setCameraId(e.target.value)}>
                  {cameras.map((camera) => (
                    <option key={camera.camera_id} value={camera.camera_id}>
                      {camera.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Zone
                <select value={zoneId} onChange={(e) => setZoneId(e.target.value)}>
                  {zonesForCamera.map((zone) => (
                    <option key={zone.zone_id} value={zone.zone_id}>
                      {zone.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Trigger
                <select value={ruleType} onChange={(e) => setRuleType(e.target.value)}>
                  <option value="zone_enter">zone_enter</option>
                  <option value="line_cross">line_cross</option>
                  <option value="dwell_time">dwell_time</option>
                </select>
              </label>
              <button type="submit">Create rule</button>
            </form>
          ) : (
            <p className="muted">You need operator or admin role to create rules.</p>
          )}
        </article>
        <article className="card rule-stats">
          <h3>Policy coverage</h3>
          <div className="stat-stack">
            <div>
              <span>High severity</span>
              <strong>{ruleStats.high}</strong>
            </div>
            <div>
              <span>Zone enter</span>
              <strong>{ruleStats.zoneEnter}</strong>
            </div>
            <div>
              <span>Line cross</span>
              <strong>{ruleStats.lineCross}</strong>
            </div>
            <div>
              <span>Dwell time</span>
              <strong>{ruleStats.dwellTime}</strong>
            </div>
          </div>
        </article>
        <article className="card active-rule-panel">
          <div className="section-heading">
            <div>
              <h3>Active rules</h3>
              <p>{rules.length} configured</p>
            </div>
          </div>
          <div className="rule-list">
            {rules.map((rule) => (
              <button
                className={rule.rule_id === selectedRule?.rule_id ? "rule-list-item active" : "rule-list-item"}
                key={rule.rule_id}
                onClick={() => setSelectedRuleId(rule.rule_id)}
                type="button"
              >
                <strong>{rule.name}</strong>
                <span>{rule.rule_type}</span>
                <small>{rule.severity}</small>
              </button>
            ))}
            {rules.length === 0 && <p className="muted">No rules configured.</p>}
          </div>
        </article>
      </section>
    </>
  );
}
