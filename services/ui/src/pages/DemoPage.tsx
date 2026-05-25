import { useEffect, useMemo, useRef, useState } from "react";
import { API_BASE_URL, api } from "../api";

type Camera = {
  camera_id: string;
  name: string;
  rtsp_url: string;
  status: string;
  resolution: string;
};

type Track = {
  track_id: string;
  camera_id: string;
  object_class: string;
  started_at: string;
  last_seen_at: string;
  last_bbox: number[];
  state: {
    confidence?: number;
  };
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
    bbox?: number[];
    track_confidence?: number;
  };
};

type VideoSize = {
  width: number;
  height: number;
};

function isDemoCamera(camera: Camera): boolean {
  return camera.name.toLowerCase().includes("drone") || camera.rtsp_url.includes("V_DRONE_009.mp4");
}

function formatPercent(value: number | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "-";
  }
  return `${Math.round(value * 100)}%`;
}

export function DemoPage() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoError, setVideoError] = useState<string | null>(null);
  const [videoSize, setVideoSize] = useState<VideoSize>({ width: 640, height: 512 });
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [tracks, setTracks] = useState<Track[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);

  const demoCamera = useMemo(() => cameras.find(isDemoCamera) ?? cameras[0], [cameras]);
  const activeTracks = useMemo(() => {
    if (!demoCamera) {
      return [];
    }
    return tracks.filter((track) => track.camera_id === demoCamera.camera_id);
  }, [demoCamera, tracks]);
  const demoEvents = useMemo(() => {
    if (!demoCamera) {
      return [];
    }
    return events.filter((event) => event.camera_id === demoCamera.camera_id);
  }, [demoCamera, events]);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;

    async function loadVideo() {
      try {
        const response = await api.get<Blob>("/api/v1/demo/drone-video", { responseType: "blob" });
        if (cancelled) {
          return;
        }
        objectUrl = URL.createObjectURL(response.data);
        setVideoUrl(objectUrl);
        setVideoError(null);
      } catch (error) {
        if (!cancelled) {
          setVideoError("Demo video is not available from the API container.");
        }
      }
    }

    loadVideo();
    return () => {
      cancelled = true;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, []);

  useEffect(() => {
    async function loadData() {
      const [cameraResponse, trackResponse, eventResponse] = await Promise.all([
        api.get<Camera[]>("/api/v1/cameras"),
        api.get<Track[]>("/api/v1/tracks?object_class=drone&limit=50"),
        api.get<EventItem[]>("/api/v1/events?limit=100")
      ]);
      setCameras(cameraResponse.data);
      setTracks(trackResponse.data);
      setEvents(eventResponse.data);
    }

    loadData().catch(() => undefined);
    const timer = setInterval(() => {
      loadData().catch(() => undefined);
    }, 2000);
    return () => clearInterval(timer);
  }, []);

  function onMetadataLoaded() {
    const video = videoRef.current;
    if (!video) {
      return;
    }
    setVideoSize({
      width: video.videoWidth || 640,
      height: video.videoHeight || 512
    });
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <h2>Drone detection live console</h2>
          <p className="muted">YOLO pipeline monitoring, tracks, event stream and rule health in one operational view.</p>
        </div>
        <a className="button-link" href={`${API_BASE_URL}/docs`} target="_blank" rel="noreferrer">
          Open API docs
        </a>
      </div>

      <section className="demo-grid">
        <div className="card demo-video-card">
          <div className="demo-video-shell">
            {videoUrl ? (
              <>
                <video ref={videoRef} src={videoUrl} autoPlay loop muted playsInline onLoadedMetadata={onMetadataLoaded} />
                <div className="bbox-layer">
                  {activeTracks.map((track) => {
                    const [x1, y1, x2, y2] = track.last_bbox;
                    const left = (x1 / videoSize.width) * 100;
                    const top = (y1 / videoSize.height) * 100;
                    const width = ((x2 - x1) / videoSize.width) * 100;
                    const height = ((y2 - y1) / videoSize.height) * 100;
                    return (
                      <div
                        className="bbox"
                        key={`${track.camera_id}-${track.track_id}`}
                        style={{ left: `${left}%`, top: `${top}%`, width: `${width}%`, height: `${height}%` }}
                      >
                        <span>
                          {track.object_class} {formatPercent(track.state.confidence)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </>
            ) : (
              <div className="demo-video-placeholder">{videoError ?? "Loading demo video..."}</div>
            )}
          </div>
        </div>

        <div className="card demo-status-card">
          <h3>Pipeline status</h3>
          <dl className="kv-list">
            <div>
              <dt>Camera</dt>
              <dd>{demoCamera?.name ?? "-"}</dd>
            </div>
            <div>
              <dt>Source</dt>
              <dd>{demoCamera?.rtsp_url ?? "-"}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{demoCamera?.status ?? "-"}</dd>
            </div>
            <div>
              <dt>Active drone tracks</dt>
              <dd>{activeTracks.length}</dd>
            </div>
            <div>
              <dt>Demo events</dt>
              <dd>{demoEvents.length}</dd>
            </div>
          </dl>
        </div>
      </section>

      <section className="grid">
        <div className="card">
          <h3>Latest drone tracks</h3>
          <table>
            <thead>
              <tr>
                <th>Track</th>
                <th>Class</th>
                <th>Confidence</th>
                <th>Last seen</th>
                <th>BBox</th>
              </tr>
            </thead>
            <tbody>
              {activeTracks.length > 0 ? (
                activeTracks.map((track) => (
                  <tr key={`${track.camera_id}-${track.track_id}`}>
                    <td>{track.track_id}</td>
                    <td>{track.object_class}</td>
                    <td>{formatPercent(track.state.confidence)}</td>
                    <td>{new Date(track.last_seen_at).toLocaleTimeString()}</td>
                    <td>{track.last_bbox.map((value) => Math.round(value)).join(", ")}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5}>No active drone tracks.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="card">
          <h3>Latest demo events</h3>
          <table>
            <thead>
              <tr>
                <th>Occurred</th>
                <th>Type</th>
                <th>Track</th>
                <th>Severity</th>
                <th>Object</th>
              </tr>
            </thead>
            <tbody>
              {demoEvents.length > 0 ? (
                demoEvents.map((event) => (
                  <tr key={event.event_id}>
                    <td>{new Date(event.occurred_at).toLocaleTimeString()}</td>
                    <td>{event.event_type}</td>
                    <td>{event.track_id}</td>
                    <td>{event.severity}</td>
                    <td>{event.attributes.object_class ?? "-"}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5}>No demo events yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
