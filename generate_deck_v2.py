#!/usr/bin/env python3
"""
STRIKEBACK CYBERDECK v2  --  2 parts (tray + top deck), A1 mini, no supports
 * LCD window + Pi stack CENTRED on the deck
 * Battery bay for up to 4x 18650 (BAT_CELLS) lying side by side, 26.8 mm tall bay
 * Sci-fi: LED light-bar channels, LCD bezel step + frame groove, 6 status-LED
   holes, encoder + 2-button control cluster, mesh grille, GPS/radio racks both sides
Run: python3 generate_deck_v2.py stl
"""
import sys, os, math, threading
import numpy as np
from generate_case import Box, RRect, Cyl, union_all, sub_all, to_tris, write_stl, volume
from generate_deck import raycheck

OX, WALL, R_OUT, FLOOR, PLATE = 172.0, 2.4, 6.0, 3.0, 2.4
KB_W, KB_D_, KB_T, KB_CLR, KB_DEPTH, FRONT_M = 155.0, 89.0, 16.5, 1.0, 12.4, 10.0
PI_L, PI_W = 85.0, 56.0
STANDOFF_H, STANDOFF_R, STANDOFF_HOLE, PCB_T = 4.0, 3.0, 2.3, 1.6
LCD_TOP_ABOVE_PCB, LCD_GAP = 20.6, 0.6
LCD_WINDOW, LCD_OFF = (74.0, 50.0), (0.0, 0.0)
BZ = 64.0
BAT_CELLS, CELL_D = 4, 18.6                       # <- your 18650s (up to 4 side-by-side)
BAT_BAY_W = BAT_CELLS*20.0 + 2.0
POST_R, INSERT_HOLE, INSERT_DEPTH, SCREW_HOLE, CBORE_D, CBORE_DEPTH = 3.6, 4.0, 6.0, 3.4, 6.4, 2.2
PART_T = 1.6
PART_X = (38.0, 38.0 + PART_T + BAT_BAY_W)
CRADLE_X = (5.0, 6.6, 33.0, 34.6); CRADLE_Y = (12.0, 100.0); RAIL_H = 10.0

POCKET_W, POCKET_H = KB_W+2*KB_CLR, KB_D_+2*KB_CLR
POCKET_X0 = (OX-POCKET_W)/2
POCKET_Y0, POCKET_Y1 = FRONT_M, FRONT_M+POCKET_H
Y_BZ0 = POCKET_Y1 + PART_T
OY = Y_BZ0 + BZ + WALL
PB_H = STANDOFF_H + PCB_T + LCD_TOP_ABOVE_PCB + LCD_GAP
ZP = FLOOR + PB_H; Z_SHELF = ZP + PLATE; H = Z_SHELF + KB_DEPTH
STEP_Y = POCKET_Y1 + 2.4
PI_X0 = OX/2 - PI_L/2                              # centred
PI_Y0 = (Y_BZ0 + Y_BZ0 + BZ)/2 - PI_W/2
PCB_TOP = FLOOR + STANDOFF_H + PCB_T
LCX, LCY = PI_X0+PI_L/2+LCD_OFF[0], PI_Y0+PI_W/2+LCD_OFF[1]
YM = 118.0
POSTS = [(6.0, 5.0, 'margin'), (OX/2, 5.0, 'margin'), (OX-6.0, 5.0, 'margin'),
         (5.6, YM, 'plate'), (OX-5.6, YM, 'plate'), (5.6, OY-5.6, 'plate'), (OX-5.6, OY-5.6, 'plate')]
SMA_X = (12, 26, 40, 140, 156)
ENC = (152.0, 124.0); BTN = ((138.0, 136.0), (162.0, 136.0)); GRILLE = (150.0, 155.0)
STATUS_LED_X = [62.0 + 9.6*k for k in range(6)]; STATUS_LED_Y = 163.0


def pi_xy(px, py): return (PI_X0 + PI_L - px, PI_Y0 + PI_W - py)
def outer(z0, z1, g=0.0): return RRect(-g, -g, OX+g, OY+g, R_OUT+g, z0, z1)
def inset(dd, z0, z1): return RRect(dd, dd, OX-dd, OY-dd, max(0.4, R_OUT-dd), z0, z1)
def standoffs(): return [pi_xy(px, py) for px in (3.5, 61.5) for py in (3.5, 52.5)]


def tray_cutters():
    c = []; zc = FLOOR + PB_H/2
    for x in SMA_X: c.append(Cyl('y', zc, x, 3.3, OY-WALL-0.6, OY+0.5))
    yb0, yb1 = OY-WALL-0.6, OY+0.5
    ux = pi_xy(11.2, 0)[0]
    c.append(Box(ux-6.5, ux+6.5, yb0, yb1, PCB_TOP-1.6, PCB_TOP+6.0))                       # USB-C
    c.append(Box(pi_xy(39.5, 0)[0]-7.0, pi_xy(26.0, 0)[0]+7.0, yb0, yb1, PCB_TOP-1.6, PCB_TOP+5.5))  # micro-HDMI x2
    c.append(Cyl('y', PCB_TOP+3.0, pi_xy(53.5, 0)[0], 4.6, yb0, yb1))                         # audio
    c.append(Box(OX-WALL-0.6, OX+0.5, 35-6.5, 35+6.5, 6.0, 13.5))                              # USB-C charge in
    c.append(Cyl('x', 60.0, 10.0, 6.0, OX-WALL-0.6, OX+0.5))                                   # power switch
    return c


