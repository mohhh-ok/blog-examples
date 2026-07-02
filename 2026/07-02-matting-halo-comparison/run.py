"""
End-to-end reproduction: patch → mask → MatAnyone 2 → RVM → analyze.
Requires:
- ../MatAnyone2 and ../RVM cloned
- input.mp4 already fetched (see README)
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent


def step(desc, cmd):
    print(f"\n=== {desc} ===")
    subprocess.run(cmd, cwd=HERE, check=True)


def main():
    assert (HERE.parent / "MatAnyone2").exists(), "clone MatAnyone2 into ../MatAnyone2 first"
    assert (HERE.parent / "RVM").exists(), "clone RVM into ../RVM first"
    assert (HERE / "input.mp4").exists(), "download input.mp4 first (see README)"

    (HERE / "output").mkdir(exist_ok=True)

    step("patch MatAnyone2 for new torchvision", [sys.executable, "patch_matanyone2.py"])
    step("patch RVM for new PyAV", [sys.executable, "patch_rvm.py"])
    step("green-key first-frame mask", [sys.executable, "generate_mask.py", "input.mp4", "output/first_frame_mask.png"])
    step("MatAnyone 2 inference", [sys.executable, "run_matanyone2.py"])
    step("RVM inference", [sys.executable, "run_rvm.py"])
    step("analyze + save webp", [sys.executable, "analyze.py"])
    print("\nall done. see output/metrics.csv and output/*.webp")


if __name__ == "__main__":
    main()
