"""Body + lid + board envelope in the board frame - see xiao_sense_case_common.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from xiao_sense_case_common import body, lid, board_ref
from build123d import Compound


def gen_step():
    a = Compound(children=[body(), lid(), board_ref()])
    a.label = "xiao_sense_case_assembly"
    return a
