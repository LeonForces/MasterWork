#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib import error, request


@dataclass
class HttpResponse:
    status_code: int
    text: str

    def json(self) -> Any:
        if not self.text:
            return {}
        return json.loads(self.text)


@dataclass
class SmokeConfig:
    api_base: str
    username: str
    password: str
    camera_source: str
    startup_timeout_sec: int


class SmokeRunner:
    def __init__(self, cfg: SmokeConfig) -> None:
        self.cfg = cfg
        self.headers: dict[str, str] = {}

    def _url(self, path: str) -> str:
        return f"{self.cfg.api_base.rstrip('/')}{path}"

    def _request(
        self,
        method: str,
        path: str,
        json_payload: dict[str, Any] | None = None,
        timeout_sec: int = 10,
    ) -> HttpResponse:
        data: bytes | None = None
        headers = dict(self.headers)
        if json_payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(json_payload).encode("utf-8")
        req = request.Request(url=self._url(path), data=data, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=timeout_sec) as resp:
                body = resp.read().decode("utf-8")
                return HttpResponse(status_code=resp.status, text=body)
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{method} {path} failed: {exc.code} {body}") from exc
        except OSError as exc:
            reason = getattr(exc, "reason", str(exc))
            raise RuntimeError(f"{method} {path} failed: {reason}") from exc

    def _wait_for_api_live(self) -> None:
        print(f"[0/7] Wait API live (timeout {self.cfg.startup_timeout_sec}s)")
        deadline = time.monotonic() + self.cfg.startup_timeout_sec
        last_error = "unknown error"
        while time.monotonic() < deadline:
            try:
                self._request("GET", "/health/live", timeout_sec=2)
                return
            except RuntimeError as exc:
                last_error = str(exc)
                time.sleep(2)
        raise RuntimeError(
            f"API did not become live within {self.cfg.startup_timeout_sec}s. Last error: {last_error}"
        )

    def run(self) -> None:
        self._wait_for_api_live()

        print("[1/7] Login")
        auth = self._request(
            "POST",
            "/api/v1/auth/login",
            json_payload={"username": self.cfg.username, "password": self.cfg.password},
        ).json()
        self.headers["Authorization"] = f"Bearer {auth['access_token']}"

        print("[2/7] Create camera")
        camera = self._request(
            "POST",
            "/api/v1/cameras",
            json_payload={
                "name": "smoke-cam",
                "rtsp_url": self.cfg.camera_source,
                "status": "active",
                "fps_target": 10,
                "resolution": "1280x720",
            },
        ).json()
        camera_id = camera["camera_id"]

        print("[3/7] Create zone")
        zone = self._request(
            "POST",
            "/api/v1/zones",
            json_payload={
                "camera_id": camera_id,
                "name": "smoke-zone",
                "zone_type": "polygon",
                "geometry": {
                    "points": [[100, 100], [400, 100], [400, 400], [100, 400]],
                },
            },
        ).json()
        zone_id = zone["zone_id"]

        print("[4/7] Create rule zone_enter")
        self._request(
            "POST",
            "/api/v1/rules",
            json_payload={
                "camera_id": camera_id,
                "name": "smoke-zone-enter",
                "rule_type": "zone_enter",
                "params": {"zone_id": zone_id},
                "severity": "high",
                "enabled": True,
            },
        )

        print("[5/7] Create rule line_cross")
        self._request(
            "POST",
            "/api/v1/rules",
            json_payload={
                "camera_id": camera_id,
                "name": "smoke-line-cross",
                "rule_type": "line_cross",
                "params": {"zone_id": zone_id, "line": [[120, 220], [520, 220]]},
                "severity": "high",
                "enabled": True,
            },
        )

        print("[6/7] Create rule dwell_time")
        self._request(
            "POST",
            "/api/v1/rules",
            json_payload={
                "camera_id": camera_id,
                "name": "smoke-dwell",
                "rule_type": "dwell_time",
                "params": {"zone_id": zone_id, "seconds": 5},
                "severity": "high",
                "enabled": True,
            },
        )

        print("[7/7] Fetch summary")
        cameras = self._request("GET", "/api/v1/cameras").json()
        zones = self._request("GET", "/api/v1/zones").json()
        rules = self._request("GET", "/api/v1/rules").json()
        events = self._request("GET", "/api/v1/events?limit=20").json()
        summary: dict[str, Any] = {
            "cameras": len(cameras),
            "zones": len(zones),
            "rules": len(rules),
            "events_last_20": len(events),
            "camera_id": camera_id,
            "zone_id": zone_id,
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        print("Smoke API flow finished successfully.")


def parse_args() -> SmokeConfig:
    parser = argparse.ArgumentParser(description="Run E2E smoke flow against API.")
    parser.add_argument("--api-base", default="http://localhost:8000")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="admin12345")
    parser.add_argument("--camera-source", default="sample.mp4")
    parser.add_argument("--startup-timeout-sec", type=int, default=90)
    args = parser.parse_args()
    return SmokeConfig(
        api_base=args.api_base,
        username=args.username,
        password=args.password,
        camera_source=args.camera_source,
        startup_timeout_sec=args.startup_timeout_sec,
    )


def main() -> None:
    cfg = parse_args()
    SmokeRunner(cfg).run()


if __name__ == "__main__":
    main()
