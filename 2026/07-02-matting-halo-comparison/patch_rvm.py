"""
Patch RVM's inference_utils.py so PyAV's add_stream accepts numeric rate.
Newer PyAV requires Fraction/int, not str like '60.0000'.
"""
from pathlib import Path

RVM_UTIL = Path(__file__).parent.parent / "RVM" / "inference_utils.py"

OLD = "        self.stream = self.container.add_stream('h264', rate=f'{frame_rate:.4f}')"
NEW = (
    "        from fractions import Fraction\n"
    "        self.stream = self.container.add_stream('h264', rate=Fraction(round(float(frame_rate) * 1000), 1000))"
)


def apply():
    text = RVM_UTIL.read_text()
    if NEW.strip() in text:
        print("already patched")
        return
    if OLD not in text:
        raise RuntimeError(f"expected block not found in {RVM_UTIL}")
    RVM_UTIL.write_text(text.replace(OLD, NEW))
    print(f"patched {RVM_UTIL}")


if __name__ == "__main__":
    apply()
