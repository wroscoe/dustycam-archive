#!/usr/bin/env bash
# Regenerate every PNG in snaps/.  Run from this directory:
#     bash render.sh
# Builds each review model's scratch .step (they are NOT committed), renders
# it with the camera recorded here, then deletes the .step again.  The two
# coupon images are rendered straight from print/*.3mf.
set -euo pipefail

PY=~/.claude/skills/cad/.venv/bin/python
CADGEN=~/.claude/skills/cad/.venv/bin/cadgen
DISP='{"mode":"solid"}'

cd "$(dirname "$0")"

for m in bay_view section_cx section_tongue section_rails tilt_insertion \
         plate_inner section_lens; do
    $PY "$m.step.py" >/dev/null
done

# looking IN through the back mouth (+Z side), and the same model from the front
$CADGEN snapshot bay_view.step bay_back.png \
    --camera '{"direction":[0,0,1],"up":[0,1,0]}' --display "$DISP"
$CADGEN snapshot bay_view.step bay_front.png \
    --camera '{"direction":[0,0,-1],"up":[0,1,0]}' --display "$DISP"

# sections: X-cuts are viewed from +X, the Y-cut from +Y with the front up
$CADGEN snapshot section_cx.step section_cx.png \
    --camera '{"direction":[1,0,0],"up":[0,1,0]}' --display "$DISP"
$CADGEN snapshot section_tongue.step section_tongue.png \
    --camera '{"direction":[1,0,0],"up":[0,1,0]}' --display "$DISP"
$CADGEN snapshot section_lens.step section_lens.png \
    --camera '{"direction":[1,0,0],"up":[0,1,0]}' --display "$DISP"
$CADGEN snapshot section_rails.step section_rails.png \
    --camera '{"direction":[0,1,0],"up":[0,0,-1]}' --display "$DISP"
$CADGEN snapshot tilt_insertion.step tilt_insertion.png \
    --camera '{"direction":[1,0,0],"up":[0,1,0]}' --display "$DISP"

# the front plate from its inner side, slightly off axis so the boss reads
$CADGEN snapshot plate_inner.step plate_inner.png \
    --camera '{"direction":[0.45,-0.35,1],"up":[0,1,0]}' --display "$DISP"

# coupons, in print orientation, from under the bed plane so the bay reads
$CADGEN snapshot ../print/coupon_ring_bay.3mf coupon_ring_bay.png \
    --camera '{"direction":[0.55,-0.55,-0.62],"up":[0,0,1]}'
$CADGEN snapshot ../print/coupon_front_plate.3mf coupon_front_plate.png \
    --camera '{"direction":[0.55,0.55,0.62],"up":[0,0,1]}'

rm -f bay_view.step section_cx.step section_tongue.step section_rails.step \
      tilt_insertion.step plate_inner.step section_lens.step
