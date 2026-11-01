"""
Sandbox Empire — province layer prototype (Pygame).

Built on hex_engine_turns.py: same axial hex math, A*, Dijkstra flood-fill,
turn counter and movement points — now driving a province map.

Controls
  Left click      select province / ruler; choose target hex in an action mode
  Right click     cancel action / deselect
  I / E / L       province action: Irtás (clear) / Építés (build) / Lakoma (feast)
  1..9            pick a building option in the build menu
  K               centre on the king        N  next own province
  H               the king stays put this turn
  Arrows / WASD   pan the map (or drag with the middle mouse button)
  SPACE / ENTER   end turn (season)
  ESC             cancel; quit when nothing is selected

Requires: pygame (pip install pygame  — or pygame-ce)
"""

import math
import sys

import pygame

from hexcore import (EDGE_CORNERS, DIRECTIONS, axial_to_pixel, corner_pixel, hex_corners,
                     pixel_to_axial)
from world import (BUILDINGS, FEAST_COST, FEAST_PRESTIGE, LOYALTY, POP_NAMES, RELIGION,
                   RULER_MP, SEASON_WORK, SEASON_YIELD, SEASONS, TERRAIN, TOWN, VILLAGE,
                   FIELD, FACTIONS, World)

# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------
SCREEN_W, SCREEN_H = 1280, 800
PANEL_W = 330
TOP_H = 34
HEX_SIZE = 20
MAP_MARGIN = 30
PAN_SPEED = 600          # px / s
RULER_ANIM_SPEED = 6.0   # hexes / s
CAM_EASE = 12.0          # camera glide: share of the remaining distance per s

COL_BG = (20, 22, 27)
COL_PANEL = (32, 30, 28)
COL_PANEL_EDGE = (74, 64, 50)
COL_TEXT = (232, 226, 212)
COL_DIM = (150, 144, 132)
COL_BAD = (214, 120, 100)
COL_GOOD = (150, 200, 120)
COL_GOLD = (226, 190, 92)
COL_GRID = (0, 0, 0, 36)
COL_HOVER = (250, 236, 150)
COL_TARGET = (255, 230, 110)
COL_REACH = (250, 250, 250)

TERRAIN_COL = {
    "plains": (140, 158, 92),
    "forest": (64, 102, 60),
    "hills": (152, 140, 98),
    "marsh": (94, 116, 104),
    "mountain": (122, 118, 114),
    "water": (62, 98, 140),
    "sea": (40, 70, 112),
}
WHEAT = (204, 184, 106)
ROAD_COL = (120, 92, 62)
RIVER_COL = (104, 196, 236)   # bright cyan: distinct from the blue Alemann borders


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ----------------------------------------------------------------------
# Ruler sprite (the animated part of the engine's old Unit class)
# ----------------------------------------------------------------------
class RulerSprite:
    def __init__(self, hex_pos):
        self.hex = hex_pos
        self.path = []
        self.progress = 0.0
        self.pixel = axial_to_pixel(*hex_pos, HEX_SIZE)

    @property
    def moving(self):
        return bool(self.path)

    def set_path(self, path):
        if path and len(path) > 1:
            self.path = path[1:]
            self.progress = 0.0

    def snap(self, hex_pos):
        self.hex, self.path, self.progress = hex_pos, [], 0.0
        self.pixel = axial_to_pixel(*hex_pos, HEX_SIZE)

    def update(self, dt):
        if not self.path:
            return
        self.progress += RULER_ANIM_SPEED * dt
        while self.progress >= 1.0 and self.path:
            self.hex = self.path.pop(0)
            self.progress -= 1.0
        if self.path:
            ax, ay = axial_to_pixel(*self.hex, HEX_SIZE)
            bx, by = axial_to_pixel(*self.path[0], HEX_SIZE)
            t = self.progress
            self.pixel = (ax + (bx - ax) * t, ay + (by - ay) * t)
        else:
            self.pixel = axial_to_pixel(*self.hex, HEX_SIZE)
            self.progress = 0.0


