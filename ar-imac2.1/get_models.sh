#!/usr/bin/env bash
# Face models for AR-iMac 2.1 scoring and head crops, into ar-imac2.1/models/.
# Reuses the v2.0 copies in poc/models/ when they are already downloaded (no second 300 MB download).
#
# Licences: yunet.onnx and sface.onnx (OpenCV zoo) are fine for commercial use.
# buffalo_l (InsightFace ArcFace) is non-commercial research only.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$HERE/models" && cd "$HERE/models"
V20="$HERE/../poc/models"

fetch() {
  if [ -s "$2" ]; then echo "have $2"
  elif [ -s "$V20/$2" ]; then echo "copy $2 from poc/models"; cp "$V20/$2" "$2"
  else echo "get  $2"; curl -fL --retry 3 -o "$2" "$1"; fi
}

fetch https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx yunet.onnx
fetch https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx sface.onnx
fetch https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip buffalo_l.zip
[ -d buffalo_l ] || unzip -q buffalo_l.zip -d buffalo_l
echo "done: $(pwd)"
