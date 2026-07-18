"""Fine-tune a YOLO ball/hoop detector on a Roboflow-exported dataset.

This is the accuracy follow-up referenced in the README: the default
checkpoint (models/basketball_best.pt) is a community fine-tune with an
unspecified license, fine for local prototyping but not for redistribution,
and not tuned for your specific camera angle/gym/ball. Fine-tuning on your
own or a CC-BY-licensed Roboflow dataset fixes both.

Not run as part of this session — this is the follow-up path, not a
built model.

Setup:
  1. Create a free Roboflow account: https://roboflow.com
  2. Find or build a basketball ball+hoop dataset on Roboflow Universe
     (search "basketball hoop"), or upload your own frames and annotate
     ball + hoop boxes.
  3. Export the dataset in "YOLOv8" format and download the zip
     (Roboflow gives you a `data.yaml` + train/valid/test image+label
     folders). Unzip it somewhere, e.g. `datasets/basketball/`.
  4. Check the dataset's license (CC BY 4.0 is common on Universe) before
     using it for anything beyond local experimentation.

Usage:
  python scripts/finetune_roboflow.py \
      --data datasets/basketball/data.yaml \
      --base yolo11n.pt \
      --epochs 100 \
      --imgsz 640

The resulting weights land in runs/detect/train/weights/best.pt — copy
that to models/basketball_best.pt (or point config/default.json's
model.weights at it) to use it in place of the default checkpoint.
"""
from __future__ import annotations

import argparse

from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune YOLO on a Roboflow ball/hoop export")
    parser.add_argument("--data", required=True, help="Path to the exported data.yaml")
    parser.add_argument(
        "--base",
        default="yolo11n.pt",
        help="Base checkpoint to fine-tune from (default: yolo11n.pt, nano COCO)",
    )
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument(
        "--device",
        default=None,
        help="Training device (cuda/mps/cpu). Omit to let ultralytics pick.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model = YOLO(args.base)
    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        device=args.device,
    )


if __name__ == "__main__":
    main()
