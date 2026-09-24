"""Seeed XIAO ESP32S3 Sense board envelope (boxes measured off the vendor STEP) - see xiao_board_ref.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import xiao_board_ref


def gen_step():
    return xiao_board_ref.gen_step()
