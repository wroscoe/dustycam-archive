"""xiao_pantilt: geared pan-tilt head for the XIAO ESP32S3 Sense (9 g servos, v2).

Zero pose (pan 0, tilt 0). Geometry and the pose function live in
pantilt_lib.py; the viewer sidecar xiao_pantilt.params.js animates pan/tilt.
"""

import pantilt_lib as L


def gen_step():
    return {"shape": L.build_assembly(0.0, 0.0), "params": "xiao_pantilt.params.js"}


if __name__ == "__main__":
    print(gen_step()["shape"].bounding_box())
