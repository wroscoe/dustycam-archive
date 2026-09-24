"""tubecase: static XIAO Sense tube camera with a bq25185 solar compartment.

Full assembly at rest (installed pose). Geometry lives in tubecase_lib.py.
"""

import tubecase_lib as L


def gen_step():
    return {"shape": L.build_assembly()}


if __name__ == "__main__":
    print(gen_step()["shape"].bounding_box())
