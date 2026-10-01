"""Shared hard points + per-style parameters.

Everything that touches the driver, the Yamaha R15 V2 power-train and the rear axle is
common to all ten styles; the styles differ in wheelbase/track, frame topology, bumper
shapes, side bumpers and bodywork.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

IN = 25.4

# --------------------------------------------------------------- materials / tube
TUBE_OD = 25.4          # 1 in
TUBE_WALL = 1.65        # 16 SWG  (rule: >= 1.2 mm)
TUBE_MAT = "AISI 4130 chromoly, seamless (C 0.28-0.33 %)"
BEND_R = 76.2           # 3 x OD centre-line radius
HOOP_BEND_R = 101.6

# --------------------------------------------------------------- vertical datum
Y_RAIL = 50.8           # centre-line of floor level members  (tube bottom = 1.5 in)
FLOOR_T = 2.0           # floor close-out (rule: >= 1 mm)
FIREWALL_T = 1.5        # rule: >= 1.5 mm aluminium

# --------------------------------------------------------------- wheels (rule table 1)
F_TYRE_D, F_TYRE_W = 10.0 * IN, 4.5 * IN      # 4.5x10.0-5
R_TYRE_D, R_TYRE_W = 11.0 * IN, 7.1 * IN      # 7.1x11.0-5
RIM_D = 5.0 * IN
Y_FAX = F_TYRE_D / 2    # 127.0
Y_RAX = R_TYRE_D / 2    # 139.7

# --------------------------------------------------------------- rear end (common)
X_RAX = 0.0
X_RBH = -125.0          # rear bulkhead
X_AXM = 70.0            # axle cross member
Z_RBOX = 420.0          # rear box half width
BEARING_Z = (-420.0, 80.0, 420.0)
AXLE_OD = 40.0
DISC_Z = -250.0
DISC_D = 180.0
SPROCKET_Z = 190.0      # chain plane
CHAIN_PITCH = 12.7      # #428
N_FRONT_SPROCKET = 14
N_REAR_SPROCKET = 34

# --------------------------------------------------------------- driver package (common)
Z_D = -60.0             # driver / seat / steering centre-line (seat offset left, engine right)
X_H, Y_H = 320.0, 150.0  # H-point
BACK_ANGLE = 20.0       # deg from vertical (rule: <= 30)
DRIVER_H = 1750.0
Z_LM, Z_RM = -290.0, 150.0   # main rails (left, right)
X_HOOP = 170.0          # roll hoop base (on main rails)
HOOP_TOP_Y = 1060.0     # centre-line of hoop top
HOOP_LEAN = 20.0        # deg, lower hoop leaning rearward (parallel to seat back)
HOOP_KNEE_Y = 650.0     # hoop bend / brace node height
HOOP_UPPER_LEAN = 8.0   # deg, upper hoop above the brace node
HOOP_CROSS_Y = 400.0
SEAT_CORNER = (X_H - 105.0, 48.0)
X_SEAT_XM = 620.0       # seat front cross member

# --------------------------------------------------------------- engine (common)
ENGINE_ORIGIN = (247.6, 230.0, SPROCKET_Z)   # countershaft centre in chain plane (66-link #428 chain)
Z_EBAY = 530.0          # engine bay outer rail
X_EBAY0, X_EBAY1 = 200.0, 800.0
X_CRADLE = (217.6, 497.6)
FIREWALL_Z = 165.0

# --------------------------------------------------------------- front end (common)
X_FB = 1290.0           # front bulkhead / foot guard
FB_HALF = 200.0         # about Z_D
FOOT_GUARD_TOP = 420.0
PEDAL_PIVOT = (1273.9, 284.5)
PEDAL_PAD = (1231.0, 205.0)
PEDAL_PAD_N = (-0.919, 0.394)   # pad face normal (towards driver)
BRAKE_LEVER = 80.0
BRAKE_LEVER_TILT = 15.0   # deg rearward from vertical
PEDAL_XBAR_Y = 330.0

# --------------------------------------------------------------- steering (common)
CASTER = 10.0           # deg
SCRUB = 89.4            # wheel centre to king-pin (3.52 in, from team sketch)
ARM_LEN = 155.0         # knuckle steering arm
Y_ARM = 82.0            # tie-rod plane (bottom of king-pin boss)
KP_BOSS_LEN = 100.0
COL_ANGLE = 33.0        # column, deg below horizontal
PITMAN_R = 90.0
WHEEL_Y = 420.0         # steering wheel hub height
STEER_WHEEL_OD = 280.0  # rule: >= 10 in (254)
COL_UPPER_BRG = 130.0   # distance of upper bearing from wheel hub along column
TARGET_R_OUTER = 2850.0  # design turning radius at outer front wheel (rule: <= 3000)

# --------------------------------------------------------------- rule limits
RULE = dict(
    wheelbase_max=60 * IN, track_max=50 * IN, length_max=65 * IN,
    gc_min=1 * IN, gc_max=2 * IN, hoop_over_helmet=3 * IN,
    front_bumper_from_bh=4 * IN, rear_bumper_from_bh=2 * IN,
    tube_od=(1 * IN, 2 * IN), tube_wall_min=1.2, turn_r_max=3000.0,
    wheel_od_min=10 * IN, fuel_max_l=3.0, exhaust_h_max=650.0, foot_guard_over_toe=3 * IN,
    engine_cc_max=160.0, mount_tab_min=5.0, firewall_min=1.5, floor_min=1.0, back_angle_max=30.0,
)


@dataclass
class Style:
    code: str
    name: str
    wheelbase_in: float
    ftrack_in: float
    rtrack_in: float
    length_in: float            # (informative) expected bumper-to-bumper length
    frame: str                  # frame topology key
    front_bumper: str
    rear_bumper: str
    side_bumper: str
    nose: str
    pods: str
    colour: tuple
    body_colour: tuple
    blurb: str = ""
    extra: dict = field(default_factory=dict)

    # derived ------------------------------------------------------------
    @property
    def W(self):
        return self.wheelbase_in * IN

    @property
    def FT(self):
        return self.ftrack_in * IN

    @property
    def RT(self):
        return self.rtrack_in * IN

    @property
    def KH(self):           # king-pin half spacing
        return self.FT / 2 - SCRUB

    @property
    def slug(self):
        return f"{self.code}_{self.name.replace(' ', '')}"


def col_dir_down():
    a = math.radians(COL_ANGLE)
    return (math.cos(a), -math.sin(a), 0.0)


def col_u():
    """Unit vector perpendicular to the column in the XY plane, pointing forward-up."""
    a = math.radians(COL_ANGLE)
    return (math.sin(a), math.cos(a), 0.0)


@dataclass
class Hard:
    """Per-style derived hard points (mm)."""
    s: Style
    beta: float = 0.0        # steering arm angle (rad) from -X towards centre
    arm_end_x: float = 0.0
    cb: tuple = ()           # column bottom
    wheel_c: tuple = ()      # steering wheel hub
    upper_brg: tuple = ()
    x_dash: float = 0.0
    x_ff: float = 0.0        # front bumper front face
    x_rf: float = 0.0        # rear bumper rear face
    x_fbar: float = 0.0      # front bumper bar centre-line
    x_rbar: float = 0.0
    fb_half: float = 0.0     # front bumper half width (centre-line)
    rb_half: float = 0.0
    z_side: float = 0.0      # side bumper centre-line |Z|
    sweep_x: float = 0.0     # max forward reach of steered front tyre


def derive(s: Style, sweep_x: float, beta: float | None = None) -> Hard:
    h = Hard(s)
    W = s.W
    # steering arm angle; tuned by steering.design() for ~100 % Ackermann at full lock
    h.beta = math.atan2(s.KH, W) if beta is None else beta
    h.arm_end_x = W - ARM_LEN * math.cos(h.beta)
    u = col_u()
    h.cb = (h.arm_end_x + PITMAN_R * u[0], Y_ARM + PITMAN_R * u[1], Z_D)
    d = col_dir_down()
    L = (WHEEL_Y - h.cb[1]) / (-d[1])
    h.wheel_c = (h.cb[0] - d[0] * L, WHEEL_Y, Z_D)
    h.upper_brg = (h.wheel_c[0] + d[0] * COL_UPPER_BRG, h.wheel_c[1] + d[1] * COL_UPPER_BRG, Z_D)
    h.x_dash = h.upper_brg[0]
    h.sweep_x = sweep_x
    # front bumper: clear steered tyre and >= 4 in (+5 mm) ahead of front bulkhead
    x_bar = max(sweep_x + 15.0 + TUBE_OD / 2, X_FB + RULE["front_bumper_from_bh"] + 5.0)
    h.x_fbar = x_bar
    h.x_ff = x_bar + TUBE_OD / 2
    # rear bumper: >= 2 in (+6 mm) behind rear bulkhead and clear of the rear tyre
    h.x_rbar = min(X_RBH - RULE["rear_bumper_from_bh"] - 6.0, X_RAX - R_TYRE_D / 2 - 20.0 - TUBE_OD / 2)
    h.x_rf = h.x_rbar - TUBE_OD / 2
    h.fb_half = s.FT / 2 + F_TYRE_W / 2 + 22.0
    h.rb_half = s.RT / 2 + R_TYRE_W / 2 + 4.0
    h.z_side = max(s.RT / 2 + R_TYRE_W / 2 - 25.0, Z_EBAY + 78.0)
    return h