def build_tray():
    body = outer(0, ZP)
    cav = inset(WALL, FLOOR, ZP+0.5)
    keep = [Box(x, x+PART_T, WALL-0.4, POCKET_Y1+PART_T, FLOOR-1, ZP+1) for x in PART_X]
    keep.append(Box(WALL-0.4, OX-WALL+0.4, POCKET_Y1, Y_BZ0, FLOOR-1, ZP+1))
    keep += [Cyl('z', cx, cy, POST_R, FLOOR-1, ZP+1) for cx, cy, _ in POSTS]
    keep += [Cyl('z', sx, sy, STANDOFF_R, FLOOR-1, FLOOR+STANDOFF_H) for sx, sy in standoffs()]
    a, b, c_, e = CRADLE_X
    keep.append(Box(a, b, CRADLE_Y[0], CRADLE_Y[1], FLOOR-1, FLOOR+RAIL_H))
    keep.append(Box(c_, e, CRADLE_Y[0], CRADLE_Y[1], FLOOR-1, FLOOR+RAIL_H))
    body = body - sub_all(cav, keep)
    cuts = tray_cutters()
    cuts += [Cyl('z', sx, sy, STANDOFF_HOLE/2, FLOOR+0.8, FLOOR+STANDOFF_H+0.5) for sx, sy in standoffs()]
    cuts += [Cyl('z', cx, cy, INSERT_HOLE/2, ZP-INSERT_DEPTH, ZP+0.5) for cx, cy, _ in POSTS]
    for x in PART_X:                                                       # cable windows in bay partitions
        for y in (22.0, 84.0):
            cuts.append(Box(x-0.5, x+PART_T+0.5, y-7, y+7, FLOOR+3.0, FLOOR+13.0))
    for x in (20.0, 80.0, 146.0):                                          # bays -> back zone
        cuts.append(Box(x-8, x+8, POCKET_Y1-0.5, Y_BZ0+0.5, FLOOR+3.0, FLOOR+13.0))
    for k in range(5):                                                     # floor vents under Pi
        cuts.append(Box(72, 120, 114+k*10-1.2, 114+k*10+1.2, -0.5, FLOOR+0.5))
    return sub_all(body, cuts)


def build_top():
    body = outer(ZP, H)
    body = body - Box(-1, OX+1, STEP_Y, OY+1, Z_SHELF, H+1)
    pocket = Box(POCKET_X0, POCKET_X0+POCKET_W, POCKET_Y0, POCKET_Y1, Z_SHELF, H+0.5)
    lips = []
    for x in (30, 62, 110, 142):
        lips.append(Box(x, x+14, POCKET_Y0-0.1, POCKET_Y0+1.2, H-2.0, H+1.0))
        lips.append(Box(x, x+14, POCKET_Y1-1.2, POCKET_Y1+0.1, H-2.0, H+1.0))
    body = body - sub_all(pocket, lips)
    cuts = []
    for x in (45.0, 127.0): cuts.append(Cyl('z', x, POCKET_Y0, 7.0, Z_SHELF-1.0, H+0.5))     # finger scoops
    ym = (POCKET_Y0+POCKET_Y1)/2                                                              # K06 USB-C / switch
    cuts.append(Box(-0.5, POCKET_X0+0.5, ym-8, ym+8, Z_SHELF+1.5, Z_SHELF+10.5))
    cuts.append(Box(POCKET_X0+POCKET_W-0.5, OX+0.5, ym-8, ym+8, Z_SHELF+1.5, Z_SHELF+10.5))
    wx, wy = LCD_WINDOW                                                                       # LCD window + bezel step
    cuts.append(Box(LCX-wx/2, LCX+wx/2, LCY-wy/2, LCY+wy/2, ZP-0.5, Z_SHELF+0.5))
    cuts.append(Box(LCX-40, LCX+40, LCY-28, LCY+28, Z_SHELF-1.2, Z_SHELF+0.5))
    ring = Box(LCX-42.4, LCX+42.4, LCY-29.8, LCY+29.8, Z_SHELF-0.6, Z_SHELF+0.5) - \
           Box(LCX-41.6, LCX+41.6, LCY-29.0, LCY+29.0, Z_SHELF-1.0, Z_SHELF+1.0)
    cuts.append(ring)                                                                         # frame groove
    for x0, x1 in ((14, 80), (92, 158)):                                                      # palm-rest accent grooves
        cuts.append(Box(x0, x1, 8.6, 9.2, H-0.6, H+0.5))
    zc = H-6.0                                                                                # LED light-bar channels (5.6 wide)
    cuts.append(Box(14, OX-14, -0.5, 1.5, zc-2.8, zc+2.8))
    cuts.append(Box(-0.5, 1.5, 14, STEP_Y-14, zc-2.8, zc+2.8))
    cuts.append(Box(OX-1.5, OX+0.5, 14, STEP_Y-14, zc-2.8, zc+2.8))
    for x in STATUS_LED_X: cuts.append(Cyl('z', x, STATUS_LED_Y, 1.6, ZP-0.5, Z_SHELF+0.5))   # 6 status LEDs
    cuts.append(Cyl('z', ENC[0], ENC[1], 3.7, ZP-0.5, Z_SHELF+0.5))                           # rotary encoder
    for bx, by in BTN: cuts.append(Cyl('z', bx, by, 6.1, ZP-0.5, Z_SHELF+0.5))                # 12 mm buttons
    gx, gy = GRILLE                                                                           # mesh grille (30 mm fan)
    for i in range(-3, 4):
        for j in range(-3, 4):
            if math.hypot(i*5.4, j*5.4) <= 11.5:
                cuts.append(Box(gx+i*5.4-1.5, gx+i*5.4+1.5, gy+j*5.4-1.5, gy+j*5.4+1.5, ZP-0.5, Z_SHELF+0.5))
    for k in range(7):                                                                        # GPS-side vents (left rack)
        y = 112 + 8*k; cuts.append(Box(8, 42, y-1.2, y+1.2, ZP-0.5, Z_SHELF+0.5))
    for (cx, cy, kind) in POSTS:
        cuts.append(Cyl('z', cx, cy, SCREW_HOLE/2, ZP-0.5, H+0.5))
        if kind == 'margin': cuts.append(Cyl('z', cx, cy, CBORE_D/2, H-CBORE_DEPTH, H+0.5))
    return sub_all(body, cuts)


