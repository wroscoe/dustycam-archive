#!/bin/bash
S=~/.claude/skills/cad; P=$S/.venv/bin/python; export PYTHONPATH=$S/scripts/packages/cadgen/src
PANTILT_BACKLASH=0 $P sweep.py --corners --out clash_corners_backlash0.md
$P sweep.py --out clash_table.md
PANTILT_COVER=dome4 $P sweep.py --out clash_table_dome4.md
PANTILT_COVER=jar_pint $P sweep.py --out clash_table_jar_pint.md
echo ALLDONE
