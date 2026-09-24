"""Case lid for the Seeed XIAO ESP32S3 Sense - see xiao_sense_case_common.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from xiao_sense_case_common import lid


def gen_step():
    return lid()