def ghost_clearance(parts):
    rng = np.random.default_rng(7)
    bcx = (PART_X[0]+PART_T+PART_X[1])/2
    ghosts = {
        "Pi board": ((PI_X0, PI_Y0, FLOOR+STANDOFF_H), (PI_X0+PI_L, PI_Y0+PI_W, PCB_TOP)),
        "LCD stack": ((PI_X0+10, PI_Y0+2, PCB_TOP+LCD_TOP_ABOVE_PCB-4.6), (PI_X0+PI_L, PI_Y0+PI_W-2, PCB_TOP+LCD_TOP_ABOVE_PCB)),
        "SDR dongle": ((CRADLE_X[1]+0.3, CRADLE_Y[0]+1, FLOOR+0.2), (CRADLE_X[2]-0.3, CRADLE_Y[0]+87, FLOOR+15.5)),
        f"{BAT_CELLS}x18650 + holder": ((bcx-BAT_BAY_W/2+1.0, 9.0, FLOOR+0.2), (bcx+BAT_BAY_W/2-1.0, 89.0, FLOOR+CELL_D+2.5)),
        "Rii K06": ((POCKET_X0+KB_CLR, POCKET_Y0+KB_CLR, Z_SHELF+0.1), (POCKET_X0+KB_CLR+KB_W, POCKET_Y0+KB_CLR+KB_D_, H-2.1)),
    }
    ub, lb = PCB_TOP+15.6, PCB_TOP+LCD_TOP_ABOVE_PCB-4.6
    print(f"  Pi USB stack top {ub:.1f} vs LCD underside {lb:.1f} -> {'OK' if lb >= ub+0.2 else 'COLLIDES'}")
    for name, (lo, hi) in ghosts.items():
        lo, hi = np.array(lo), np.array(hi); P = rng.random((60000, 3))*(hi-lo)+lo
        hit = np.zeros(len(P), bool)
        for s in parts: hit |= s.inside(P)
        print(f"  clearance {name:18s}: {int(hit.sum())} of {len(P)} collide")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    os.makedirs(out, exist_ok=True)
    print(f"deck {OX} x {OY:.1f} x {H:.1f}  battery bay {BAT_BAY_W:.0f} wide x {PB_H:.1f} tall  LCD centre x={LCX:.1f} (deck centre {OX/2})")
    shapes = {}
    for name, fn, bb in (("tray", build_tray, ((0, 0, 0), (OX, OY, ZP))), ("top", build_top, ((0, 0, ZP), (OX, OY, H)))):
        shp = fn(); shapes[name] = shp; T = to_tris(shp.polys())
        write_stl(os.path.join(out, f"strikeback_deck3_{name}.stl"), T, f"deck3_{name}")
        mn, mx = T.reshape(-1, 3).min(0), T.reshape(-1, 3).max(0); bad, N = raycheck(T, shp, bb)
        print(f"{name:5s} tris={len(T)} ~{volume(T)/1000*1.24:.0f} g PLA size={np.round(mx-mn,1)} raycheck {bad}/{N}")
    ghost_clearance(list(shapes.values()))


if __name__ == '__main__':
    threading.stack_size(512*1024*1024); t = threading.Thread(target=main); t.start(); t.join()
