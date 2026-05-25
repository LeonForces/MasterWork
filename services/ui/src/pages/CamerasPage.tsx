import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";

type Camera = {
  camera_id: string;
  name: string;
  rtsp_url: string;
  status: string;
  fps_target: number;
  resolution: string;
};

export function CamerasPage() {
  const { user } = useAuth();
  const canEdit = !!user && (user.roles.includes("admin") || user.roles.includes("operator"));

  const [items, setItems] = useState<Camera[]>([]);
  const [selectedCameraId, setSelectedCameraId] = useState<string | null>(null);
  const [name, setName] = useState("cam-01");
  const [rtspUrl, setRtspUrl] = useState("sample.mp4");

  async function load() {
    const response = await api.get<Camera[]>("/api/v1/cameras");
    setItems(response.data);
    setSelectedCameraId((current) => current ?? response.data[0]?.camera_id ?? null);
  }

  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    await api.post("/api/v1/cameras", {
      name,
      rtsp_url: rtspUrl,
      status: "active",
      fps_target: 10,
      resolution: "1280x720"
    });
    await load();
  }

  const selectedCamera = useMemo(
    () => items.find((item) => item.camera_id === selectedCameraId) ?? items[0],
    [items, selectedCameraId]
  );

  return (
    <>
      <div className="page-heading">
        <div>
          <h2>Camera administration</h2>
          <p className="muted">Register sources, inspect stream health and prepare feeds for analytics workers.</p>
        </div>
      </div>
      <section className="camera-admin-grid">
        {canEdit && (
          <article className="card camera-create-card">
            <div className="section-heading">
              <div>
                <h3>Create camera</h3>
                <p>Add RTSP or MP4 source</p>
              </div>
            </div>
            <form className="composer-form" onSubmit={onCreate}>
              <label>
                Camera name
                <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Camera name" />
              </label>
              <label>
                Source
                <input value={rtspUrl} onChange={(e) => setRtspUrl(e.target.value)} placeholder="RTSP/MP4 source" />
              </label>
              <button type="submit">Create camera</button>
            </form>
          </article>
        )}
        <article className="card camera-fleet-card">
          <div className="section-heading">
            <div>
              <h3>Fleet status</h3>
              <p>{items.length} sources configured</p>
            </div>
          </div>
          <div className="camera-card-grid">
            {items.slice(0, 6).map((item) => (
              <button
                className={item.camera_id === selectedCamera?.camera_id ? "camera-tile active" : "camera-tile"}
                key={item.camera_id}
                onClick={() => setSelectedCameraId(item.camera_id)}
                type="button"
              >
                <span>{item.status}</span>
                <strong>{item.name}</strong>
                <small>{item.resolution} · {item.fps_target} fps</small>
              </button>
            ))}
            {items.length === 0 && <p className="muted">No cameras loaded.</p>}
          </div>
        </article>
        <article className="card camera-detail-panel">
          <div className="section-heading">
            <div>
              <h3>Selected source</h3>
              <p>{selectedCamera?.camera_id ?? "No camera selected"}</p>
            </div>
            <span>{selectedCamera?.status ?? "n/a"}</span>
          </div>
          {selectedCamera ? (
            <div className="detail-grid">
              <div>
                <span>Name</span>
                <strong>{selectedCamera.name}</strong>
              </div>
              <div>
                <span>Source</span>
                <strong>{selectedCamera.rtsp_url}</strong>
              </div>
              <div>
                <span>Target FPS</span>
                <strong>{selectedCamera.fps_target}</strong>
              </div>
              <div>
                <span>Resolution</span>
                <strong>{selectedCamera.resolution}</strong>
              </div>
            </div>
          ) : (
            <p className="muted">Create or load a camera to inspect stream details.</p>
          )}
        </article>
      </section>
      <div className="card">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Source</th>
              <th>Status</th>
              <th>FPS</th>
              <th>Resolution</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.camera_id}>
                <td>{item.camera_id}</td>
                <td>{item.name}</td>
                <td>{item.rtsp_url}</td>
                <td>{item.status}</td>
                <td>{item.fps_target}</td>
                <td>{item.resolution}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
