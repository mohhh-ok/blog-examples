"""
Patch MatAnyone2 to use PyAV instead of torchvision.io.read_video.
New torchvision (0.20+) removed read_video; MatAnyone2 still expects it.
Run this after cloning MatAnyone2 to `../MatAnyone2/`.
"""
from pathlib import Path

MATANYONE_UTIL = Path(__file__).parent.parent / "MatAnyone2" / "matanyone2" / "utils" / "inference_utils.py"

OLD = '''    if frame_root.endswith(VIDEO_EXTENSIONS):  # Video file path
        video_name = os.path.basename(frame_root)[:-4]
        frames, _, info = torchvision.io.read_video(filename=frame_root, pts_unit='sec', output_format='TCHW') # RGB
        fps = info['video_fps']'''

NEW = '''    if frame_root.endswith(VIDEO_EXTENSIONS):  # Video file path
        video_name = os.path.basename(frame_root)[:-4]
        import av
        container = av.open(frame_root)
        stream = container.streams.video[0]
        fps = float(stream.average_rate)
        frames_list = []
        for frame in container.decode(stream):
            arr = frame.to_ndarray(format='rgb24')  # HWC uint8
            frames_list.append(arr)
        container.close()
        frames = torch.from_numpy(np.stack(frames_list)).permute(0, 3, 1, 2).contiguous()  # TCHW uint8'''


def apply():
    text = MATANYONE_UTIL.read_text()
    if NEW.strip() in text:
        print("already patched")
        return
    if OLD not in text:
        raise RuntimeError(f"expected block not found in {MATANYONE_UTIL}")
    MATANYONE_UTIL.write_text(text.replace(OLD, NEW))
    print(f"patched {MATANYONE_UTIL}")


if __name__ == "__main__":
    apply()
