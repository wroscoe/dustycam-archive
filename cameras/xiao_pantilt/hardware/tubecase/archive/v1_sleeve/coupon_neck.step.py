"""Print-oriented test coupon: a ring, ID 38, printed in minutes, with three
stepped-OD bands (bottom to top: 44.4, 44.2, 44.0) so the real acrylic tube
(vendor-nominal ID 44.5, not measured) can be slid on from the top and stops
at the band that actually fits. See tubecase_lib.coupon_neck_zero()."""
import tubecase_lib as L


def gen_step():
    s = L.coupon_neck_zero()
    s.label = "tubecase_coupon_neck_print"
    return s
