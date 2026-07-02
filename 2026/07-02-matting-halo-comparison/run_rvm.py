"""
Run RVM (mobilenetv3) inference on the same input via torch.hub-style loading.
Assumes RVM cloned to ../RVM.
"""
import sys
from pathlib import Path

import torch


def main():
    here = Path(__file__).parent
    rvm = here.parent / "RVM"
    sys.path.insert(0, str(rvm))

    from model import MattingNetwork
    from inference import convert_video

    weight_url = "https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3.pth"
    weight_path = here / "output" / "rvm_mobilenetv3.pth"
    if not weight_path.exists():
        import urllib.request
        print(f"downloading {weight_url}")
        urllib.request.urlretrieve(weight_url, weight_path)

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"device: {device}")
    model = MattingNetwork("mobilenetv3").eval().to(device)
    model.load_state_dict(torch.load(str(weight_path), map_location="cpu", weights_only=True))

    convert_video(
        model=model,
        input_source=str(here / "input.mp4"),
        output_type="video",
        output_alpha=str(here / "output" / "rvm_alpha.mp4"),
        output_foreground=str(here / "output" / "rvm_fgr.mp4"),
        output_video_mbps=4,
        seq_chunk=1,
        downsample_ratio=None,
        progress=True,
    )
    print("RVM outputs: output/rvm_fgr.mp4 output/rvm_alpha.mp4")


if __name__ == "__main__":
    main()
