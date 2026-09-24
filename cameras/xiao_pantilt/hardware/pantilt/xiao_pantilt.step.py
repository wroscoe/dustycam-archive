"""xiao_pantilt v7: direct-drive pan-only camera pod for the XIAO ESP32S3 Sense under a 2" acrylic tube.

Current split-pod, battery-base assembly at zero pose (pan 0, tilt 0). Geometry
and the pose function live in pantilt_lib.py; the viewer sidecar
xiao_pantilt.params.js animates pan/tilt.
"""

import pantilt_lib as L


def gen_step():
    return {"shape": L.build_assembly(0.0, 0.0), "params": "xiao_pantilt.params.js"}


if __name__ == "__main__":
    print(gen_step()["shape"].bounding_box())
