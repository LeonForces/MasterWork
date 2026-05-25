"""
Training YOLO26 on the Roboflow dataset:
  https://universe.roboflow.com/fatin-zamri/small-detection-jic7b

Usage:
    python scripts/train_yolo26.py \
        --api-key YOUR_ROBOFLOW_API_KEY \
        --model yolo26n \
        --epochs 100 \
        --imgsz 640 \
        --batch 16
"""

import argparse
import io
import os
import sys
import zipfile
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Train YOLO26 on small-detection dataset")
    parser.add_argument("--api-key", required=True, help="Roboflow API key")
    parser.add_argument(
        "--model",
        default="yolo26n",
        choices=["yolo26n", "yolo26s", "yolo26m", "yolo26l", "yolo26x"],
        help="YOLO26 model variant (default: yolo26n)",
    )
    parser.add_argument("--version", type=int, default=0, help="Roboflow dataset version, 0=latest (default: 0)")
    parser.add_argument("--epochs", type=int, default=100, help="Number of training epochs (default: 100)")
    parser.add_argument("--imgsz", type=int, default=640, help="Input image size (default: 640)")
    parser.add_argument("--batch", type=int, default=16, help="Batch size, -1 for auto (default: 16)")
    parser.add_argument("--device", default=None, help="Device: 0, 0,1, cpu (default: auto)")
    parser.add_argument("--project", default="runs/train", help="Output project directory")
    parser.add_argument("--name", default="small_detection", help="Run name")
    parser.add_argument("--workers", type=int, default=8, help="Dataloader workers (default: 8)")
    parser.add_argument("--patience", type=int, default=50, help="Early stopping patience (default: 50)")
    parser.add_argument("--resume", action="store_true", help="Resume interrupted training")
    parser.add_argument("--export", action="store_true", help="Export best model to ONNX after training")
    return parser.parse_args()


def _get_latest_version(api_key: str) -> int:
    """Query Roboflow API to find the latest available version number."""
    import urllib.request
    import json

    url = f"https://api.roboflow.com/fatin-zamri/small-detection-jic7b?api_key={api_key}"
    with urllib.request.urlopen(url) as resp:
        data = json.loads(resp.read())
    versions = data.get("project", {}).get("versions", 0)
    if isinstance(versions, int):
        return versions
    # If it's a list of version objects, take the max id
    return max(int(v.get("id", "0").split("/")[-1]) for v in versions)


def download_dataset(api_key: str, version: int, dest: Path) -> str:
    import urllib.request
    import json

    # Resolve latest version via REST API (no SDK quirks)
    print("\n[1/3] Fetching dataset info from Roboflow API...")
    info_url = f"https://api.roboflow.com/fatin-zamri/small-detection-jic7b/{version}?api_key={api_key}"
    try:
        with urllib.request.urlopen(info_url) as resp:
            info = json.loads(resp.read())
    except Exception as e:
        # Version not found — try to get the total count and use the latest
        print(f"      Version {version} not found ({e}), detecting latest...")
        try:
            version = _get_latest_version(api_key)
            print(f"      Latest version: {version}")
            info_url = f"https://api.roboflow.com/fatin-zamri/small-detection-jic7b/{version}?api_key={api_key}"
            with urllib.request.urlopen(info_url) as resp:
                info = json.loads(resp.read())
        except Exception as e2:
            print(f"[ERROR] Could not fetch dataset info: {e2}")
            sys.exit(1)

    # Request export in YOLOv8 format
    export_url = (
        f"https://api.roboflow.com/fatin-zamri/small-detection-jic7b/{version}/yolov8"
        f"?api_key={api_key}&format=yolov8"
    )
    print(f"      Requesting YOLOv8 export (version {version})...")
    with urllib.request.urlopen(export_url) as resp:
        export_info = json.loads(resp.read())

    zip_link = export_info.get("export", {}).get("link") or export_info.get("link")
    if not zip_link:
        print(f"[ERROR] No download link in response: {export_info}")
        sys.exit(1)

    print(f"      Downloading ZIP...")
    with urllib.request.urlopen(zip_link) as resp:
        zip_bytes = resp.read()

    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        zf.extractall(dest)
    print(f"      Extracted to: {dest}")

    candidates = list(dest.rglob("data.yaml"))
    if not candidates:
        print(f"[ERROR] data.yaml not found in {dest}. Files present:")
        for f in dest.rglob("*"):
            print(f"        {f}")
        sys.exit(1)

    data_yaml = str(candidates[0].resolve())
    print(f"      data.yaml: {data_yaml}")
    return data_yaml


def train(args, data_yaml: str):
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] ultralytics package not found. Run: pip install ultralytics>=8.4.41")
        sys.exit(1)

    weights = f"{args.model}.pt"
    print(f"\n[2/3] Training {weights} for {args.epochs} epochs at imgsz={args.imgsz}...")

    model = YOLO(weights)
    train_kwargs = dict(
        data=data_yaml,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        workers=args.workers,
        patience=args.patience,
        project=args.project,
        name=args.name,
        resume=args.resume,
        exist_ok=True,
        verbose=True,
    )
    if args.device is not None:
        train_kwargs["device"] = args.device

    results = model.train(**train_kwargs)

    # Ultralytics may nest under a 'detect' subdirectory on some versions
    candidate_paths = [
        Path(args.project) / args.name / "weights" / "best.pt",
        Path("runs/detect") / args.project / args.name / "weights" / "best.pt",
    ]
    best_weights = next((p for p in candidate_paths if p.exists()), candidate_paths[0])
    print(f"\n      Best weights: {best_weights}")
    return best_weights


def validate(args, best_weights: Path, data_yaml: str):
    from ultralytics import YOLO
    import os

    if not best_weights.exists():
        print(f"\n[3/3] Skipping validation — weights not found at {best_weights}")
        print(f"      (Training validation results are already printed above)")
        return None

    print(f"\n[3/3] Validating best model: {best_weights}")
    # Disable Ultralytics network calls to avoid SSL issues on air-gapped runs
    os.environ.setdefault("YOLO_OFFLINE", "1")
    model = YOLO(str(best_weights))
    metrics = model.val(data=data_yaml, imgsz=args.imgsz, project=args.project, name=args.name + "_val")
    print(f"\n      mAP50:    {metrics.box.map50:.4f}")
    print(f"      mAP50-95: {metrics.box.map:.4f}")
    return metrics


def export_onnx(best_weights: Path, imgsz: int):
    from ultralytics import YOLO

    print(f"\n[+] Exporting to ONNX...")
    model = YOLO(str(best_weights))
    model.export(format="onnx", imgsz=imgsz, dynamic=True, simplify=True)
    onnx_path = best_weights.with_suffix(".onnx")
    print(f"      Saved: {onnx_path}")


def main():
    args = parse_args()

    dataset_dir = Path("datasets/small-detection-jic7b")
    dataset_dir.mkdir(parents=True, exist_ok=True)

    version = args.version if args.version > 0 else _get_latest_version(args.api_key)
    data_yaml = download_dataset(args.api_key, version, dataset_dir)
    best_weights = train(args, data_yaml)
    validate(args, best_weights, data_yaml)

    if args.export:
        export_onnx(best_weights, args.imgsz)

    print("\n Done. Results saved to:", Path(args.project) / args.name)


if __name__ == "__main__":
    main()
