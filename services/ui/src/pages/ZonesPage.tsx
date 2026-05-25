import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";

type Camera = { camera_id: string; name: string };
type Zone = { zone_id: string; camera_id: string; name: string; zone_type: string };

export function ZonesPage() {
  const { user } = useAuth();
  const canEdit = !!user && (user.roles.includes("admin") || user.roles.includes("operator"));

  const [cameras, setCameras] = useState<Camera[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [cameraId, setCameraId] = useState("");
  const [zoneName, setZoneName] = useState("zone-a");
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);

  async function load() {
    const [camerasRes, zonesRes] = await Promise.all([api.get<Camera[]>("/api/v1/cameras"), api.get<Zone[]>("/api/v1/zones")]);
    setCameras(camerasRes.data);
    setZones(zonesRes.data);
    if (!cameraId && camerasRes.data.length > 0) {
      setCameraId(camerasRes.data[0].camera_id);
    }
    setSelectedZoneId((current) => current ?? zonesRes.data[0]?.zone_id ?? null);
  }

  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    await api.post("/api/v1/zones", {
      camera_id: cameraId,
      name: zoneName,
      zone_type: "polygon",
      geometry: {
        points: [
          [100, 100],
          [300, 100],
          [300, 300],
          [100, 300]
        ]
      }
    });
    await load();
  }

  const selectedZone = useMemo(
    () => zones.find((zone) => zone.zone_id === selectedZoneId) ?? zones[0],
    [selectedZoneId, zones]
  );
  const zonesForCamera = useMemo(() => zones.filter((zone) => zone.camera_id === cameraId), [cameraId, zones]);

  return (
    <>
      <div className="page-heading">
        <div>
          <h2>Zone builder</h2>
          <p className="muted">Design spatial areas over the video field and prepare them for perimeter rules.</p>
        </div>
      </div>
      <section className="builder-layout">
        <aside className="card builder-list-panel">
          <div className="section-heading">
            <div>
              <h3>Zones</h3>
              <p>{zones.length} configured</p>
            </div>
          </div>
          <div className="builder-list">
            {zones.map((zone) => (
              <button
                className={zone.zone_id === selectedZone?.zone_id ? "builder-list-item active" : "builder-list-item"}
                key={zone.zone_id}
                onClick={() => setSelectedZoneId(zone.zone_id)}
                type="button"
              >
                <strong>{zone.name}</strong>
                <span>{zone.zone_type}</span>
              </button>
            ))}
            {zones.length === 0 && <p className="muted">No zones yet.</p>}
          </div>
        </aside>
        <main className="card spatial-workspace">
          <div className="section-heading">
            <div>
              <h3>{selectedZone?.name ?? "Camera map"}</h3>
              <p>{selectedZone?.camera_id ?? cameraId ?? "Select a camera"}</p>
            </div>
            <div className="tool-strip">
              <button type="button">Polygon</button>
              <button className="secondary" type="button">Line</button>
              <button className="secondary" type="button">Dwell</button>
            </div>
          </div>
          <div className="spatial-canvas">
            <div className="spatial-canvas-grid" />
            <div className="spatial-zone spatial-zone-main">{selectedZone?.name ?? "zone"}</div>
            <div className="spatial-zone spatial-zone-line">line_cross</div>
            <span className="camera-pin camera-pin-a">cam-01</span>
            <span className="camera-pin camera-pin-b">cam-02</span>
            <span className="camera-pin camera-pin-c">drone</span>
          </div>
        </main>
        <aside className="card inspector-panel">
          <h3>Zone params</h3>
          {canEdit && (
            <form className="inspector-form" onSubmit={onCreate}>
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
                Zone name
                <input value={zoneName} onChange={(e) => setZoneName(e.target.value)} />
              </label>
              <button type="submit">Create zone</button>
            </form>
          )}
          <div className="evidence-kv">
            <div>
              <span>Selected</span>
              <strong>{selectedZone?.name ?? "-"}</strong>
            </div>
            <div>
              <span>Zones on camera</span>
              <strong>{zonesForCamera.length}</strong>
            </div>
            <div>
              <span>Geometry</span>
              <strong>{selectedZone?.zone_type ?? "polygon"}</strong>
            </div>
          </div>
        </aside>
      </section>
    </>
  );
}
