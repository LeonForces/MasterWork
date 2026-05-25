#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib import error, request
from uuid import uuid4


@dataclass
class HttpResponse:
    status_code: int
    text: str

    def json(self) -> Any:
        if not self.text:
            return {}
        return json.loads(self.text)


@dataclass
class Config:
    api_base: str
    webhook_base: str
    username: str
    password: str
    compose_bin: str
    timeout_sec: int
    poll_sec: float


class AcceptanceRunner:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.headers: dict[str, str] = {}
        self._stopped_services: set[str] = set()

    def _request(
        self,
        method: str,
        url: str,
        payload: dict[str, Any] | None = None,
        timeout_sec: int = 10,
        expected: tuple[int, ...] = (200,),
    ) -> HttpResponse:
        data: bytes | None = None
        headers = dict(self.headers)
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode("utf-8")
        req = request.Request(url=url, data=data, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=timeout_sec) as resp:
                body = resp.read().decode("utf-8")
                if resp.status not in expected:
                    raise RuntimeError(f"{method} {url} unexpected status: {resp.status}, body={body}")
                return HttpResponse(status_code=resp.status, text=body)
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code in expected:
                return HttpResponse(status_code=exc.code, text=body)
            raise RuntimeError(f"{method} {url} failed: {exc.code}, body={body}") from exc
        except OSError as exc:
            reason = getattr(exc, "reason", str(exc))
            raise RuntimeError(f"{method} {url} failed: {reason}") from exc

    def _api(self, method: str, path: str, payload: dict[str, Any] | None = None, expected: tuple[int, ...] = (200,)) -> HttpResponse:
        base = self.cfg.api_base.rstrip("/")
        return self._request(method, f"{base}{path}", payload, expected=expected)

    def _webhook(self, method: str, path: str, expected: tuple[int, ...] = (200,)) -> HttpResponse:
        base = self.cfg.webhook_base.rstrip("/")
        return self._request(method, f"{base}{path}", expected=expected)

    def _compose(self, *args: str) -> subprocess.CompletedProcess[str]:
        cmd = [*shlex.split(self.cfg.compose_bin), *args]
        return subprocess.run(cmd, check=True, capture_output=True, text=True)

    def _psql(self, sql: str) -> str:
        shell_cmd = (
            "psql -v ON_ERROR_STOP=1 -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\" "
            f"-At -F '|' -c {shlex.quote(sql)}"
        )
        result = self._compose("exec", "-T", "postgres", "sh", "-lc", shell_cmd)
        return result.stdout.strip()

    def _wait(self, name: str, fn, timeout_sec: int | None = None, poll_sec: float | None = None) -> Any:
        timeout = timeout_sec if timeout_sec is not None else self.cfg.timeout_sec
        poll = poll_sec if poll_sec is not None else self.cfg.poll_sec
        deadline = time.monotonic() + timeout
        last_error = "not ready"
        while time.monotonic() < deadline:
            try:
                value = fn()
                if value:
                    return value
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
            time.sleep(poll)
        raise RuntimeError(f"Timeout waiting for {name}: {last_error}")

    def _login(self) -> None:
        token = self._api(
            "POST",
            "/api/v1/auth/login",
            {"username": self.cfg.username, "password": self.cfg.password},
        ).json()
        self.headers["Authorization"] = f"Bearer {token['access_token']}"

    def _create_camera_zone_rule(self) -> tuple[str, str, str]:
        camera = self._api(
            "POST",
            "/api/v1/cameras",
            {
                "name": f"acc-cam-{uuid4().hex[:8]}",
                "rtsp_url": "synthetic://camera",
                "status": "active",
                "fps_target": 10,
                "resolution": "1280x720",
            },
        ).json()
        camera_id = camera["camera_id"]

        zone = self._api(
            "POST",
            "/api/v1/zones",
            {
                "camera_id": camera_id,
                "name": f"acc-zone-{uuid4().hex[:8]}",
                "zone_type": "polygon",
                "geometry": {"points": [[100, 100], [400, 100], [400, 400], [100, 400]]},
            },
        ).json()
        zone_id = zone["zone_id"]

        rule = self._api(
            "POST",
            "/api/v1/rules",
            {
                "camera_id": camera_id,
                "name": f"acc-rule-{uuid4().hex[:8]}",
                "rule_type": "zone_enter",
                "params": {"zone_id": zone_id},
                "severity": "high",
                "enabled": True,
            },
        ).json()
        return camera_id, zone_id, rule["rule_id"]

    def _insert_synthetic_event(self, camera_id: str, rule_id: str, event_type: str) -> tuple[str, str]:
        event_id = str(uuid4())
        outbox_id = str(uuid4())
        dedup_key = f"{camera_id}:{rule_id}:{uuid4().hex[:10]}"
        occurred_at = datetime.now(tz=timezone.utc).isoformat()
        payload = {
            "schema_version": 1,
            "event_id": event_id,
            "event_type": event_type,
            "camera_id": camera_id,
            "track_id": f"trk-{uuid4().hex[:8]}",
            "object_class": "person",
            "confidence": 0.99,
            "occurred_at": occurred_at,
            "zone_id": "",
            "rule_id": rule_id,
            "severity": "high",
            "snapshot_path": None,
            "dedup_key": dedup_key,
            "attributes": {"source": "acceptance"},
        }
        payload_json = json.dumps(payload, ensure_ascii=False).replace("'", "''")
        sql = f"""
        INSERT INTO events (
            event_id, camera_id, track_id, rule_id, event_type, severity, occurred_at,
            confidence, snapshot_path, dedup_key, attributes
        ) VALUES (
            '{event_id}', '{camera_id}', '{payload["track_id"]}', '{rule_id}', '{event_type}', 'high', NOW(),
            0.99, NULL, '{dedup_key}', '{{"source":"acceptance"}}'::json
        );
        INSERT INTO event_outbox (
            outbox_id, event_id, payload, status, retry_count, next_retry_at, published_at, created_at
        ) VALUES (
            '{outbox_id}', '{event_id}', '{payload_json}'::json, 'pending', 0, NULL, NULL, NOW()
        );
        """
        self._psql(sql)
        return event_id, outbox_id

    def _outbox_status(self, event_id: str) -> dict[str, Any]:
        row = self._psql(
            "SELECT status, retry_count, COALESCE(to_char(published_at, 'YYYY-MM-DD\"T\"HH24:MI:SSOF'), '') "
            f"FROM event_outbox WHERE event_id='{event_id}' LIMIT 1;"
        )
        if not row:
            return {}
        status, retry_count, published_at = row.split("|")
        return {
            "status": status,
            "retry_count": int(retry_count),
            "published_at": published_at,
        }

    def _delivery_counts(self, event_id: str) -> tuple[int, int]:
        out = self._psql(
            "SELECT "
            "SUM(CASE WHEN status='success' THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) "
            f"FROM delivery_attempts WHERE event_id='{event_id}';"
        )
        if not out:
            return 0, 0
        success, failed = out.split("|")
        return int(success or "0"), int(failed or "0")

    def _stop_service(self, name: str) -> None:
        self._compose("stop", name)
        self._stopped_services.add(name)

    def _start_service(self, name: str) -> None:
        self._compose("start", name)
        self._stopped_services.discard(name)

    def _ensure_started(self) -> None:
        for service in list(self._stopped_services):
            try:
                self._start_service(service)
            except Exception:  # noqa: BLE001
                pass

    def _security_check(self) -> dict[str, Any]:
        viewer_username = f"viewer_{uuid4().hex[:8]}"
        viewer_password = "viewer12345"
        self._api(
            "POST",
            "/api/v1/users",
            {"username": viewer_username, "password": viewer_password, "roles": ["viewer"]},
        )
        viewer_token = self._request(
            "POST",
            f"{self.cfg.api_base.rstrip('/')}/api/v1/auth/login",
            {"username": viewer_username, "password": viewer_password},
        ).json()["access_token"]
        original = dict(self.headers)
        self.headers["Authorization"] = f"Bearer {viewer_token}"
        forbidden = self._api(
            "POST",
            "/api/v1/cameras",
            {
                "name": "viewer-forbidden",
                "rtsp_url": "synthetic://viewer",
                "status": "active",
                "fps_target": 5,
                "resolution": "640x480",
            },
            expected=(403,),
        )
        self.headers = original
        return {"viewer_create_camera_status": forbidden.status_code}

    def run(self) -> dict[str, Any]:
        started_at = time.time()
        summary: dict[str, Any] = {
            "checks": {},
            "timings_sec": {},
        }
        try:
            self._wait("api live", lambda: self._api("GET", "/health/live"))
            self._wait("api ready", lambda: self._api("GET", "/health/ready"))
            self._wait("webhook mock", lambda: self._webhook("GET", "/health"))

            self._login()
            summary["checks"]["security"] = self._security_check()

            camera_id, zone_id, rule_id = self._create_camera_zone_rule()
            summary["camera_id"] = camera_id
            summary["zone_id"] = zone_id
            summary["rule_id"] = rule_id

            # Functional E2E: synthetic event should be published and delivered.
            t0 = time.time()
            event_1, _ = self._insert_synthetic_event(camera_id, rule_id, "zone_enter")
            self._wait(
                "functional delivery",
                lambda: self._delivery_counts(event_1)[0] >= 1,
                timeout_sec=120,
            )
            functional_delivery_sec = round(time.time() - t0, 3)
            status_1 = self._outbox_status(event_1)
            summary["checks"]["functional_e2e"] = {
                "event_id": event_1,
                "outbox_status": status_1,
                "delivery_counts": {
                    "success": self._delivery_counts(event_1)[0],
                    "failed": self._delivery_counts(event_1)[1],
                },
            }
            summary["timings_sec"]["functional_delivery"] = functional_delivery_sec

            # Reliability: RabbitMQ outage should keep event in outbox; after recovery it should be delivered.
            self._stop_service("rabbitmq")
            event_2, _ = self._insert_synthetic_event(camera_id, rule_id, "line_cross")
            time.sleep(6)
            during_outage = self._outbox_status(event_2)
            if during_outage.get("status") == "published":
                raise RuntimeError("Event unexpectedly published while RabbitMQ was stopped")
            t1 = time.time()
            self._start_service("rabbitmq")
            self._wait(
                "rabbitmq recovery delivery",
                lambda: self._delivery_counts(event_2)[0] >= 1,
                timeout_sec=180,
            )
            rabbit_recovery_sec = round(time.time() - t1, 3)
            summary["checks"]["rabbitmq_reliability"] = {
                "event_id": event_2,
                "status_during_outage": during_outage,
                "status_after_recovery": self._outbox_status(event_2),
                "delivery_counts": {
                    "success": self._delivery_counts(event_2)[0],
                    "failed": self._delivery_counts(event_2)[1],
                },
            }
            summary["timings_sec"]["rabbitmq_recovery"] = rabbit_recovery_sec

            # Retry path: webhook down -> at least one failed attempt; after recovery -> success.
            self._stop_service("webhook-mock")
            event_3, _ = self._insert_synthetic_event(camera_id, rule_id, "dwell_time")
            self._wait(
                "failed delivery attempt",
                lambda: self._delivery_counts(event_3)[1] >= 1,
                timeout_sec=120,
            )
            failed_before = self._delivery_counts(event_3)[1]
            t2 = time.time()
            self._start_service("webhook-mock")
            self._wait("webhook recovery", lambda: self._webhook("GET", "/health"), timeout_sec=60)
            self._wait(
                "successful retry delivery",
                lambda: self._delivery_counts(event_3)[0] >= 1,
                timeout_sec=180,
            )
            webhook_recovery_sec = round(time.time() - t2, 3)
            summary["checks"]["webhook_retry"] = {
                "event_id": event_3,
                "failed_attempts_before_recovery": failed_before,
                "delivery_counts": {
                    "success": self._delivery_counts(event_3)[0],
                    "failed": self._delivery_counts(event_3)[1],
                },
                "outbox_status": self._outbox_status(event_3),
            }
            summary["timings_sec"]["webhook_recovery"] = webhook_recovery_sec

            summary["result"] = "passed"
            summary["duration_sec"] = round(time.time() - started_at, 3)
            return summary
        finally:
            self._ensure_started()


def parse_args() -> Config:
    parser = argparse.ArgumentParser(description="Run end-to-end acceptance checks for the platform.")
    parser.add_argument("--api-base", default="http://localhost:8000")
    parser.add_argument("--webhook-base", default="http://localhost:8090")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="admin12345")
    parser.add_argument("--compose-bin", default="docker-compose")
    parser.add_argument("--timeout-sec", type=int, default=180)
    parser.add_argument("--poll-sec", type=float, default=2.0)
    args = parser.parse_args()
    return Config(
        api_base=args.api_base,
        webhook_base=args.webhook_base,
        username=args.username,
        password=args.password,
        compose_bin=args.compose_bin,
        timeout_sec=args.timeout_sec,
        poll_sec=args.poll_sec,
    )


def main() -> None:
    cfg = parse_args()
    runner = AcceptanceRunner(cfg)
    summary = runner.run()
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
