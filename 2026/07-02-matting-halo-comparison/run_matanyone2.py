"""
Run MatAnyone 2 inference on the sample green-screen video.

Assumes:
- MatAnyone 2 cloned to ../MatAnyone2
- Green-key mask exists at inputs/first_frame_mask.png (see generate_mask.py)
- Weights auto-download to ../MatAnyone2/pretrained_models/matanyone2.pth
"""
import subprocess
import sys
from pathlib import Path


def main():
    here = Path(__file__).parent
    matanyone = here.parent / "MatAnyone2"
    video = here / "input.mp4"
    mask = here / "output" / "first_frame_mask.png"
    result_dir = matanyone / "results"

    assert video.exists(), f"missing {video} — run: curl -L -o input.mp4 https://assets.mixkit.co/videos/28287/28287-720.mp4"
    assert mask.exists(), f"missing {mask} — run: python generate_mask.py input.mp4 output/first_frame_mask.png"

    # copy inputs into MatAnyone2/inputs/ per its convention
    (matanyone / "inputs").mkdir(exist_ok=True)
    subprocess.run(["cp", str(video), str(matanyone / "inputs" / "sample.mp4")], check=True)
    subprocess.run(["cp", str(mask), str(matanyone / "inputs" / "sample.png")], check=True)

    cmd = [
        sys.executable, "inference_matanyone2.py",
        "-i", "inputs/sample.mp4",
        "-m", "inputs/sample.png",
    ]
    subprocess.run(cmd, cwd=matanyone, check=True)

    # collect outputs
    out_fgr = result_dir / "sample_fgr.mp4"
    out_pha = result_dir / "sample_pha.mp4"
    (here / "output").mkdir(exist_ok=True)
    subprocess.run(["cp", str(out_fgr), str(here / "output" / "matanyone2_fgr.mp4")], check=True)
    subprocess.run(["cp", str(out_pha), str(here / "output" / "matanyone2_alpha.mp4")], check=True)
    print(f"MatAnyone 2 outputs: output/matanyone2_fgr.mp4 output/matanyone2_alpha.mp4")


if __name__ == "__main__":
    main()
