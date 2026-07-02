"""
Generate first-frame person mask from a green-screen video via simple chroma key.
Used as MatAnyone 2's first-frame hint.
"""
import cv2
import numpy as np
from pathlib import Path


def generate(video_path: str, out_path: str) -> None:
    cap = cv2.VideoCapture(video_path)
    ok, frame = cap.read()
    cap.release()
    assert ok, f"failed to read first frame from {video_path}"

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    green_mask = cv2.inRange(hsv, np.array([35, 40, 40]), np.array([85, 255, 255]))
    person = cv2.bitwise_not(green_mask)
    person = cv2.medianBlur(person, 5)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    person = cv2.morphologyEx(person, cv2.MORPH_CLOSE, kernel)
    person = cv2.morphologyEx(person, cv2.MORPH_OPEN, kernel)

    num, labels, stats, _ = cv2.connectedComponentsWithStats(person, connectivity=8)
    if num > 1:
        largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        person = (labels == largest).astype(np.uint8) * 255

    cv2.imwrite(out_path, person)
    coverage = (person > 0).mean() * 100
    print(f"mask saved: {out_path}  coverage={coverage:.1f}%")


if __name__ == "__main__":
    import sys
    generate(sys.argv[1], sys.argv[2])
