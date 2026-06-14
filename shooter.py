"""
TopDown Shooter v6 - with Boss System + COOP Mode
操作：WASD移动 鼠标瞄准 左键射击 M换弹 ESC暂停
"""
import pygame, math, random, sys, array, struct, json, os, hashlib

def get_app_dir():
    """获取 exe 或脚本所在目录（兼容 PyInstaller 打包）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

try:
    import ctypes
    if sys.platform == "win32":
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
except Exception:
    pass

# === Config ===
W, H    = 800, 600
FPS    = 60
SR     = 22050

# === Colors ===
C_BG       = (18,  18,  28)
C_GRID     = (28,  28,  42)
C_PLAYER   = (70, 200, 120)
C_PLAYER_G = (160, 220, 180)
C_PLAYER2   = (70, 130, 220)
C_PLAYER2_G = (130, 170, 240)
C_BULLET   = (255, 240,  70)
C_E1       = (210,  55,  55)
C_E2       = (220, 115,  25)
C_E3       = (150,  40, 195)
C_HP_BG    = (55,  18,  18)
C_HP_FG    = (210,  55,  55)
C_TEXT     = (235, 235, 235)
C_TEXT_D   = (130, 130, 150)
C_ACCENT   = (255, 215,  50)
C_WARN     = (255,  90,  90)
C_COVER    = (65,  65,  90)
C_COVER_E  = (90,  90, 120)
C_POVER_BG = (0,   0,   0, 170)
C_BOSS     = (255, 50,  50)
C_BOSS_2   = (255, 180, 30)
C_BOSS_BUL = (255, 100, 60)

# === Game Params ===
PLAYER_SPD = 3.5
PLAYER_R   = 14
BULLET_SPD = 9.5
BULLET_R   = 4
SHOOT_CD   = 160
MAX_BULLETS= 120
RELOAD_MS  = 1400

# === Globals (cheat-overridable) ===
g_bullet_r   = BULLET_R
g_shoot_cd   = SHOOT_CD
g_bullet_dmg = 1
g_reload_ms  = RELOAD_MS
g_player_spd = PLAYER_SPD
g_bullet_spd = BULLET_SPD

# === Game Modes ===
# "normal" "hard" "endless" "speedrun"
GAME_MODES = ["NORMAL", "HARD", "ENDLESS", "SPEEDRUN", "COOP"]
MODE_DESC   = {
    "NORMAL":   "Standard difficulty",
    "HARD":     "2x enemy HP & speed",
    "ENDLESS":  "No level limit, ever harder",
    "SPEEDRUN": "30s per level or lose!",
    "COOP":     "2P co-op! P1:WASD+mouse P2:Arrows+RShift",
}
SPEEDRUN_TIME = 30000  # ms per level

# === Levels ===
LEVELS = [
    (8,   2000, 0, 12, 48),
    (12,  1800, 2, 12, 48),
    (16,  1600, 3, 15, 60),
    (20,  1400, 3, 15, 60),
    (25,  1200, 4, 18, 72),
    (30,  1000, 4, 18, 72),
    (35,   850, 5, 22, 88),
    (40,   700, 5, 22, 88),
    (50,   600, 6, 26, 104),
    (60,   500, 6, 30, 120),
]
BOSS_LEVELS = {4, 9}
BOSS_HP     = [50, 100]
BOSS_R      = 36
BOSS_FIRE_CD= [900, 600]
BOSS_BUL_SPD= 3.5


def dist(a, b):
    dx, dy = a[0]-b[0], a[1]-b[1]
    return math.sqrt(dx*dx + dy*dy)

def angle_to(src, dst):
    return math.atan2(dst[1]-src[1], dst[0]-src[0])

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def scale_mouse(mx, my, screen, surf):
    """将屏幕鼠标坐标转换为逻辑坐标 (800x600)"""
    sw, sh = screen.get_size()
    return mx * surf.get_width() / sw, my * surf.get_height() / sh

# === Account System ===
USER_FILE = os.path.join(get_app_dir(), "users.json")

def load_users():
    if not os.path.exists(USER_FILE):
        return {}
    try:
        with open(USER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_users(users):
    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def hash_pwd(pwd):
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()

def verify_user(username, pwd):
    users = load_users()
    return users.get(username) == hash_pwd(pwd)

def register_user(username, pwd):
    users = load_users()
    if username in users:
        return False
    users[username] = hash_pwd(pwd)
    save_users(users)
    return True

# === TextInput ===
class TextInput:
    _scale = None  # (screen_w, screen_h, surf_w, surf_h)
    @classmethod
    def set_scale(cls, screen, surf):
        sw, sh = screen.get_size()
        cls._scale = (sw, sh, surf.get_width(), surf.get_height())
    def __init__(self, x, y, w, h, font, mask=False):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = ""
        self.mask = mask
        self.font = font
        self.active = False
        self.cursor_t = 0
    def _scaled_pos(self, pos):
        if self._scale:
            sw, sh, lw, lh = self._scale
            return pos[0] * lw / sw, pos[1] * lh / sh
        return pos
    def handle_event(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            mx, my = self._scaled_pos(ev.pos)
            self.active = self.rect.collidepoint(mx, my)
        if not self.active:
            return
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif ev.key == pygame.K_RETURN:
                pass
            elif ev.key == pygame.K_TAB:
                pass
            elif len(self.text) < 20:
                self.text += ev.unicode
    def draw(self, surf):
        col = (255,255,255) if self.active else (180,180,180)
        pygame.draw.rect(surf, (45,45,65), self.rect, border_radius=10)
        pygame.draw.rect(surf, col, self.rect, 5, border_radius=10)
        display = "*" * len(self.text) if self.mask else self.text
        txt = self.font.render(display, True, (235,235,235))
        surf.blit(txt, (self.rect.x+19, self.rect.y + (self.rect.h-txt.get_height())//2))
        if self.active:
            self.cursor_t += 1
            if self.cursor_t % 60 < 30:
                cx = self.rect.x + 19 + txt.get_width() + 5
                pygame.draw.line(surf, (235,235,235), (cx, self.rect.y+14), (cx, self.rect.y+self.rect.h-14), 5)
        return self.active
    def get(self):
        return self.text
    def set(self, s):
        self.text = s
    def clear(self):
        self.text = ""

    # === Sound ===
def make_sound(gen_func):
    try:
        buf = gen_func()
        if buf:
            return pygame.mixer.Sound(buffer=buf)
    except Exception:
        pass
    return None

# 安全的声音播放辅助函数
def safe_play(sound_obj):
    """安全地播放声音，如果声音对象为None则忽略"""
    if sound_obj:
        try:
            sound_obj.play()
        except Exception:
            pass

def tone(freq, dur, vol=0.3, wave="sine"):
    n = int(SR * dur)
    buf = bytearray(n * 2)
    for i in range(n):
        t = i / SR
        env = max(0.0, 1.0 - t / dur)
        v = 0.0
        if wave == "sine":
            v = math.sin(2.0 * math.pi * freq * t)
        elif wave == "square":
            v = 1.0 if math.sin(2.0 * math.pi * freq * t) >= 0 else -1.0
        elif wave == "saw":
            v = 2.0 * ((freq * t) % 1.0) - 1.0
        elif wave == "noise":
            v = random.random() * 2.0 - 1.0
        sample = int(max(-32767, min(32767, v * vol * env * 32767)))
        b = struct.pack("<h", sample)
        buf[i*2]   = b[0]
        buf[i*2+1] = b[1]
    return bytes(buf)

def init_sounds():
    snd = {}
    snd["shoot"]      = make_sound(lambda: tone(1200,0.04,0.25,"noise")  + tone(600,0.06,0.20,"square"))
    snd["hit"]        = make_sound(lambda: tone(900,0.05,0.18,"square") + tone(500,0.06,0.15,"saw"))
    snd["explode"]   = make_sound(lambda: tone(300,0.08,0.30,"noise")  + tone(120,0.18,0.25,"saw"))
    snd["reload_s"]   = make_sound(lambda: tone(1800,0.03,0.15,"sine")   + tone(1400,0.04,0.12,"sine"))
    snd["reload_d"]   = make_sound(lambda: tone(2400,0.02,0.20,"square") + tone(1600,0.05,0.18,"sine"))
    snd["player_hit"] = make_sound(lambda: tone(200,0.12,0.30,"saw")    + tone(100,0.10,0.20,"noise"))
    snd["level_up"]   = make_sound(lambda: tone(523,0.10,0.25,"sine")   + tone(659,0.10,0.25,"sine") + tone(784,0.20,0.30,"sine"))
    snd["game_over"]  = make_sound(lambda: tone(400,0.15,0.30,"sine")   + tone(300,0.15,0.25,"sine") + tone(180,0.40,0.30,"saw"))
    snd["pickup"]    = make_sound(lambda: tone(1000,0.04,0.18,"sine")  + tone(1400,0.06,0.20,"sine"))
    snd["empty"]      = make_sound(lambda: tone(200,0.06,0.20,"square"))
    snd["boss_warn"]  = make_sound(lambda: tone(150,0.30,0.35,"saw")    + tone(100,0.40,0.30,"noise"))
    snd["boss_fire"]  = make_sound(lambda: tone(400,0.05,0.20,"noise")  + tone(250,0.06,0.15,"square"))
    snd["boss_die"]   = make_sound(lambda: tone(200,0.15,0.35,"noise")  + tone(80,0.40,0.30,"saw"))
    return snd

# === Cover ===
class Cover:
    __slots__ = ("rect",)
    def __init__(s, x, y, w, h):
        s.rect = pygame.Rect(x, y, w, h)
    def draw(s, surf):
        pygame.draw.rect(surf, (65,65,90),   s.rect, border_radius=4)
        pygame.draw.rect(surf, (90,90,120),  s.rect, 2, border_radius=4)
    def blocks_circle(s, x, y, r):
        cx = clamp(x, s.rect.left,   s.rect.right)
        cy = clamp(y, s.rect.top,    s.rect.bottom)
        return (cx-x)**2 + (cy-y)**2 < r*r
    def blocks_point(s, x, y, margin=0):
        return s.rect.inflate(margin*2, margin*2).collidepoint(x, y)

# === Particle ===
class Particle:
    __slots__ = ("x","y","vx","vy","life","max_life","color","r")
    def __init__(s, x, y, color, spd=2.5, life=22):
        a  = random.uniform(0, math.pi*2)
        sp = random.uniform(spd*0.3, spd)
        s.x, s.y = x, y
        s.vx = math.cos(a)*sp; s.vy = math.sin(a)*sp
        s.life = s.max_life = life + random.randint(-4, 4)
        s.color = color; s.r = random.randint(2, 5)
    def update(s):
        s.x += s.vx; s.y += s.vy
        s.vx *= 0.91; s.vy *= 0.91; s.life -= 1
    def draw(s, surf):
        if s.life <= 0: return
        alpha = max(0.15, s.life / s.max_life)
        r = max(1, int(s.r * alpha))
        c = tuple(int(v*alpha) for v in s.color)
        pygame.draw.circle(surf, c, (int(s.x), int(s.y)), r)

# === Bullet ===
class Bullet:
    __slots__ = ("x","y","vx","vy","alive","dmg")
    def __init__(s, x, y, angle, dmg=1):
        s.x, s.y = float(x), float(y)
        s.vx = math.cos(angle) * g_bullet_spd
        s.vy = math.sin(angle) * g_bullet_spd
        s.alive = True; s.dmg = dmg
    def update(s, covers, g_br):
        s.x += s.vx; s.y += s.vy
        if not (-30 <= s.x <= W+30 and -30 <= s.y <= H+30):
            s.alive = False; return
        for cv in covers:
            if cv.blocks_circle(s.x, s.y, g_br + 2):
                s.alive = False; return
    def draw(s, surf, g_br):
        if not s.alive: return
        br = max(1, g_br)
        pygame.draw.circle(surf, C_BULLET, (int(s.x), int(s.y)), br)
        tx = int(s.x - s.vx * 1.8)
        ty = int(s.y - s.vy * 1.8)
        pygame.draw.line(surf, (190,175,35), (tx,ty), (int(s.x),int(s.y)), 2)

# === BossBullet ===
class BossBullet:
    __slots__ = ("x","y","vx","vy","alive","r")
    def __init__(s, x, y, angle, spd=BOSS_BUL_SPD):
        s.x, s.y = float(x), float(y)
        s.vx = math.cos(angle) * spd
        s.vy = math.sin(angle) * spd
        s.alive = True; s.r = 7
    def update(s, covers):
        s.x += s.vx; s.y += s.vy
        if not (-40 <= s.x <= W+40 and -40 <= s.y <= H+40):
            s.alive = False; return
        for cv in covers:
            if cv.blocks_circle(s.x, s.y, s.r + 2):
                s.alive = False; return
    def draw(s, surf):
        if not s.alive: return
        pygame.draw.circle(surf, C_BOSS_BUL, (int(s.x), int(s.y)), s.r)
        pygame.draw.circle(surf, C_WARN, (int(s.x), int(s.y)), s.r, 2)

# === Enemy ===
g_mode_hp_mul = 1.0
g_mode_spd_mul = 1.0

class Enemy:
    __slots__ = ("x","y","hp","max_hp","spd","r","kind","alive","flash","color")
    def __init__(s, kind, covers):
        s.kind = kind; s.alive = True; s.flash = 0
        for _ in range(200):
            edge = random.randint(0, 3)
            if   edge == 0: sx, sy = random.uniform(96,W-96), -72
            elif edge == 1: sx, sy = W+72, random.uniform(96,H-96)
            elif edge == 2: sx, sy = random.uniform(96,W-96), H+72
            else:           sx, sy = -72, random.uniform(96,H-96)
            ok = True
            for cv in covers:
                if cv.blocks_point(sx, sy, 48): ok = False; break
            if ok:
                s.x, s.y = sx, sy; break
        else:
            s.x, s.y = W+72, random.uniform(96,H-96)
        if   kind == 0:
            s.hp=s.max_hp=int(2*g_mode_hp_mul); s.spd=random.uniform(2.9,4.6)*g_mode_spd_mul; s.r=12; s.color=C_E1
        elif kind == 1:
            s.hp=s.max_hp=int(1*g_mode_hp_mul); s.spd=random.uniform(6.0,8.6)*g_mode_spd_mul; s.r=9;  s.color=C_E2
        else:
            s.hp=s.max_hp=int(5*g_mode_hp_mul); s.spd=random.uniform(1.2,2.2)*g_mode_spd_mul; s.r=18; s.color=C_E3
    def update(s, px, py, covers):
        a = angle_to((s.x,s.y), (px,py))
        nx = s.x + math.cos(a)*s.spd
        ny = s.y + math.sin(a)*s.spd
        for cv in covers:
            if cv.blocks_point(nx, ny, s.r+2):
                nx2 = s.x + math.cos(a)*s.spd; ny2 = s.y
                if not any(cv2.blocks_point(nx2,ny2,s.r+2) for cv2 in covers):
                    nx, ny = nx2, ny2
                else:
                    nx2b = s.x; ny2b = s.y + math.sin(a)*s.spd
                    if not any(cv2.blocks_point(nx2b,ny2b,s.r+2) for cv2 in covers):
                        nx, ny = nx2b, ny2b
                    else:
                        nx = s.x+random.uniform(-0.5,0.5)
                        ny = s.y+random.uniform(-0.5,0.5)
                break
        s.x, s.y = nx, ny
        s.x = clamp(s.x, s.r, W-s.r)
        s.y = clamp(s.y, s.r, H-s.r)
        if s.flash > 0: s.flash -= 1
    def hit(s, dmg):
        s.hp -= dmg; s.flash = 6
        if s.hp <= 0: s.alive = False
    def draw(s, surf):
        c = C_WARN if s.flash>0 else s.color
        pygame.draw.circle(surf, c, (int(s.x),int(s.y)), s.r)
        if s.r == 18:
            pygame.draw.circle(surf, (90,15,110), (int(s.x),int(s.y)), s.r, 2)
        if s.hp < s.max_hp:
            bw = s.r*2; bx = int(s.x)-s.r; by = int(s.y)-s.r-7
            pygame.draw.rect(surf, C_HP_BG, (bx,by,bw,4))
            pygame.draw.rect(surf, C_HP_FG, (bx,by,max(0,int(bw*s.hp/s.max_hp)),4))

# === Boss ===
class Boss:
    _font_cache = None  # 缓存字体对象
    
    @classmethod
    def _get_font(cls):
        if cls._font_cache is None:
            try:
                cls._font_cache = pygame.font.SysFont("consolas", 10, bold=True)
            except:
                cls._font_cache = pygame.font.Font(None, 14)
        return cls._font_cache
    
    def __init__(s, lv_idx, covers):
        diff = 0 if lv_idx <= 4 else 1
        s.hp = BOSS_HP[diff]; s.max_hp = s.hp
        s.r = BOSS_R; s.spd = 1.0 + diff * 0.3
        s.alive = True; s.flash = 0
        s.fire_timer = 0; s.fire_cd = BOSS_FIRE_CD[diff]
        s.pattern = 0; s.pattern_timer = 0
        s.move_angle = random.uniform(0, math.pi*2)
        s.move_t = 0; s.x, s.y = W//2, -60
        s.entering = True; s.enter_y = 80
    def update(s, px, py, covers, now, boss_bullets, snd):
        if s.entering:
            s.y += 2.5
            if s.y >= s.enter_y:
                s.y = s.enter_y; s.entering = False
            return
        s.move_t += 1
        if s.move_t > 100:
            s.move_angle = random.uniform(0, math.pi*2)
            s.move_t = 0
        mx = math.cos(s.move_angle) * s.spd * 0.5
        my = math.sin(s.move_angle) * s.spd * 0.3
        nx = s.x + mx; ny = s.y + my
        nx = clamp(nx, s.r+20, W-s.r-20)
        ny = clamp(ny, s.r+10, H*0.45)
        ok = True
        for cv in covers:
            if cv.blocks_point(nx, ny, s.r+4):
                ok = False; break
        if ok: s.x, s.y = nx, ny
        else: s.move_angle += math.pi
        if now - s.fire_timer >= s.fire_cd:
            s.fire_timer = now
            s._fire(px, py, boss_bullets, snd)
        if now - s.pattern_timer > 3500:
            s.pattern = (s.pattern + 1) % 3
            s.pattern_timer = now
        if s.flash > 0: s.flash -= 1
    def _fire(s, px, py, boss_bullets, snd):
        if snd: safe_play(snd.get("boss_fire"))
        base = angle_to((s.x, s.y), (px, py))
        if s.pattern == 0:
            for i in range(5):
                a = base + (i-2) * 0.20
                boss_bullets.append(BossBullet(s.x, s.y, a))
        elif s.pattern == 1:
            for i in range(14):
                a = i * math.pi * 2 / 14
                boss_bullets.append(BossBullet(s.x, s.y, a, BOSS_BUL_SPD*0.7))
        else:
            base2 = base + pygame.time.get_ticks() * 0.0005
            for i in range(4):
                a = base2 + i * math.pi/2
                boss_bullets.append(BossBullet(s.x, s.y, a, BOSS_BUL_SPD*1.1))
    def hit(s, dmg):
        s.hp -= dmg; s.flash = 6
        if s.hp <= 0: s.alive = False
    def draw(s, surf):
        pulse = int(abs(math.sin(pygame.time.get_ticks() * 0.004)) * 25)
        cx, cy = int(s.x), int(s.y)
        pygame.draw.circle(surf, (255,50+pulse,30), (cx,cy), s.r+4, 3)
        body = C_WARN if s.flash>0 else C_BOSS
        pygame.draw.circle(surf, body, (cx,cy), s.r)
        pygame.draw.circle(surf, C_BOSS_2, (cx,cy), s.r-10, 2)
        for ex in (cx-12, cx+12):
            pygame.draw.circle(surf, (255,255,0), (ex, cy-6), 5)
            pygame.draw.circle(surf, (0,0,0),     (ex, cy-6), 2)
        bw = W-100; bx = 50; by = 6
        pygame.draw.rect(surf, C_HP_BG, (bx,by,bw,12), border_radius=3)
        fw = max(0, int(bw * s.hp / s.max_hp))
        if fw > 0:
            pygame.draw.rect(surf, C_BOSS, (bx,by,fw,12), border_radius=3)
        pygame.draw.rect(surf, C_TEXT_D, (bx,by,bw,12), 2, border_radius=3)
        ft = s._get_font()  # 使用缓存的字体
        tl = ft.render("BOSS", True, C_TEXT)
        surf.blit(tl, (bx-50, by))

# === Player ===
class Player:
    def __init__(s, mag_size, reserve, pnum=1):
        s.x=W//2; s.y=H//2; s.hp=8; s.hp_max=8
        s.angle=0; s.alive=True; s.inv_timer=0
        s.shoot_timer=0; s.mag_size=mag_size; s.ammo=mag_size
        s.reserve=reserve; s.reloading=False; s.reload_start=0
        s.pnum = pnum
        s.color = C_PLAYER if pnum==1 else C_PLAYER2
        s.glow_color = C_PLAYER_G if pnum==1 else C_PLAYER2_G
    def set_mag(s, ms):
        s.mag_size = ms
    def start_reload(s, now, snd=None):
        if s.reloading or s.ammo>=s.mag_size or s.reserve<=0: return
        s.reloading=True; s.reload_start=now
        if snd: safe_play(snd.get("reload_s"))
    def tick_reload(s, now, snd=None):
        if s.reloading and now - s.reload_start >= g_reload_ms:
            need = s.mag_size - s.ammo
            take = min(need, s.reserve)
            s.ammo += take; s.reserve -= take
            s.reloading = False
            if snd: safe_play(snd.get("reload_d"))
    def update(s, held, mx, my, now, covers, snd=None):
        dx=dy=0
        if held["up"]:    dy-=1
        if held["down"]:  dy+=1
        if held["left"]:  dx-=1
        if held["right"]: dx+=1
        if dx or dy:
            l=math.sqrt(dx*dx+dy*dy)
            spd = g_player_spd
            nx=s.x+dx/l*spd; ny=s.y+dy/l*spd
            ok=True
            for cv in covers:
                if cv.blocks_point(nx,ny,PLAYER_R+1): ok=False; break
            if ok: s.x,s.y=nx,ny
            else:
                if dx and not any(cv.blocks_point(s.x+dx/l*spd,s.y,PLAYER_R+1) for cv in covers):
                    s.x=nx
                if dy and not any(cv.blocks_point(s.x,s.y+dy/l*spd,PLAYER_R+1) for cv in covers):
                    s.y=ny
        s.x=clamp(s.x,PLAYER_R,W-PLAYER_R)
        s.y=clamp(s.y,PLAYER_R,H-PLAYER_R)
        s.angle = angle_to((s.x,s.y),(mx,my))
        s.tick_reload(now, snd)
        if s.inv_timer>0: s.inv_timer-=1
    def try_shoot(s, now, bullets, multi, snd, g_scd, g_br, g_bd):
        if s.reloading: return
        if s.ammo <= 0:
            if snd: safe_play(snd.get("empty"))
            return
        if now - s.shoot_timer < g_scd: return
        if len(bullets) >= MAX_BULLETS: return
        s.shoot_timer = now
        if not getattr(s, "inf_ammo", False): s.ammo -= 1
        bullets.append(Bullet(s.x, s.y, s.angle, g_bd))
        if snd: safe_play(snd.get("shoot"))
        if multi:
            bullets.append(Bullet(s.x,s.y,s.angle+0.12, g_bd))
            bullets.append(Bullet(s.x,s.y,s.angle-0.12, g_bd))
    def take_damage(s, snd=None):
        if not s.alive: return
        if getattr(s, "invincible", False): return
        if s.inv_timer > 0: return
        s.hp -= 1; s.inv_timer = 90
        if snd: safe_play(snd.get("player_hit"))
        if s.hp <= 0: s.alive = False
    def draw(s, surf, g_rld):
        blink = s.inv_timer>0 and (s.inv_timer%8<4)
        c = C_TEXT_D if blink else s.color
        pygame.draw.circle(surf,c,(int(s.x),int(s.y)),PLAYER_R)
        gx=int(s.x+math.cos(s.angle)*(PLAYER_R+4))
        gy=int(s.y+math.sin(s.angle)*(PLAYER_R+4))
        pygame.draw.line(surf,s.glow_color,(int(s.x),int(s.y)),(gx,gy),2)
        if s.pnum == 2:
            pygame.draw.circle(surf, s.color, (int(s.x), int(s.y)), PLAYER_R, 2)
        if s.reloading:
            prog=min(1.0,(pygame.time.get_ticks()-s.reload_start)/g_rld)
            bw=30; bx=int(s.x)-15; by=int(s.y)+PLAYER_R+6
            pygame.draw.rect(surf,C_HP_BG,(bx,by,bw,5))
            pygame.draw.rect(surf,(80,180,255),(bx,by,int(bw*prog),5))

# === Level helpers ===
def spawn_covers(n):
    covers=[]
    safe = pygame.Rect(W//2-120, H//2-90, 240, 180)
    for _ in range(n):
        for attempt in range(80):
            w=random.randint(40,100); h=random.randint(40,100)
            x=random.randint(90,W-90-w); y=random.randint(68,H-68-h)
            rect=pygame.Rect(x,y,w,h)
            if rect.colliderect(safe): continue
            if any(rect.colliderect(c.rect.inflate(24,24)) for c in covers): continue
            covers.append(Cover(x,y,w,h)); break
    return covers

def make_level(lv_idx):
    idx = min(lv_idx, len(LEVELS)-1)
    t,sp,_,mg,rs = LEVELS[idx]
    covs = spawn_covers(LEVELS[idx][2])
    return idx,0,mg,rs,covs,sp,t

# === Drawing ===
def draw_hud(surf, font, sfont, bigfont, player, lv_num, kills, kt, fps, boss, mode="NORMAL", spd_timer=0, player2=None):
    if fps > 0:
        fc = (80,220,80) if fps>=55 else ((255,215,50) if fps>=30 else (255,90,90))
        ft = sfont.render("FPS "+str(int(fps)), True, fc)
        surf.blit(ft, (W-ft.get_width()-8, 36))
    # 模式标签
    if mode=="COOP":
        mc = (100,180,255)
    else:
        mc = C_ACCENT if mode=="NORMAL" else (C_WARN if mode=="HARD" else ((255,100,255) if mode=="ENDLESS" else (100,255,255)))
    mt = sfont.render(mode, True, mc)
    surf.blit(mt, (8, 72))
    # 速通倒计时
    if mode=="SPEEDRUN" and spd_timer>0:
        sec = spd_timer/1000.0
        tc = C_ACCENT if sec>10 else C_WARN
        if sec<=5: tc=(255,50,50)
        st = bigfont.render(("%.1f" if sec<=5 else "%.0f")%sec, True, tc)
        surf.blit(st, (W//2-st.get_width()//2, H-65))
    # P1 血量
    for i in range(player.hp_max):
        c = C_HP_FG if i<player.hp else C_HP_BG
        pygame.draw.circle(surf,c,(24+i*26,20),8)
    # P1 编号标记
    p1_tag = sfont.render("P1", True, C_PLAYER)
    surf.blit(p1_tag, (4, 36))
    t = font.render("LV."+str(lv_num),True,C_ACCENT)
    surf.blit(t,(W-20-t.get_width(),14))
    kt2 = sfont.render(str(kills)+"/"+str(kt),True,C_TEXT)
    surf.blit(kt2,(W//2-kt2.get_width()//2,12))
    # P1 弹药
    ac = C_WARN if player.ammo==0 else (C_ACCENT if player.ammo<=4 else C_TEXT)
    a = sfont.render(str(player.ammo)+"/"+str(player.mag_size),True,ac)
    surf.blit(a,(30,36))
    r = sfont.render("RES "+str(player.reserve),True,C_TEXT_D)
    surf.blit(r,(30,52))
    if player.ammo==0 and player.reserve>0 and not player.reloading:
        h=sfont.render("[M] RELOAD",True,C_WARN)
        surf.blit(h,(W//2-h.get_width()//2,36))
    if player.reloading:
        rl=sfont.render("P1 RELOADING...",True,(80,180,255))
        surf.blit(rl,(W//2-rl.get_width()//2,36))
    # P2 信息（COOP模式）— 放在右下角区域避免重叠
    if player2 is not None:
        p2_y = H - 52  # 底部对齐
        # P2 血量（右侧底部）
        for i in range(player2.hp_max):
            c = C_HP_FG if i<player2.hp else C_HP_BG
            pygame.draw.circle(surf, c, (W-24-i*26, p2_y), 8)
        p2_tag = sfont.render("P2", True, C_PLAYER2)
        surf.blit(p2_tag, (W-20-p2_tag.get_width(), p2_y+16))
        # P2 弹药
        ac2 = C_WARN if player2.ammo==0 else (C_ACCENT if player2.ammo<=4 else C_TEXT)
        a2 = sfont.render(str(player2.ammo)+"/"+str(player2.mag_size), True, ac2)
        surf.blit(a2, (W-30-a2.get_width(), p2_y+16))
        r2 = sfont.render("RES "+str(player2.reserve), True, C_TEXT_D)
        surf.blit(r2, (W-30-r2.get_width(), p2_y+32))
        if player2.reloading:
            rl2 = sfont.render("P2 RELOADING...", True, (80,180,255))
            surf.blit(rl2, (W//2-rl2.get_width()//2, H-30))
        elif player2.ammo==0 and player2.reserve>0:
            h2=sfont.render("P2 [RCTRL] RELOAD",True,C_WARN)
            surf.blit(h2,(W//2-h2.get_width()//2,H-30))
    if boss and boss.alive:
        wt = font.render("!! BOSS !!", True, C_WARN)
        surf.blit(wt, (W//2-wt.get_width()//2, 22))
    fl=[]
    if getattr(player,"invincible",False): fl.append("INV")
    if getattr(player,"inf_ammo",False):   fl.append("INF")
    if g_shoot_cd != 160:               fl.append("CD:"+str(g_shoot_cd))
    if g_bullet_r != 4:                fl.append("BR:"+str(g_bullet_r))
    if g_bullet_dmg != 1:              fl.append("DMG:"+str(g_bullet_dmg))
    if g_reload_ms != 1400:            fl.append("RL:"+str(g_reload_ms))
    if fl:
        ct = sfont.render("  ".join(fl), True, (255,210,50))
        surf.blit(ct, (W-ct.get_width()-8, H-22))

def draw_grid(surf):
    for x in range(0,W,40): pygame.draw.line(surf,C_GRID,(x,0),(x,H))
    for y in range(0,H,40): pygame.draw.line(surf,C_GRID,(0,y),(W,y))

def draw_boss_warn(surf, bigfont, font, timer):
    alpha = int(abs(math.sin(timer*0.008)) * 180) + 40
    ov = pygame.Surface((W,H), pygame.SRCALPHA)
    ov.fill((60,0,0,min(140,alpha)))
    surf.blit(ov,(0,0))
    t1 = bigfont.render("WARNING", True, C_WARN)
    t2 = font.render("BOSS INCOMING!", True, C_BOSS_2)
    surf.blit(t1, (W//2-t1.get_width()//2, H//2-25))
    surf.blit(t2, (W//2-t2.get_width()//2, H//2+4))

def draw_boss_kill(surf, bigfont, font, timer):
    alpha = min(200, max(0, int(timer*2.5)))
    ov = pygame.Surface((W,H), pygame.SRCALPHA)
    ov.fill((0,60,0,alpha))
    surf.blit(ov,(0,0))
    t1 = bigfont.render("BOSS DEFEATED!", True, C_ACCENT)
    t2 = font.render("REWARD: +50 AMMO  +2 HP", True, (80,220,80))
    surf.blit(t1, (W//2-t1.get_width()//2, H//2-20))
    surf.blit(t2, (W//2-t2.get_width()//2, H//2+8))

def draw_pause(surf,font,sfont,sel):
    ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill(C_POVER_BG); surf.blit(ov,(0,0))
    t=font.render("PAUSED",True,C_TEXT)
    surf.blit(t,(W//2-t.get_width()//2,H//2-46))
    for i,(cn,_) in enumerate([("CONTINUE","CONTINUE"),("RESTART","RESTART"),("QUIT","QUIT")]):
        y=H//2-18+i*52; col=C_ACCENT if i==sel else C_TEXT
        if i==sel:
            r=pygame.Rect(W//2-100,y-17,200,38)
            pygame.draw.rect(surf,(40,40,60),r,border_radius=8)
        ti=font.render(cn,True,col)
        surf.blit(ti,(W//2-ti.get_width()//2,y-ti.get_height()//2))
    h=sfont.render("W/S:Select  ENTER:Confirm  ESC:Resume",True,C_TEXT_D)
    surf.blit(h,(W//2-h.get_width()//2,H//2+130))

def draw_transition(surf,bigfont,font,lv_num,mag_up):
    ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,140)); surf.blit(ov,(0,0))
    t1=bigfont.render("LEVEL  "+str(lv_num),True,C_ACCENT)
    surf.blit(t1,(W//2-t1.get_width()//2,H//2-21))
    if mag_up:
        t2=font.render("MAGAZINE UPGRADED",True,(80,200,120))
        surf.blit(t2,(W//2-t2.get_width()//2,H//2+4))

def draw_gameover(surf,bigfont,font,sfont,score,lv_num):
    ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,180)); surf.blit(ov,(0,0))
    t1=bigfont.render("GAME OVER",True,C_WARN)
    t2=font.render("SCORE "+str(score).zfill(6),True,C_TEXT)
    t3=font.render("LEVEL "+str(lv_num),True,C_TEXT_D)
    t4=sfont.render("R:RESTART  Q:QUIT",True,C_TEXT_D)
    surf.blit(t1,(W//2-t1.get_width()//2,H//2-46))
    surf.blit(t2,(W//2-t2.get_width()//2,H//2-12))
    surf.blit(t3,(W//2-t3.get_width()//2,H//2+4))
    surf.blit(t4,(W//2-t4.get_width()//2,H//2+29))

# === Cheat config ===
CHEAT_FILE = os.path.join(get_app_dir(), "cheat_cfg.json")
cheat_last_v = -1
def read_cheat():
    try:
        if os.path.exists(CHEAT_FILE):
            with open(CHEAT_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: pass
    return None
def write_cheat(cfg):
    try:
        cfg["apply"] = False
        with open(CHEAT_FILE, "w", encoding="utf-8") as f: json.dump(cfg, f, indent=2)
    except Exception: pass

# === Login Screen ===
def login_screen(screen, surf, font, sfont, bigfont):
    """返回 username 表示登录成功，'REGISTER'=注册，'OFFLINE'=离线，None=退出"""
    user_in  = TextInput(W//2-100, 220, 200, 32, font, False)
    pass_in  = TextInput(W//2-100, 290, 200, 32, font, True)
    err_msg  = ""
    err_t    = 0
    clock    = pygame.time.Clock()
    # 按钮区域
    btn_login   = pygame.Rect(W//2-120, H//2+68,  100, 32)
    btn_reg     = pygame.Rect(W//2+20,  H//2+68,  100, 32)
    btn_offline = pygame.Rect(W//2-90,  H//2+114, 180, 30)
    btn_quit    = pygame.Rect(W//2-55,  H//2+158, 110, 30)
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: return None
                if ev.key == pygame.K_RETURN:
                    u = user_in.get().strip(); p = pass_in.get()
                    if verify_user(u, p): return u
                    else: err_msg = "Invalid username or password"; err_t = 120
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                smx, smy = scale_mouse(*ev.pos, screen, surf)
                if btn_login.collidepoint(smx, smy):
                    u = user_in.get().strip(); p = pass_in.get()
                    if verify_user(u, p): return u
                    else: err_msg = "Invalid username or password"; err_t = 120
                elif btn_reg.collidepoint(smx, smy):
                    return "REGISTER"
                elif btn_offline.collidepoint(smx, smy):
                    return "OFFLINE"
                elif btn_quit.collidepoint(smx, smy):
                    pygame.quit(); sys.exit()
            user_in.handle_event(ev); pass_in.handle_event(ev)
        surf.fill(C_BG); draw_grid(surf)
        t = bigfont.render("LOGIN", True, C_ACCENT)
        surf.blit(t, (W//2-t.get_width()//2, 80))
        lbl = sfont.render("USERNAME:", True, C_TEXT_D); surf.blit(lbl, (W//2-100, 195))
        user_in.draw(surf)
        lbl = sfont.render("PASSWORD:", True, C_TEXT_D); surf.blit(lbl, (W//2-100, 265))
        pass_in.draw(surf)
        # 按钮
        mx, my = scale_mouse(*pygame.mouse.get_pos(), screen, surf)
        for name, rect, color in [
            ("LOGIN",   btn_login,   C_ACCENT),
            ("REGISTER",btn_reg,     C_TEXT),
            ("OFFLINE", btn_offline, C_TEXT_D),
            ("QUIT",    btn_quit,    C_WARN),
        ]:
            hover = rect.collidepoint(mx, my)
            bg = (55,55,80) if hover else (40,40,60)
            col = C_ACCENT if hover else color
            pygame.draw.rect(surf, bg, rect, border_radius=6)
            pygame.draw.rect(surf, col, rect, 2, border_radius=6)
            btxt = sfont.render(name, True, col)
            surf.blit(btxt, (rect.x+(rect.w-btxt.get_width())//2, rect.y+(rect.h-btxt.get_height())//2))
        # 离线说明
        hint = sfont.render("Offline: limited to level 1-5, no save", True, (80,80,100))
        surf.blit(hint, (W//2-hint.get_width()//2, H//2+148))
        if err_msg and err_t > 0:
            err_surf = sfont.render(err_msg, True, C_WARN)
            surf.blit(err_surf, (W//2-err_surf.get_width()//2, H//2+195))
            err_t -= 1
        screen.blit(pygame.transform.scale(surf, screen.get_size()), (0,0))
        pygame.display.flip()
        clock.tick(FPS)

# === Register Screen ===
def register_screen(screen, surf, font, sfont, bigfont):
    """返回 username 表示注册成功，返回 'LOGIN' 表示返回登录，返回 None 表示退出"""
    user_in = TextInput(W//2-100, 200, 200, 32, font, False)
    pass_in = TextInput(W//2-100, 260, 200, 32, font, True)
    cpass_in= TextInput(W//2-100, 320, 200, 32, font, True)
    err_msg = ""; err_t = 0; ok_msg = ""
    clock   = pygame.time.Clock()
    btn_reg  = pygame.Rect(W//2-120, H//2+100, 100, 36)
    btn_back = pygame.Rect(W//2+20,  H//2+100, 100, 36)
    btn_quit = pygame.Rect(W//2-60,  H//2+170, 120, 36)
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: return None
                if ev.key == pygame.K_RETURN:
                    u=user_in.get().strip(); p=pass_in.get(); cp=cpass_in.get()
                    if not u or not p: err_msg="Username and password required"; err_t=120
                    elif p != cp: err_msg="Passwords do not match"; err_t=120
                    elif register_user(u, p):
                        ok_msg="Registered! Please login."
                        user_in.clear(); pass_in.clear(); cpass_in.clear()
                        pygame.time.delay(800); return "LOGIN"
                    else: err_msg="Username already exists"; err_t=120
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                smx, smy = scale_mouse(*ev.pos, screen, surf)
                if btn_reg.collidepoint(smx, smy):
                    u=user_in.get().strip(); p=pass_in.get(); cp=cpass_in.get()
                    if not u or not p: err_msg="Username and password required"; err_t=120
                    elif p != cp: err_msg="Passwords do not match"; err_t=120
                    elif register_user(u, p):
                        ok_msg="Registered! Please login."
                        user_in.clear(); pass_in.clear(); cpass_in.clear()
                        pygame.time.delay(800); return "LOGIN"
                    else: err_msg="Username already exists"; err_t=120
                elif btn_back.collidepoint(smx, smy): return "LOGIN"
                elif btn_quit.collidepoint(smx, smy): pygame.quit(); sys.exit()
            user_in.handle_event(ev); pass_in.handle_event(ev); cpass_in.handle_event(ev)
        surf.fill(C_BG); draw_grid(surf)
        t = bigfont.render("REGISTER", True, C_ACCENT)
        surf.blit(t, (W//2-t.get_width()//2, 80))
        lbl = sfont.render("USERNAME:", True, C_TEXT_D); surf.blit(lbl, (W//2-100, 175))
        user_in.draw(surf)
        lbl = sfont.render("PASSWORD:", True, C_TEXT_D); surf.blit(lbl, (W//2-100, 235))
        pass_in.draw(surf)
        lbl = sfont.render("CONFIRM:", True, C_TEXT_D);  surf.blit(lbl, (W//2-100, 295))
        cpass_in.draw(surf)
        mx, my = scale_mouse(*pygame.mouse.get_pos(), screen, surf)
        for name, rect in [("REGISTER", btn_reg), ("BACK", btn_back), ("QUIT", btn_quit)]:
            hover = rect.collidepoint(mx, my)
            bg = (55,55,80) if hover else (40,40,60)
            col = C_ACCENT if hover else C_TEXT
            pygame.draw.rect(surf, bg, rect, border_radius=6)
            pygame.draw.rect(surf, col, rect, 2, border_radius=6)
            btxt = sfont.render(name, True, col)
            surf.blit(btxt, (rect.x+(rect.w-btxt.get_width())//2, rect.y+(rect.h-btxt.get_height())//2))
        if err_msg and err_t>0:
            err_surf = sfont.render(err_msg, True, C_WARN)
            surf.blit(err_surf, (W//2-err_surf.get_width()//2, H//2+240))
            err_t -= 1
        if ok_msg:
            ok_surf = sfont.render(ok_msg, True, (80,220,120))
            surf.blit(ok_surf, (W//2-ok_surf.get_width()//2, H//2+240))
        screen.blit(pygame.transform.scale(surf, screen.get_size()), (0,0))
        pygame.display.flip()
        clock.tick(FPS)

# === Level Select Screen ===
def level_select_screen(screen, surf, font, sfont, bigfont, unlocked=10):
    """返回 (关卡索引, 模式字符串) 元组，返回 None 表示退出"""
    sel        = 0
    mode_sel   = 0  # 当前选中模式索引
    clock      = pygame.time.Clock()
    total      = len(LEVELS)

    while True:
        # 模式按钮区域（上方一行）
        mode_rects = []
        mw = 110; mh = 26; mgap = 8
        mx0 = W//2 - (len(GAME_MODES)*mw + (len(GAME_MODES)-1)*mgap)//2
        for i, m in enumerate(GAME_MODES):
            mode_rects.append(pygame.Rect(mx0+i*(mw+mgap), 95, mw, mh))

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: return None
                if ev.key in (pygame.K_LEFT,  pygame.K_a): sel = max(0, sel-1)
                if ev.key in (pygame.K_RIGHT, pygame.K_d): sel = min(unlocked, min(total-1, sel+1))
                if ev.key in (pygame.K_UP,    pygame.K_w): mode_sel = (mode_sel-1) % len(GAME_MODES)
                if ev.key in (pygame.K_DOWN,  pygame.K_s): mode_sel = (mode_sel+1) % len(GAME_MODES)
                if ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                    return sel, GAME_MODES[mode_sel]
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                smx2, smy2 = scale_mouse(*ev.pos, screen, surf)
                # 模式按钮
                for i, mr in enumerate(mode_rects):
                    if mr.collidepoint(smx2, smy2):
                        mode_sel = i
                # 关卡格
                lx = 40; ly = 148; bw = 90; bh = 55; gap = 10; cols = 5
                for i in range(total):
                    row, col = i//cols, i%cols
                    bx = lx + col*(bw+gap); by = ly + row*(bh+gap)
                    if i <= unlocked and pygame.Rect(bx, by, bw, bh).collidepoint(smx2, smy2):
                        sel = i
                # START 按钮
                if pygame.Rect(W//2-80, H-62, 160, 36).collidepoint(smx2, smy2):
                    return sel, GAME_MODES[mode_sel]
        surf.fill(C_BG); draw_grid(surf)
        t = bigfont.render("SELECT LEVEL", True, C_ACCENT)
        surf.blit(t, (W//2-t.get_width()//2, 42))
        # 模式按钮行
        mxi, myi = scale_mouse(*pygame.mouse.get_pos(), screen, surf)
        for i, (m, mr) in enumerate(zip(GAME_MODES, mode_rects)):
            is_sel = i == mode_sel
            mc2 = C_ACCENT if is_sel else (C_TEXT if mr.collidepoint(mxi, myi) else C_TEXT_D)
            bg2 = (50,50,80) if is_sel else ((44,44,66) if mr.collidepoint(mxi, myi) else (35,35,52))
            pygame.draw.rect(surf, bg2, mr, border_radius=5)
            pygame.draw.rect(surf, mc2, mr, 2, border_radius=5)
            mlbl = sfont.render(m, True, mc2)
            surf.blit(mlbl, (mr.x+(mr.w-mlbl.get_width())//2, mr.y+(mr.h-mlbl.get_height())//2))
        # 模式描述
        desc = sfont.render(MODE_DESC[GAME_MODES[mode_sel]], True, C_TEXT_D)
        surf.blit(desc, (W//2-desc.get_width()//2, 126))
        # 关卡按钮网格
        lx=40; ly=148; bw=90; bh=55; gap=10; cols=5
        for i in range(total):
            row,col = i//cols, i%cols
            bx = lx+col*(bw+gap); by = ly+row*(bh+gap)
            is_boss  = i in BOSS_LEVELS
            is_unlock= i <= unlocked
            is_sel   = i == sel
            if is_sel:      bg=(70,90,140); border=C_ACCENT
            elif is_boss:   bg=(100,30,30); border=C_BOSS
            elif is_unlock: bg=(45,45,75);  border=C_TEXT_D
            else:           bg=(30,30,45);  border=(60,60,80)
            r=pygame.Rect(bx,by,bw,bh)
            pygame.draw.rect(surf,bg,r,border_radius=8)
            pygame.draw.rect(surf,border,r,2,border_radius=8)
            num=font.render(str(i+1),True,C_TEXT if is_unlock else (80,80,100))
            surf.blit(num,(r.x+(r.w-num.get_width())//2, r.y+8))
            if is_boss:
                blbl=sfont.render("BOSS",True,C_BOSS_2)
                surf.blit(blbl,(r.x+(r.w-blbl.get_width())//2, r.y+32))
            if not is_unlock:
                lvlbl=sfont.render("LOCK",True,(80,80,100))
                surf.blit(lvlbl,(r.x+(r.w-lvlbl.get_width())//2, r.y+32))
        # START 按钮
        r=pygame.Rect(W//2-80,H-62,160,36)
        pygame.draw.rect(surf,(50,120,70),r,border_radius=8)
        pygame.draw.rect(surf,C_ACCENT,r,2,border_radius=8)
        st=font.render("START",True,C_TEXT)
        surf.blit(st,(r.x+(r.w-st.get_width())//2, r.y+(r.h-st.get_height())//2))
        # 提示
        hint=sfont.render("A/D:level  W/S:mode  ENTER:start  ESC:quit",True,C_TEXT_D)
        surf.blit(hint,(W//2-hint.get_width()//2, H-18))
        screen.blit(pygame.transform.scale(surf, screen.get_size()), (0,0))
        pygame.display.flip()
        clock.tick(FPS)
    return None

# === Main ===
def game(start_level=0, mode="NORMAL"):
    global g_bullet_r, g_shoot_cd, g_bullet_dmg, g_reload_ms, g_player_spd, g_bullet_spd
    global g_mode_hp_mul, g_mode_spd_mul
    # 根据模式设置参数
    if mode == "HARD":
        g_mode_hp_mul = 2.0; g_mode_spd_mul = 1.4
    elif mode == "ENDLESS":
        g_mode_hp_mul = 1.0; g_mode_spd_mul = 1.0
    else:
        g_mode_hp_mul = 1.0; g_mode_spd_mul = 1.0
    is_coop = (mode == "COOP")
    pygame.init()
    pygame.mixer.init(frequency=SR, size=-16, channels=1, buffer=512)
    pygame.mixer.set_num_channels(8)
    snd = init_sounds()
    # 普通窗口 800x600
    screen = pygame.display.set_mode((W, H))
    surf = pygame.Surface((W, H))
    TextInput.set_scale(screen, surf)
    pygame.display.set_caption("TopDown Shooter v6")
    clock = pygame.time.Clock()
    def flip_display():
        screen.blit(pygame.transform.scale(surf, screen.get_size()), (0,0))
        pygame.display.flip()
    def mkf(size, bold=False):
        try: return pygame.font.SysFont("consolas", size, bold=bold)
        except: return pygame.font.Font(None, size+(4 if bold else 0))
    font=mkf(22,True); sfont=mkf(15); bigfont=mkf(48,True)
    global cheat_last_v
    fc=[0]
    cheat_kill_all = [False]
    cheat_restore  = [False]
    cheat_teleport = [False]
    def apply_cheat(p, p2=None):
        nonlocal fc
        fc[0]+=1
        if fc[0]%6!=0: return
        global g_bullet_r,g_shoot_cd,g_bullet_dmg,g_reload_ms,g_player_spd,g_bullet_spd,cheat_last_v
        cfg=read_cheat()
        if not cfg: return
        v=cfg.get("_version",0)
        if v==cheat_last_v: return
        cheat_last_v=v
        p.invincible=bool(cfg.get("invincible",False))
        p.inf_ammo=bool(cfg.get("inf_ammo",False))
        if p2:
            p2.invincible=bool(cfg.get("invincible",False))
            p2.inf_ammo=bool(cfg.get("inf_ammo",False))
        g_shoot_cd=max(0,int(cfg.get("shoot_cd",160)))
        g_bullet_r=max(1,int(cfg.get("bullet_r",4)))
        g_bullet_dmg=max(1,int(cfg.get("bullet_dmg",1)))
        g_reload_ms=max(50,int(cfg.get("reload_ms",1400)))
        g_player_spd=max(1.0,float(cfg.get("player_spd",PLAYER_SPD)))
        g_bullet_spd=max(1.0,float(cfg.get("bullet_spd",BULLET_SPD)))
        if cfg.get("apply",False):
            nh=max(1,int(cfg.get("hp",p.hp))); nhm=max(1,int(cfg.get("hp_max",p.hp_max)))
            nm=max(1,int(cfg.get("mag_size",p.mag_size)))
            p.hp=min(nh,nhm); p.hp_max=nhm
            if nm!=p.mag_size: p.set_mag(nm); p.ammo=min(p.ammo,nm)
            if p.inf_ammo: p.ammo=p.mag_size
            if p2:
                p2.hp=min(nh,nhm); p2.hp_max=nhm
                if nm!=p2.mag_size: p2.set_mag(nm); p2.ammo=min(p2.ammo,nm)
                if p2.inf_ammo: p2.ammo=p2.mag_size
            cheat_teleport[0] = bool(cfg.get("teleport_center",False))
            cheat_kill_all[0] = bool(cfg.get("kill_all",False))
            cheat_restore[0]  = bool(cfg.get("full_restore",False))
            if cheat_restore[0]:
                p.hp=p.hp_max; p.ammo=p.mag_size; p.reserve=p.mag_size*5
                if p2: p2.hp=p2.hp_max; p2.ammo=p2.mag_size; p2.reserve=p2.mag_size*5
            if cheat_teleport[0]:
                p.x=W//2; p.y=H//2
                if p2: p2.x=W//2+40; p2.y=H//2
            write_cheat(cfg)
    def make_level_endless(lv_idx):
        """无尽模式：超过10关后动态生成越来越难的关卡"""
        if lv_idx < len(LEVELS):
            return make_level(lv_idx)
        # 超出原有关卡：按比例生成更难的
        extra = lv_idx - len(LEVELS) + 1
        t  = max(20, 60 - extra*2)          # 击杀目标
        sp = max(200, 500 - extra*20)        # 生成间隔(ms)，越小越快
        cv_n = min(6, 3 + extra//2)          # 掩体数
        mg = min(30, 12 + extra*2)           # 弹匣
        rs = mg * 4
        covs = spawn_covers(cv_n)
        # 无尽模式逐渐增加难度乘数
        global g_mode_hp_mul, g_mode_spd_mul
        g_mode_hp_mul = min(5.0, 1.0 + extra*0.3)
        g_mode_spd_mul= min(3.0, 1.0 + extra*0.15)
        return lv_idx, 0, mg, rs, covs, sp, t

    def reset_all():
        if mode == "ENDLESS":
            idx,_,mg,rs,cv,sp,kt = make_level_endless(start_level)
        else:
            idx,_,mg,rs,cv,sp,kt = make_level(start_level)
        p1=Player(mg, rs, pnum=1)
        p1.x = W//2 - 60 if is_coop else W//2
        p1.y = H//2
        p2 = None
        if is_coop:
            p2 = Player(mg, rs, pnum=2)
            p2.x = W//2 + 60; p2.y = H//2
        return p1,p2,[],[],[],0,idx,0,kt,sp,cv,pygame.time.get_ticks(),None,[]
    (player,player2,bullets,enemies,particles,score,lv_idx,kills,kt,spd,covers,last_spawn,boss,boss_bullets)=reset_all()
    game_over=False; paused=False; pause_sel=0; shooting=False; p2_shooting=False
    trans_t=0; trans_up=False; boss_warn_t=0; boss_kill_t=0
    # 速通模式计时
    level_start_t = pygame.time.get_ticks()
    spd_timer_remain = SPEEDRUN_TIME  # ms remaining
    if start_level in BOSS_LEVELS:
        boss=Boss(start_level,covers); boss_warn_t=120
        safe_play(snd.get("boss_warn"))
    # 按键映射：COOP模式分两套，普通模式合并
    if is_coop:
        P1_KEYS = {pygame.K_w:"up", pygame.K_s:"down", pygame.K_a:"left", pygame.K_d:"right"}
        P2_KEYS = {pygame.K_UP:"up", pygame.K_DOWN:"down", pygame.K_LEFT:"left", pygame.K_RIGHT:"right"}
        held1={"up":False,"down":False,"left":False,"right":False}
        held2={"up":False,"down":False,"left":False,"right":False}
    else:
        MOVE_KEYS={pygame.K_w:"up",pygame.K_UP:"up",pygame.K_s:"down",pygame.K_DOWN:"down",pygame.K_a:"left",pygame.K_LEFT:"left",pygame.K_d:"right",pygame.K_RIGHT:"right"}
        held1={"up":False,"down":False,"left":False,"right":False}

    def get_nearest_alive_player(x, y):
        """获取离指定位置最近的存活玩家坐标"""
        if is_coop and player2 and player2.alive:
            d1 = dist((x,y),(player.x,player.y)) if player.alive else 99999
            d2 = dist((x,y),(player2.x,player2.y))
            if not player.alive: return player2.x, player2.y
            return (player.x, player.y) if d1 <= d2 else (player2.x, player2.y)
        return player.x, player.y

    def any_player_alive():
        if is_coop and player2:
            return player.alive or player2.alive
        return player.alive

    def try_spawn():
        nonlocal last_spawn,spd
        now=pygame.time.get_ticks()
        if now-last_spawn<spd: return
        if boss and boss.alive: return
        last_spawn=now
        w=[6,2,0] if lv_idx<=1 else ([4,4,2] if lv_idx<=4 else [3,4,3])
        enemies.append(Enemy(random.choices([0,1,2],weights=w)[0], covers))
        if lv_idx>=3 and random.random()<0.25: enemies.append(Enemy(0,covers))
    cur_fps=0.0
    while True:
        now=pygame.time.get_ticks()
        mx,my=scale_mouse(*pygame.mouse.get_pos(), screen, surf)
        cur_fps=clock.get_fps()
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            elif ev.type==pygame.KEYDOWN:
                if game_over:
                    if ev.key==pygame.K_r: (player,player2,bullets,enemies,particles,score,lv_idx,kills,kt,spd,covers,last_spawn,boss,boss_bullets)=reset_all(); game_over=False; paused=False; trans_t=0; trans_up=False; boss_warn_t=0; boss_kill_t=0; p2_shooting=False
                    elif ev.key==pygame.K_q: pygame.quit(); sys.exit()
                    continue
                if ev.key==pygame.K_ESCAPE: paused=not paused; pause_sel=0; continue
                if paused:
                    if ev.key in (pygame.K_w,pygame.K_UP):   pause_sel=(pause_sel-1)%3
                    elif ev.key in (pygame.K_s,pygame.K_DOWN): pause_sel=(pause_sel+1)%3
                    elif ev.key in (pygame.K_RETURN,pygame.K_SPACE,pygame.K_KP_ENTER):
                        if pause_sel==0: paused=False
                        elif pause_sel==1: (player,player2,bullets,enemies,particles,score,lv_idx,kills,kt,spd,covers,last_spawn,boss,boss_bullets)=reset_all(); paused=False; game_over=False; trans_t=0; trans_up=False; boss_warn_t=0; boss_kill_t=0; p2_shooting=False
                        elif pause_sel==2: pygame.quit(); sys.exit()
                    continue
                if is_coop:
                    if ev.key in P1_KEYS: held1[P1_KEYS[ev.key]]=True
                    if ev.key in P2_KEYS: held2[P2_KEYS[ev.key]]=True
                    if ev.key==pygame.K_m: player.start_reload(now,snd)
                    if ev.key==pygame.K_RCTRL: 
                        if player2: player2.start_reload(now,snd)
                    if ev.key==pygame.K_RSHIFT: p2_shooting=True
                else:
                    if ev.key in MOVE_KEYS: held1[MOVE_KEYS[ev.key]]=True
                if ev.key==pygame.K_r and not is_coop: (player,player2,bullets,enemies,particles,score,lv_idx,kills,kt,spd,covers,last_spawn,boss,boss_bullets)=reset_all(); game_over=False; trans_t=0; trans_up=False; boss_warn_t=0; boss_kill_t=0
            elif ev.type==pygame.KEYUP:
                if is_coop:
                    if ev.key in P1_KEYS: held1[P1_KEYS[ev.key]]=False
                    if ev.key in P2_KEYS: held2[P2_KEYS[ev.key]]=False
                    if ev.key==pygame.K_RSHIFT: p2_shooting=False
                else:
                    if ev.key in MOVE_KEYS: held1[MOVE_KEYS[ev.key]]=False
            elif ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                if not paused and not game_over: shooting=True
            elif ev.type==pygame.MOUSEBUTTONUP and ev.button==1: shooting=False
        # 速通模式：更新倒计时
        if mode == "SPEEDRUN" and not game_over and not paused and boss_warn_t==0:
            elapsed = now - level_start_t
            spd_timer_remain = max(0, SPEEDRUN_TIME - elapsed)
            if spd_timer_remain <= 0:
                game_over = True; safe_play(snd.get("game_over"))
        if paused and not game_over:
            surf.fill(C_BG); draw_grid(surf)
            for cv in covers: cv.draw(surf)
            for p in particles: p.draw(surf)
            for e in enemies: e.draw(surf)
            for bb in boss_bullets: bb.draw(surf)
            if boss and boss.alive: boss.draw(surf)
            for b in bullets: b.draw(surf,g_bullet_r)
            player.draw(surf,g_reload_ms)
            if player2: player2.draw(surf,g_reload_ms)
            draw_hud(surf,font,sfont,bigfont,player,lv_idx+1,kills,kt,cur_fps,boss,mode,spd_timer_remain,player2)
            draw_pause(surf,font,sfont,pause_sel)
            flip_display(); clock.tick(FPS); continue
        if game_over:
            surf.fill(C_BG); draw_grid(surf)
            for cv in covers: cv.draw(surf)
            for p in particles: p.draw(surf)
            for e in enemies: e.draw(surf)
            if boss and boss.alive: boss.draw(surf)
            player.draw(surf,g_reload_ms)
            if player2: player2.draw(surf,g_reload_ms)
            draw_hud(surf,font,sfont,bigfont,player,lv_idx+1,kills,kt,cur_fps,boss,mode,0,player2)
            draw_gameover(surf,bigfont,font,sfont,score,lv_idx+1)
            flip_display(); clock.tick(FPS); continue
        if boss_warn_t>0:
            boss_warn_t-=1
            surf.fill(C_BG); draw_grid(surf)
            player.draw(surf,g_reload_ms)
            if player2: player2.draw(surf,g_reload_ms)
            draw_hud(surf,font,sfont,bigfont,player,lv_idx+1,kills,kt,cur_fps,boss,mode,spd_timer_remain,player2)
            draw_boss_warn(surf,bigfont,font,boss_warn_t)
            flip_display(); clock.tick(FPS); continue
        if boss_kill_t>0:
            boss_kill_t-=1
            surf.fill(C_BG); draw_grid(surf)
            for cv in covers: cv.draw(surf)
            for p in particles: p.draw(surf)
            player.draw(surf,g_reload_ms)
            if player2: player2.draw(surf,g_reload_ms)
            draw_hud(surf,font,sfont,bigfont,player,lv_idx+1,kills,kt,cur_fps,boss,mode,spd_timer_remain,player2)
            draw_boss_kill(surf,bigfont,font,boss_kill_t)
            if boss_kill_t==0: boss=None
            flip_display(); clock.tick(FPS); continue
        apply_cheat(player, player2)
        # cheat: kill all enemies
        if cheat_kill_all[0]:
            cheat_kill_all[0] = False
            for e in enemies: e.alive=False; kills+=1
        # --- 更新玩家 ---
        if player.alive:
            player.update(held1,mx,my,now,covers,snd)
        # P2 自动瞄准最近的敌人
        if player2 and player2.alive:
            aim_x, aim_y = player2.x + 100, player2.y  # 默认朝右
            alive_enemies = [e for e in enemies if e.alive]
            if alive_enemies:
                nearest_e = min(alive_enemies, key=lambda e: dist((player2.x,player2.y),(e.x,e.y)))
                aim_x, aim_y = nearest_e.x, nearest_e.y
            elif boss and boss.alive and not boss.entering:
                aim_x, aim_y = boss.x, boss.y
            player2.update(held2, aim_x, aim_y, now, covers, snd)
        multi=lv_idx>=1
        # P1 射击
        if player.alive and shooting: player.try_shoot(now,bullets,multi,snd,g_shoot_cd,g_bullet_r,g_bullet_dmg)
        # P2 射击 (Right Shift)
        if player2 and player2.alive and p2_shooting: player2.try_shoot(now,bullets,multi,snd,g_shoot_cd,g_bullet_r,g_bullet_dmg)
        for b in bullets: b.update(covers,g_bullet_r)
        bullets=[b for b in bullets if b.alive]
        for bb in boss_bullets: bb.update(covers)
        boss_bullets=[bb for bb in boss_bullets if bb.alive]
        if not (boss and boss.alive): try_spawn()
        # 敌人追踪最近的存活玩家
        for e in enemies:
            tx, ty = get_nearest_alive_player(e.x, e.y)
            e.update(tx, ty, covers)
        # Boss 追踪最近的存活玩家
        if boss and boss.alive:
            btx, bty = get_nearest_alive_player(boss.x, boss.y)
            boss.update(btx, bty, covers, now, boss_bullets, snd)
        # --- 子弹碰撞检测 ---
        for b in bullets:
            if not b.alive: continue
            for e in enemies:
                if not e.alive: continue
                if dist((b.x,b.y),(e.x,e.y)) < e.r+g_bullet_r:
                    e.hit(b.dmg); b.alive=False
                    if snd: safe_play(snd.get("hit"))
                    for _ in range(5): particles.append(Particle(e.x,e.y,e.color))
                    if not e.alive:
                        if snd: safe_play(snd.get("explode"))
                        score+=(10 if e.r==12 else 15 if e.r==9 else 30); kills+=1
                        for _ in range(10): particles.append(Particle(e.x,e.y,e.color,spd=3))
                        # 补给给存活玩家
                        if random.random()<0.35:
                            target_p = player if player.alive else player2
                            if target_p: target_p.reserve+=random.randint(3,8)
                            safe_play(snd.get("pickup"))
                    break
        for b in bullets:
            if not b.alive: continue
            if boss and boss.alive and not boss.entering:
                if dist((b.x,b.y),(boss.x,boss.y)) < boss.r+g_bullet_r:
                    boss.hit(b.dmg); b.alive=False
                    if snd: safe_play(snd.get("hit"))
                    for _ in range(8): particles.append(Particle(b.x,b.y,C_BOSS_2))
                    if not boss.alive:
                        if snd: safe_play(snd.get("boss_die"))
                        score+=200; kills+=5
                        for _ in range(30):
                            particles.append(Particle(boss.x,boss.y,C_BOSS,spd=4,life=30))
                            particles.append(Particle(boss.x,boss.y,C_BOSS_2,spd=3,life=25))
                        # Boss击杀奖励给所有存活玩家
                        if player.alive: player.reserve+=50; player.hp=min(player.hp+2,player.hp_max)
                        if player2 and player2.alive: player2.reserve+=50; player2.hp=min(player2.hp+2,player2.hp_max)
                        boss_kill_t=150
                    break
        bullets=[b for b in bullets if b.alive]
        enemies=[e for e in enemies if e.alive]
        # --- Boss子弹碰撞 ---
        for bb in boss_bullets:
            if not bb.alive: continue
            if player.alive and dist((bb.x,bb.y),(player.x,player.y)) < bb.r+PLAYER_R:
                player.take_damage(snd); bb.alive=False
            if player2 and player2.alive and dist((bb.x,bb.y),(player2.x,player2.y)) < bb.r+PLAYER_R:
                player2.take_damage(snd); bb.alive=False
        # --- 敌人碰撞 ---
        for e in enemies:
            if player.alive and dist((e.x,e.y),(player.x,player.y)) < e.r+PLAYER_R:
                player.take_damage(snd)
            if player2 and player2.alive and dist((e.x,e.y),(player2.x,player2.y)) < e.r+PLAYER_R:
                player2.take_damage(snd)
        # --- 判断游戏结束（两人都死才算） ---
        if not any_player_alive() and not game_over:
            game_over=True; safe_play(snd.get("game_over"))
        for p in particles: p.update()
        particles=[p for p in particles if p.life>0]
        if kills>=kt and trans_t==0 and boss_kill_t==0:
            nxt=lv_idx+1
            trans_t=now; trans_up=False
            # 无尽模式不限关卡数
            if mode=="ENDLESS":
                nm = LEVELS[min(nxt,len(LEVELS)-1)][3]
                if player.alive and nm>player.mag_size: player.set_mag(nm); player.ammo=min(player.ammo,nm); trans_up=True; safe_play(snd.get("level_up"))
                if player2 and player2.alive and nm>player2.mag_size: player2.set_mag(nm); player2.ammo=min(player2.ammo,nm)
            elif nxt<len(LEVELS):
                nm=LEVELS[nxt][3]
                if player.alive and nm>player.mag_size: player.set_mag(nm); player.ammo=min(player.ammo,nm); trans_up=True; safe_play(snd.get("level_up"))
                if player2 and player2.alive and nm>player2.mag_size: player2.set_mag(nm); player2.ammo=min(player2.ammo,nm)
        if trans_t and now-trans_t>1800:
            lv_idx+=1
            if mode=="ENDLESS":
                _,_,ms,rs,ncv,nspd,nkt = make_level_endless(lv_idx)
            else:
                _,_,ms,rs,ncv,nspd,nkt = make_level(lv_idx)
            if player.alive: player.set_mag(ms); player.reserve=rs
            if player.ammo>ms: player.ammo=ms
            if player2:
                if player2.alive: player2.set_mag(ms); player2.reserve=rs
                if player2.ammo>ms: player2.ammo=ms
                # P2 死了也复活，给基础弹药
                if not player2.alive:
                    player2.alive=True; player2.hp=player2.hp_max//2; player2.inv_timer=120
                    player2.ammo=ms; player2.reserve=rs; player2.reloading=False
                    player2.set_mag(ms)
            covers=ncv; spd=nspd; kt=nkt; kills=0
            enemies.clear(); bullets.clear(); boss_bullets.clear(); trans_t=0; trans_up=False
            level_start_t = now; spd_timer_remain = SPEEDRUN_TIME  # 速通模式重置计时
            if mode != "ENDLESS" and lv_idx in BOSS_LEVELS:
                boss=Boss(lv_idx,covers); boss_warn_t=120; safe_play(snd.get("boss_warn"))
            elif mode == "ENDLESS" and lv_idx in BOSS_LEVELS and lv_idx < len(LEVELS):
                boss=Boss(lv_idx,covers); boss_warn_t=120; safe_play(snd.get("boss_warn"))
            else: boss=None
        surf.fill(C_BG); draw_grid(surf)
        for cv in covers: cv.draw(surf)
        for p in particles: p.draw(surf)
        for e in enemies: e.draw(surf)
        for bb in boss_bullets: bb.draw(surf)
        if boss and boss.alive: boss.draw(surf)
        for b in bullets: b.draw(surf,g_bullet_r)
        player.draw(surf,g_reload_ms)
        if player2: player2.draw(surf,g_reload_ms)
        draw_hud(surf,font,sfont,bigfont,player,lv_idx+1,kills,kt,cur_fps,boss,mode,spd_timer_remain,player2)
        if trans_t: draw_transition(surf,bigfont,font,lv_idx+2,trans_up)
        flip_display()
        clock.tick(FPS)

if __name__=="__main__":
    pygame.init()
    pygame.mixer.init(frequency=SR, size=-16, channels=1, buffer=512)
    _scr = pygame.display.set_mode((W, H))
    _sf  = pygame.Surface((W, H))
    TextInput.set_scale(_scr, _sf)
    pygame.display.set_caption("TopDown Shooter v6")
    def _mkf(size, bold=False):
        try: return pygame.font.SysFont("consolas", size, bold=bold)
        except: return pygame.font.Font(None, size+(4 if bold else 0))
    _font = _mkf(22, True); _sfont = _mkf(15); _bfont = _mkf(48, True)
    # === 登录流程 ===
    logged_user = None
    offline_mode = False
    while logged_user is None:
        result = login_screen(_scr, _sf, _font, _sfont, _bfont)
        if result == "REGISTER":
            r = register_screen(_scr, _sf, _font, _sfont, _bfont)
            if r == "LOGIN":
                continue
            elif r is None:
                pygame.quit(); sys.exit()
            else:
                logged_user = r
        elif result == "OFFLINE":
            logged_user = "OFFLINE_GUEST"
            offline_mode = True
        elif result is None:
            pygame.quit(); sys.exit()
        else:
            logged_user = result
    # === 选关（离线模式只能选前5关）===
    unlocked = 4 if offline_mode else 9   # 0-based 最高可选关卡索引
    sel_result = level_select_screen(_scr, _sf, _font, _sfont, _bfont, unlocked=unlocked)
    if sel_result is None:
        pygame.quit(); sys.exit()
    lv, game_mode = sel_result
    # 离线模式不支持 ENDLESS 和 SPEEDRUN 的全关卡（只是提示，不强制）
    # === 开始游戏 ===
    game(lv, game_mode)
