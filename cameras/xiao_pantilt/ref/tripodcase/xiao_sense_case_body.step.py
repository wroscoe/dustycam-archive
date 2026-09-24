"""Case body for the Seeed XIAO ESP32S3 Sense - see xiao_sense_case_common.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from xiao_sense_case_common import body


def gen_step():
    return body()