# ----------------------------------------------------------------------
# Game
# ----------------------------------------------------------------------
class Game:
    def __init__(self, seed=None):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Sandbox Empire — tartományok")
        self.clock = pygame.time.Clock()
        fonts = "dejavusans,liberationsans,segoeui,arial,helvetica"
        self.font = pygame.font.SysFont(fonts, 15)
        self.font_small = pygame.font.SysFont(fonts, 12)
        self.font_label = pygame.font.SysFont(fonts, 13, bold=True)
        self.font_title = pygame.font.SysFont(fonts, 20, bold=True)

        self.world = World(seed=seed)
        self.ruler_sprite = RulerSprite(self.world.ruler.hex)

        self.selected = None        # Province or None
        self.ruler_selected = False
        self.mode = None            # None | 'clear' | 'build' | 'build_menu'
        self.menu_hex = None
        self.menu_options = []
        self.targets = set()
        self.reachable = {}
        self.preview_path = None
        self.buttons = []           # (rect, callback) rebuilt every frame
        self.dirty = True
        self.ruler_done = False     # the king has moved or held this turn
        self.focus = None           # "ruler" or a Province: the item awaiting orders
        self.pending = []           # 'ruler' and provinces still awaiting orders

        self._compute_bounds()
        self.map_surface = None
        self.view_w = SCREEN_W - PANEL_W
        self.view_h = SCREEN_H - TOP_H
        self.cam_target = None      # where the camera is gliding to
        self.center_on(self.world.ruler.hex, instant=True)
        self.dragging = False
        self.advance()

    # ---- coordinates --------------------------------------------------
    def _compute_bounds(self):
        xs, ys = [], []
        for h in self.world.tiles:
            x, y = axial_to_pixel(*h, HEX_SIZE)
            xs.append(x)
            ys.append(y)
        self.origin = (-min(xs) + HEX_SIZE + MAP_MARGIN, -min(ys) + HEX_SIZE + MAP_MARGIN)
        self.map_w = int(max(xs) - min(xs) + 2 * (HEX_SIZE + MAP_MARGIN))
        self.map_h = int(max(ys) - min(ys) + 2 * (HEX_SIZE + MAP_MARGIN))

    def to_map(self, h):
        x, y = axial_to_pixel(*h, HEX_SIZE)
        return x + self.origin[0], y + self.origin[1]

    def to_screen(self, h):
        x, y = self.to_map(h)
        return x - self.cam[0], y - self.cam[1] + TOP_H

    def pixel_to_screen(self, px, py):
        return px + self.origin[0] - self.cam[0], py + self.origin[1] - self.cam[1] + TOP_H

    def hex_at_screen(self, sx, sy):
        if sx >= self.view_w or sy < TOP_H:
            return None
        mx = sx + self.cam[0] - self.origin[0]
        my = sy - TOP_H + self.cam[1] - self.origin[1]
        h = pixel_to_axial(mx, my, HEX_SIZE)
        return h if h in self.world.tiles else None

    def clamp_cam(self):
        cx = max(0, min(self.cam[0], max(0, self.map_w - self.view_w)))
        cy = max(0, min(self.cam[1], max(0, self.map_h - self.view_h)))
        self.cam = [cx, cy]

    def center_on(self, h, instant=False):
        x, y = self.to_map(h)
        cx = max(0, min(x - self.view_w / 2, max(0, self.map_w - self.view_w)))
        cy = max(0, min(y - self.view_h / 2, max(0, self.map_h - self.view_h)))
        if instant:
            self.cam, self.cam_target = [cx, cy], None
        else:
            self.cam_target = (cx, cy)

    def update_cam(self, dt):
        if self.cam_target is None:
            return
        tx, ty = self.cam_target
        k = 1 - math.exp(-CAM_EASE * dt)
        self.cam = [self.cam[0] + (tx - self.cam[0]) * k, self.cam[1] + (ty - self.cam[1]) * k]
        if abs(tx - self.cam[0]) < 0.5 and abs(ty - self.cam[1]) < 0.5:
            self.cam, self.cam_target = [tx, ty], None

    # ---- selection / modes -------------------------------------------
    def select_province(self, p):
        self.selected = p
        self.ruler_selected = False
        self.reachable = {}
        self.cancel_mode()

    def select_ruler(self):
        self.ruler_selected = True
        self.cancel_mode()
        self.reachable = self.world.ruler_reachable()

    def cancel_mode(self):
        self.mode = None
        self.menu_hex = None
        self.menu_options = []
        self.targets = set()

    def enter_mode(self, mode):
        p = self.selected
        if not p or not p.is_player:
            return
        ok, reason, _ = self.world.can_order(p)
        if not ok:
            self.flash(reason)
            return
        if p.project:
            self.flash("A tartományban már folyik egy munka")
            return
        if mode == "clear":
            self.targets = {h for h in self.world.clear_targets(p)
                            if p.store >= self.world.clear_cost(p, h)[0]}
            if not self.targets:
                self.flash("Nincs irtható mező, vagy kevés a szolgáltatás")
                return
        elif mode == "build":
            self.targets = self.world.build_targets(p)
            if not self.targets:
                self.flash("Nincs hely építkezésre")
                return
        self.mode = mode
        self.ruler_selected = False
        self.reachable = {}

    def flash(self, text):
        self.world.add_log("» " + text)

    def do_feast(self):
        p = self.selected
        if p and self.world.feast(p):
            self.dirty = True
            self.order_given()
        elif p:
            self.flash(self.world.can_feast(p)[1])

    def pick_option(self, idx):
        if self.mode != "build_menu" or idx >= len(self.menu_options):
            return
        opt = self.menu_options[idx]
        if not opt["ok"]:
            self.flash(opt["reason"])
            return
        started = self.world.start_build(self.selected, self.menu_hex, opt)
        if started:
            self.world.add_log(f"{self.selected.name}: munka indul — {opt['label']}.")
            self.dirty = True
        self.cancel_mode()
        if started:
            self.order_given()

    # ---- turn flow: who still awaits orders ---------------------------
    def province_pending(self, p):
        w = self.world
        if not p.is_player:
            return False
        ok, _, au = w.can_order(p)
        if not ok or au:            # vassals away from the king act on their own
            return False
        if w.can_feast(p)[0]:
            return True
        if p.project:
            return False
        if any(p.store >= w.clear_cost(p, h)[0] for h in w.clear_targets(p)):
            return True
        return any(opt["ok"] for h in w.build_targets(p) for opt in w.build_options(p, h))

    def refresh_pending(self):
        w = self.world
        self.pending = [] if self.ruler_done or not w.ruler_reachable() else ["ruler"]
        self.pending += [p for p in w.player_provinces() if self.province_pending(p)]

    def order_given(self):
        # an order in the king's province while he has the focus is his action
        if self.focus == "ruler" and self.selected is self.world.ruler_province():
            self.ruler_done = True
        self.advance()

    def hold_ruler(self):
        """The king stays where he is this turn."""
        if self.focus == "ruler" or self.ruler_selected:
            self.ruler_done = True
            self.advance()

    def advance(self, prefer=None):
        """Focus the next unit/province awaiting orders, or prompt end of turn.

        Units (the king) are only focused and blink — clicking them selects
        them for movement; their province is selected so it can act instead.
        """
        self.refresh_pending()
        if not self.pending:
            self.focus = None
            self.flash("Minden parancs kiadva — SPACE: évszak vége")
            return
        order = ["ruler"] + self.world.player_provinces()
        if prefer in self.pending:
            nxt = prefer
        else:
            cur = self.focus if self.focus in order else self.selected
            i = order.index(cur) if cur in order else -1
            nxt = next(order[(i + k) % len(order)] for k in range(1, len(order) + 1)
                       if order[(i + k) % len(order)] in self.pending)
        if nxt == "ruler":
            self.select_province(self.world.ruler_province())
            self.center_on(self.world.ruler.hex)
        else:
            self.select_province(nxt)
            self.center_on(nxt.seat)
        self.focus = nxt

    def next_own_province(self):
        own = self.world.player_provinces()
        if not own:
            return
        i = own.index(self.selected) + 1 if self.selected in own else 0
        p = own[i % len(own)]
        self.select_province(p)
        self.center_on(p.seat)

    def end_turn(self):
        if self.ruler_sprite.moving:
            self.ruler_sprite.snap(self.world.ruler.hex)
        self.world.end_turn()
        self.dirty = True
        self.ruler_done = False
        self.focus = None
        self.select_province(None)    # start the round from the top
        self.advance()

    # ---- input --------------------------------------------------------
    def handle_click(self, pos):
        for rect, cb in self.buttons:
            if rect.collidepoint(pos):
                cb()
                return
        h = self.hex_at_screen(*pos)
        if h is None:
            return
        w = self.world

        if self.mode == "clear":
            if h in self.targets and w.start_clear(self.selected, h):
                w.add_log(f"{self.selected.name}: irtás indul ({TERRAIN[w.tiles[h].terrain]['name'].lower()}).")
                self.dirty = True
                self.cancel_mode()
                self.order_given()
            return
        if self.mode in ("build", "build_menu"):
            if h in self.targets:
                self.mode = "build_menu"
                self.menu_hex = h
                self.menu_options = w.build_options(self.selected, h)
            return

        if h == w.ruler.hex and not self.ruler_sprite.moving:
            if self.ruler_selected:
                self.select_province(w.province_at(h))
            else:
                self.select_ruler()
            return
        if self.ruler_selected and h in self.reachable and not self.ruler_sprite.moving:
            path = w.move_ruler(h)
            if path:
                self.ruler_sprite.set_path(path)
                self.reachable = {}
                self.ruler_done = True
            return
        self.select_province(w.province_at(h))

    def handle_key(self, key):
        if key == pygame.K_ESCAPE:
            if self.mode:
                self.cancel_mode()
            elif self.selected or self.ruler_selected:
                self.select_province(None)
            else:
                return False
        elif key in (pygame.K_SPACE, pygame.K_RETURN):
            self.end_turn()
        elif key == pygame.K_i:
            self.enter_mode("clear")
        elif key == pygame.K_e:
            self.enter_mode("build")
        elif key == pygame.K_l:
            self.do_feast()
        elif key == pygame.K_k:
            self.center_on(self.world.ruler.hex)
            self.select_ruler()
        elif key == pygame.K_n:
            self.next_own_province()
        elif key == pygame.K_h:
            self.hold_ruler()
        elif pygame.K_1 <= key <= pygame.K_9:
            self.pick_option(key - pygame.K_1)
        return True

    # ---- map surface (cached; rebuilt when the world changes) ---------
    def rebuild_map(self):
        w = self.world
        surf = pygame.Surface((self.map_w, self.map_h))
        surf.fill(COL_BG)
        tint = pygame.Surface((self.map_w, self.map_h), pygame.SRCALPHA)

        for h, t in w.tiles.items():
            cx, cy = self.to_map(h)
            pts = hex_corners(cx, cy, HEX_SIZE)
            base = TERRAIN_COL[t.terrain]
            if t.pop >= FIELD:
                base = mix(base, WHEAT, 0.45)
            pygame.draw.polygon(surf, base, pts)
            if t.owner is not None:
                pygame.draw.polygon(tint, t.owner.color + (46,), pts)
            pygame.draw.polygon(tint, COL_GRID, pts, 1)
            self.draw_terrain_detail(surf, t, cx, cy)
        surf.blit(tint, (0, 0))

        # rivers and roads
        ox, oy = self.origin
        majors = w.rivers[:w.n_major_rivers]
        for river in w.rivers + w.river_branches:   # along hex edges, corner to corner
            width = 6 if any(river is m for m in majors) else 4
            pts = [(x + ox, y + oy) for x, y in
                   (corner_pixel(c, HEX_SIZE) for c in river)]
            pygame.draw.lines(surf, RIVER_COL, False, pts, width)
            for p in pts:                       # round the joints
                pygame.draw.circle(surf, RIVER_COL, p, width // 2)
        for h, t in w.tiles.items():
            if not t.road:
                continue
            a = self.to_map(h)
            for d in DIRECTIONS[:3]:            # each pair once
                n = (h[0] + d[0], h[1] + d[1])
                if n in w.tiles and w.tiles[n].road:
                    pygame.draw.line(surf, ROAD_COL, a, self.to_map(n), 3)

        # settlements, improvements, projects
        for h, t in w.tiles.items():
            cx, cy = self.to_map(h)
            if t.pop >= VILLAGE:
                self.draw_houses(surf, cx, cy, t.pop == TOWN, t.imp is not None)
            elif t.pop == FIELD and t.imp is None:
                self.draw_field(surf, cx, cy)
            if t.imp:
                self.draw_improvement(surf, t.imp[0], t.imp[1], cx, cy)
        for p in w.provinces:
            if p.project:
                self.draw_project(surf, p)

        # borders: province edges thin, realm (faction) edges thick
        for h, t in w.tiles.items():
            if t.owner is None:
                continue
            cx, cy = self.to_map(h)
            pts = hex_corners(cx, cy, HEX_SIZE - 1)
            for i, d in enumerate(DIRECTIONS):
                n = (h[0] + d[0], h[1] + d[1])
                other = w.tiles[n].owner if n in w.tiles else None
                if other is t.owner:
                    continue
                realm_edge = other is None or other.faction != t.owner.faction
                a, b = EDGE_CORNERS[i]
                col = t.owner.color if realm_edge else mix(t.owner.color, (255, 255, 255), 0.35)
                pygame.draw.line(surf, col, pts[a], pts[b], 3 if realm_edge else 1)

        # province labels under the seats
        for p in w.provinces:
            cx, cy = self.to_map(p.seat)
            self.draw_label(surf, p.name, cx, cy + HEX_SIZE * 0.95,
                            COL_GOLD if p.is_player else COL_TEXT)

        self.map_surface = surf
        self.dirty = False

    def draw_terrain_detail(self, s, t, cx, cy):
        if t.pop:
            return
        if t.terrain == "forest":
            for dx, dy in ((-7, 2), (0, -5), (7, 3)):
                pygame.draw.polygon(s, (40, 74, 42), [(cx + dx, cy + dy - 7),
                                    (cx + dx - 5, cy + dy + 3), (cx + dx + 5, cy + dy + 3)])
        elif t.terrain == "hills":
            pygame.draw.arc(s, (118, 108, 74), (cx - 11, cy - 3, 12, 10), 0, math.pi, 2)
            pygame.draw.arc(s, (118, 108, 74), (cx - 1, cy - 6, 12, 10), 0, math.pi, 2)
        elif t.terrain == "mountain":
            pygame.draw.polygon(s, (92, 88, 86), [(cx, cy - 10), (cx - 10, cy + 6), (cx + 10, cy + 6)])
            pygame.draw.polygon(s, (226, 226, 230), [(cx, cy - 10), (cx - 3, cy - 5), (cx + 3, cy - 5)])
        elif t.terrain == "marsh":
            for dy in (-4, 2, 8):
                pygame.draw.line(s, (70, 96, 90), (cx - 7, cy + dy), (cx + 7, cy + dy), 1)

    def draw_field(self, s, cx, cy):
        col = mix(WHEAT, (120, 96, 50), 0.35)
        for k in (-6, 0, 6):
            pygame.draw.line(s, col, (cx - 9 + k * 0.3, cy + k - 3), (cx + 9 + k * 0.3, cy + k - 3), 1)

    def draw_houses(self, s, cx, cy, town, small):
        spots = [(-7, 3), (2, 6), (6, -3), (-3, -5), (-10, -4), (9, 5)] if town else [(-6, 4), (5, 5), (1, -4)]
        if small:
            spots = [(-11, 7), (11, 7)] + ([(0, 11)] if town else [])
        wall = (210, 196, 170) if town else (186, 160, 120)
        roof = (150, 64, 50) if town else (120, 84, 50)
        for dx, dy in spots:
            x, y = cx + dx, cy + dy
            pygame.draw.rect(s, wall, (x - 3, y - 2, 6, 5))
            pygame.draw.polygon(s, roof, [(x - 4, y - 2), (x + 4, y - 2), (x, y - 6)])

    def draw_improvement(self, s, line, tier, cx, cy):
        if line == "fort":
            cols = [(124, 92, 58), (150, 108, 62), (150, 148, 144), (190, 188, 186)]
            c = cols[tier]
            if tier == 0:
                pygame.draw.circle(s, c, (cx, cy), 8, 3)
            elif tier == 1:
                pygame.draw.rect(s, c, (cx - 8, cy - 6, 16, 12), 3)
                for k in range(-8, 9, 4):
                    pygame.draw.line(s, c, (cx + k, cy - 6), (cx + k, cy - 9), 2)
            else:
                pygame.draw.rect(s, c, (cx - 5, cy - 10, 10, 16))
                pygame.draw.rect(s, (60, 56, 52), (cx - 2, cy + 1, 4, 5))
                if tier == 3:
                    pygame.draw.rect(s, c, (cx - 12, cy - 4, 6, 10))
                    pygame.draw.rect(s, c, (cx + 6, cy - 4, 6, 10))
        elif line == "church":
            c = [(176, 140, 90), (220, 214, 200), (232, 228, 218), (246, 240, 226)][tier]
            if tier >= 2:
                pygame.draw.rect(s, c, (cx - 8, cy - 2, 16, 8))
            if tier == 3:
                pygame.draw.rect(s, c, (cx - 9, cy - 10, 4, 8))
                pygame.draw.rect(s, c, (cx + 5, cy - 10, 4, 8))
            pygame.draw.line(s, c, (cx, cy - 10), (cx, cy + 6), 3)
            pygame.draw.line(s, c, (cx - 5, cy - 5), (cx + 5, cy - 5), 3)
        elif line == "monastery":
            c = (196, 180, 150)
            pygame.draw.rect(s, c, (cx - 7, cy - 3, 14, 9))
            pygame.draw.polygon(s, (110, 70, 50), [(cx - 8, cy - 3), (cx + 8, cy - 3), (cx, cy - 9)])
            pygame.draw.line(s, (240, 236, 220), (cx, cy - 13), (cx, cy - 8), 2)
        elif line == "market":
            pygame.draw.circle(s, COL_GOLD, (cx, cy), 6 + tier)
            pygame.draw.circle(s, (150, 112, 40), (cx, cy), 6 + tier, 2)
        elif line == "pfalz":
            pts = [(cx - 9, cy + 5), (cx - 9, cy - 5), (cx - 4, cy), (cx, cy - 8),
                   (cx + 4, cy), (cx + 9, cy - 5), (cx + 9, cy + 5)]
            pygame.draw.polygon(s, COL_GOLD, pts)
            pygame.draw.polygon(s, (150, 112, 40), pts, 2)
        # tier pips
        n = tier + 1
        for k in range(n):
            x = cx - (n - 1) * 3 + k * 6
            pygame.draw.circle(s, (250, 246, 230), (int(x), int(cy + 12)), 2)

    def draw_project(self, s, p):
        pr = p.project
        cx, cy = self.to_map(pr["hex"])
        pts = hex_corners(cx, cy, HEX_SIZE - 4)
        for i in range(0, 6, 2):            # dashed "scaffold" outline
            pygame.draw.line(s, (240, 220, 160), pts[i], pts[(i + 1) % 6], 2)
        if pr["kind"] == "clear":
            for dx, dy in ((-5, 0), (4, -3), (2, 6)):
                pygame.draw.rect(s, (110, 80, 50), (cx + dx - 2, cy + dy - 2, 4, 4))
        done = 1 - max(0.0, pr["left"]) / pr["total"]
        bar = pygame.Rect(cx - 12, cy - HEX_SIZE + 4, 24, 4)
        pygame.draw.rect(s, (30, 30, 30), bar)
        pygame.draw.rect(s, COL_GOLD, (bar.x, bar.y, int(bar.w * done), bar.h))

    def draw_label(self, s, text, cx, cy, col):
        img = self.font_label.render(text, True, col)
        shadow = self.font_label.render(text, True, (0, 0, 0))
        x, y = cx - img.get_width() / 2, cy - img.get_height() / 2
        for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            s.blit(shadow, (x + ox, y + oy))
        s.blit(img, (x, y))

    # ---- frame drawing ------------------------------------------------
    def draw(self, hover):
        if self.dirty or self.map_surface is None:
            self.rebuild_map()
        self.screen.fill(COL_BG)
        self.screen.blit(self.map_surface, (-self.cam[0], TOP_H - self.cam[1]))
        w = self.world
        self.buttons = []

        # selected province outline
        if self.selected:
            for h in self.selected.territory:
                cx, cy = self.to_screen(h)
                if -30 < cx < self.view_w + 30 and 0 < cy < SCREEN_H + 30:
                    pts = hex_corners(cx, cy, HEX_SIZE)
                    for i, d in enumerate(DIRECTIONS):
                        n = (h[0] + d[0], h[1] + d[1])
                        if n not in self.selected.territory:
                            a, b = EDGE_CORNERS[i]
                            pygame.draw.line(self.screen, (255, 248, 220), pts[a], pts[b], 2)

        # action targets
        for h in self.targets:
            cx, cy = self.to_screen(h)
            pygame.draw.polygon(self.screen, COL_TARGET, hex_corners(cx, cy, HEX_SIZE - 4), 2)
        if self.menu_hex:
            cx, cy = self.to_screen(self.menu_hex)
            pygame.draw.polygon(self.screen, (255, 255, 255), hex_corners(cx, cy, HEX_SIZE - 2), 3)

        # ruler reach + path preview
        for h in self.reachable:
            cx, cy = self.to_screen(h)
            pygame.draw.polygon(self.screen, COL_REACH, hex_corners(cx, cy, HEX_SIZE - 6), 1)
        if self.ruler_selected and hover and hover != w.ruler.hex and not self.ruler_sprite.moving:
            path, cost = w.ruler_path(hover)
            if path and len(path) > 1:
                pts = [self.to_screen(h) for h in path]
                col = (250, 250, 250) if cost <= w.ruler.mp else (130, 130, 130)
                pygame.draw.lines(self.screen, col, False, pts, 2)
                lab = self.font_small.render(f"{cost}/{w.ruler.mp}", True, col)
                self.screen.blit(lab, (pts[-1][0] + 8, pts[-1][1] - 16))

        # hover
        if hover:
            cx, cy = self.to_screen(hover)
            pygame.draw.polygon(self.screen, COL_HOVER, hex_corners(cx, cy, HEX_SIZE), 2)

        self.draw_ruler()
        self.draw_hover_info(hover)
        self.draw_end_prompt()
        self.draw_topbar()
        self.draw_panel()
        pygame.display.flip()

    def draw_end_prompt(self):
        """Pulsing, clickable banner once nothing awaits orders."""
        if self.pending:
            return
        col = mix(COL_GOLD, COL_TEXT, 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 300))
        img = self.font_label.render("Minden parancs kiadva — SPACE / ENTER: évszak vége", True, col)
        box = pygame.Rect(0, 0, img.get_width() + 28, 32)
        box.midtop = (self.view_w // 2, TOP_H + 10)
        pygame.draw.rect(self.screen, (20, 20, 20), box)
        pygame.draw.rect(self.screen, col, box, 2)
        self.screen.blit(img, img.get_rect(center=box.center))
        self.buttons.append((box, self.end_turn))

    def draw_ruler(self):
        px, py = self.pixel_to_screen(*self.ruler_sprite.pixel)
        px, py = int(px), int(py)
        if self.ruler_selected:
            pygame.draw.circle(self.screen, COL_TARGET, (px, py), 13, 2)
        elif self.focus == "ruler" and (pygame.time.get_ticks() // 400) % 2 == 0:
            pygame.draw.circle(self.screen, COL_TARGET, (px, py), 15, 3)   # awaits orders
        # banner on a pole
        pygame.draw.line(self.screen, (60, 40, 24), (px - 4, py + 9), (px - 4, py - 14), 2)
        pygame.draw.polygon(self.screen, FACTIONS["player"]["color"],
                            [(px - 3, py - 14), (px + 9, py - 11), (px - 3, py - 7)])
        pygame.draw.circle(self.screen, (236, 210, 120), (px + 2, py + 2), 6)
        pygame.draw.circle(self.screen, (60, 40, 24), (px + 2, py + 2), 6, 1)
        mp = self.world.ruler.mp
        if mp < RULER_MP:
            lab = self.font_small.render(str(mp), True, (255, 255, 255))
            self.screen.blit(lab, (px + 8, py + 2))

    def draw_hover_info(self, hover):
        if not hover:
            return
        w = self.world
        t = w.tiles[hover]
        parts = [TERRAIN[t.terrain]["name"]]
        if t.pop:
            parts.append(POP_NAMES[t.pop])
        if t.imp:
            parts.append(BUILDINGS[t.imp[0]]["tiers"][t.imp[1]])
        if t.river:
            parts.append("folyó")
        if t.road:
            parts.append("római út")
        if t.owner:
            parts.append(t.owner.name)
        img = self.font.render(" · ".join(parts), True, COL_TEXT)
        box = pygame.Rect(8, SCREEN_H - 30, img.get_width() + 16, 24)
        pygame.draw.rect(self.screen, (20, 20, 20), box)
        pygame.draw.rect(self.screen, COL_PANEL_EDGE, box, 1)
        self.screen.blit(img, (16, SCREEN_H - 27))

    def draw_topbar(self):
        w = self.world
        pygame.draw.rect(self.screen, COL_PANEL, (0, 0, SCREEN_W, TOP_H))
        pygame.draw.line(self.screen, COL_PANEL_EDGE, (0, TOP_H - 1), (SCREEN_W, TOP_H - 1))
        age = w.year - w.ruler.born
        items = [
            (f"Kr. u. {w.year}, {SEASONS[w.season].lower()}", COL_GOLD),
            (f"Ezüst {w.silver:.0f}", COL_TEXT),
            (f"Presztízs {w.prestige}", COL_TEXT),
            (f"Tekintély {w.au}/20 (+{w.au_income()})", COL_TEXT),
            (f"{w.ruler.name}, {age} éves", COL_DIM),
            (f"Parancsra vár: {len(self.pending)} · SPACE: évszak vége", COL_DIM)
            if self.pending else ("Minden parancs kiadva — SPACE: évszak vége", COL_GOLD),
        ]
        x = 12
        for text, col in items:
            img = self.font.render(text, True, col)
            self.screen.blit(img, (x, 8))
            x += img.get_width() + 26

    # ---- side panel ---------------------------------------------------
    def draw_panel(self):
        x0 = SCREEN_W - PANEL_W
        pygame.draw.rect(self.screen, COL_PANEL, (x0, TOP_H, PANEL_W, SCREEN_H - TOP_H))
        pygame.draw.line(self.screen, COL_PANEL_EDGE, (x0, TOP_H), (x0, SCREEN_H))
        self.px, self.py = x0 + 14, TOP_H + 12

        if self.focus == "ruler" and not self.ruler_selected:
            self.text("A király parancsra vár: kattints rá a mozgatáshoz, "
                      "vagy [H] — helyben marad.", COL_TARGET, self.font_small)
            self.py += 6
        if self.ruler_selected:
            self.panel_ruler()
        elif self.selected:
            self.panel_province(self.selected)
        else:
            self.text("Kattints egy tartományra,", COL_DIM)
            self.text("vagy a király zászlajára.", COL_DIM)

        # log at the bottom
        y = SCREEN_H - 12 - 15 * 9
        pygame.draw.line(self.screen, COL_PANEL_EDGE, (x0 + 10, y - 8), (SCREEN_W - 10, y - 8))
        lines = []
        for entry in reversed(self.world.log[-12:]):
            lines.extend(self.wrap(entry, self.font_small, PANEL_W - 28))
            if len(lines) >= 10:
                break
        for i, line in enumerate(lines[:10]):
            col = COL_TEXT if i < 2 else COL_DIM
            self.screen.blit(self.font_small.render(line, True, col), (x0 + 14, y + i * 13))

    def wrap(self, text, font, width):
        words, lines, cur = text.split(), [], ""
        for wd in words:
            test = (cur + " " + wd).strip()
            if font.size(test)[0] <= width:
                cur = test
            else:
                lines.append(cur)
                cur = wd
        if cur:
            lines.append(cur)
        return lines

    def text(self, s, col=COL_TEXT, font=None, gap=3):
        font = font or self.font
        for line in self.wrap(s, font, PANEL_W - 28):
            img = font.render(line, True, col)
            self.screen.blit(img, (self.px, self.py))
            self.py += img.get_height() + gap

    def button(self, label, cb, enabled=True, hint=None):
        rect = pygame.Rect(self.px, self.py, PANEL_W - 28, 26)
        pygame.draw.rect(self.screen, (58, 52, 42) if enabled else (40, 38, 34), rect)
        pygame.draw.rect(self.screen, COL_PANEL_EDGE if enabled else (52, 48, 42), rect, 1)
        img = self.font.render(label, True, COL_TEXT if enabled else COL_DIM)
        self.screen.blit(img, (rect.x + 8, rect.y + 4))
        self.py += 30
        if enabled:
            self.buttons.append((rect, cb))
        if hint:
            self.text(hint, COL_BAD if not enabled else COL_DIM, self.font_small)
            self.py += 2

    def panel_ruler(self):
        w = self.world
        r = w.ruler
        self.text(r.name, COL_GOLD, self.font_title, 6)
        self.text(f"A száli frankok királya · {w.year - r.born} éves")
        rp = w.ruler_province()
        self.text(f"Tartózkodik: {rp.name if rp else 'vadonban'}")
        self.text(f"Mozgás: {r.mp}/{RULER_MP}")
        self.py += 8
        self.text("Ahol a király időzik: a vazallus ingyen kap parancsot, "
                  "lakoma rendezhető, a hűség javul. A rég nem látott "
                  "tartományok hűsége kopik.", COL_DIM, self.font_small)
        self.py += 6
        self.text("Kattints egy kijelölt mezőre a mozgáshoz.", COL_DIM, self.font_small)
        if not self.ruler_done:
            self.py += 6
            self.button("[H] Helyben marad ebben az évszakban", self.hold_ruler)

    def panel_province(self, p):
        w = self.world
        self.text(p.name, COL_GOLD, self.font_title, 6)
        status = {"royal": "Királyi birtok", "vassal": "Vazallus"}.get(
            p.status, f"Független — {FACTIONS[p.faction]['name']}")
        self.text(status, COL_DIM)
        self.text(f"Úr: {p.lord.name} ({p.lord.trait})")
        if p.is_player:
            col = [COL_BAD, COL_BAD, COL_TEXT, COL_GOOD][p.loyalty]
            self.text(f"Hűség: {LOYALTY[p.loyalty]}", col)
            ago = w.turn - p.last_visit
            when = "most" if w.ruler_present(p) else (f"{ago} évszaka" if ago else "nemrég")
            self.text(f"Királyi látogatás: {when}", COL_DIM, self.font_small)
        self.text(f"Vallás: {RELIGION[p.religion]}")
        renders, silver = w.yields(p)
        now = renders * SEASON_YIELD[w.season]
        self.text(f"Raktár: {p.store:.0f} szolgáltatás (+{now:.0f} ebben az évszakban)")
        if p.is_player:
            self.text(f"Ezüst: +{silver:.0f} / évszak")
        pops = [0, 0, 0, 0]
        for h in p.settled:
            pops[w.tiles[h].pop] += 1
        self.text(f"Szántó {pops[1]} · Falu {pops[2]} · Városnegyed {pops[3]}")
        self.text(f"Lovagok: {w.knights(p)} · Munkaerő ×{w.labour(p):.1f}")
        if p.project:
            pr = p.project
            per = w.labour(p) * SEASON_WORK[w.season]
            left = max(1, math.ceil(pr["left"] / max(per, 0.01)))
            self.text(f"Munka: {pr['label']} — kb. {left} évszak", COL_GOLD)
        else:
            self.text("Munka: nincs", COL_DIM)
        self.py += 8

        if not p.is_player:
            return
        ok, reason, au = w.can_order(p)
        if self.mode == "build_menu":
            self.panel_build_menu(p)
            return
        if self.mode in ("clear", "build"):
            what = "irtandó mezőt" if self.mode == "clear" else "építési helyet"
            self.text(f"Válassz egy {what} a térképen. (Jobb klikk: mégse)", COL_TARGET)
            return
        if not ok:
            self.text(reason, COL_DIM)
        elif au:
            self.text(reason, COL_GOLD, self.font_small)
        free = ok and not p.project
        self.button("[I] Irtás — új szántó", lambda: self.enter_mode("clear"), free)
        self.button("[E] Építés", lambda: self.enter_mode("build"), free)
        if p.project:
            self.text("Egy tartományban egyszerre egy munka folyhat.", COL_DIM, self.font_small)
            self.py += 4
        f_ok, f_reason = w.can_feast(p)
        self.button(f"[L] Lakoma ({FEAST_COST} szolg. → +{FEAST_PRESTIGE} presztízs)",
                    self.do_feast, f_ok, None if f_ok else f_reason)

    def panel_build_menu(self, p):
        t = self.world.tiles[self.menu_hex]
        self.text(f"Építés itt: {POP_NAMES[t.pop]}"
                  + (f" ({BUILDINGS[t.imp[0]]['tiers'][t.imp[1]]})" if t.imp else ""), COL_TARGET)
        self.py += 4
        for i, opt in enumerate(self.menu_options[:9]):
            label = f"[{i + 1}] {opt['label']} — {opt['cost']} szolg., {opt['turns']} évsz."
            self.button(label, (lambda k=i: self.pick_option(k)), opt["ok"],
                        None if opt["ok"] else opt["reason"])

    # ---- main loop ----------------------------------------------------
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            mx, my = pygame.mouse.get_pos()
            hover = self.hex_at_screen(mx, my)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    running = self.handle_key(event.key)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.handle_click(event.pos)
                    elif event.button == 2:
                        self.dragging = True
                    elif event.button == 3:
                        if self.mode:
                            self.cancel_mode()
                        else:
                            self.select_province(None)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 2:
                    self.dragging = False
                elif event.type == pygame.MOUSEMOTION and self.dragging:
                    self.cam_target = None
                    self.cam[0] -= event.rel[0]
                    self.cam[1] -= event.rel[1]
                    self.clamp_cam()

            keys = pygame.key.get_pressed()
            dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
            dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
            if dx or dy:
                self.cam_target = None
                self.cam[0] += dx * PAN_SPEED * dt
                self.cam[1] += dy * PAN_SPEED * dt
                self.clamp_cam()

            self.update_cam(dt)
            was_moving = self.ruler_sprite.moving
            self.ruler_sprite.update(dt)
            if was_moving and not self.ruler_sprite.moving and self.ruler_selected:
                self.advance(prefer=self.world.ruler_province())   # after arrival

            self.draw(hover)
        pygame.quit()


if __name__ == "__main__":
    Game(seed=int(sys.argv[1]) if len(sys.argv) > 1 else None).run()
