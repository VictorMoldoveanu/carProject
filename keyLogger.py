import math
import threading
import time

import keyboard
import pygame
import serial

PORT = 'COM6'
BAUD = 9600

# steering is sent as a single character from 0-110 (0 = full right, 55 = straight, 110 = full left)
# which lines up with the servo range on the car (35-145 degrees, so angle = value + 35)
STEER_MAX = 110
STEER_CENTER = STEER_MAX // 2

# how far the wheel graphic rotates at full lock, and how fast it moves
WHEEL_LOCK_DEG = 135
KEY_TURN_SPEED = 540   # degrees per second while holding an arrow key
RETURN_SPEED = 400     # degrees per second when the wheel springs back to center

WIDTH, HEIGHT = 960, 690
WHEEL_RADIUS = 175
WHEEL_CENTER = (330, 360)
HUB_RADIUS = int(WHEEL_RADIUS * 0.30)  # the round horn button in the middle of the wheel
FPS = 50  # also the rate packets are sent at, same as the old 0.02s loop

# colors
BG_TOP = (18, 20, 28)
BG_BOTTOM = (8, 9, 13)
CARD = (27, 30, 40)
CARD_EDGE = (44, 48, 62)
TEXT = (232, 236, 245)
SUBTEXT = (130, 138, 158)
ACCENT = (0, 196, 255)
GREEN = (60, 220, 130)
RED = (255, 72, 88)
AMBER = (255, 190, 60)


class CarLink:
    """Keeps the serial connection to the arduino alive in the background so the window never freezes."""

    def __init__(self, port, baud):
        self.port = port
        self.baud = baud
        self.ser = None
        self.connecting = False
        self.connect()

    def connect(self):
        if self.connecting:
            return
        self.connecting = True
        threading.Thread(target=self._connect, daemon=True).start()

    def _connect(self):
        while True:
            try:
                ser = serial.Serial(self.port, self.baud)
                time.sleep(2)  # arduino resets when the port opens
                self.ser = ser
                break
            except serial.SerialException:
                time.sleep(2)
        self.connecting = False

    @property
    def connected(self):
        return self.ser is not None

    def send(self, packet):
        if self.ser is None:
            return
        try:
            self.ser.write(packet)
        except serial.SerialException:
            self.ser = None
            self.connect()

    def close(self):
        if self.ser is not None:
            self.ser.close()


def build_packet(steer, c2, c3, c4, c5):
    # SAFETY: every packet goes through here, so this is the last chance to make sure the steering
    # value can never ask the servo to go past 35 or 145 (value + 35 on the car)
    steer = max(0, min(STEER_MAX, int(steer)))
    # arduino reads until '\n' (character 10), so a steering value of 10 would cut the message short
    if steer == 10:
        steer = 11
    return bytes([steer]) + (c2 + c3 + c4 + c5 + '\n').encode()


def steer_value(wheel_deg):
    # wheel turned right (positive degrees) -> smaller value -> servo turns right
    value = round(STEER_CENTER - wheel_deg / WHEEL_LOCK_DEG * STEER_CENTER)
    return max(0, min(STEER_MAX, value))


def approach(value, target, step):
    if value < target:
        return min(value + step, target)
    return max(value - step, target)


def polar(center, radius, deg):
    rad = math.radians(deg)
    return (center[0] + radius * math.cos(rad), center[1] + radius * math.sin(rad))


def make_gradient(w, h, top, bottom):
    surf = pygame.Surface((w, h))
    for y in range(h):
        t = y / (h - 1)
        color = [round(top[i] + (bottom[i] - top[i]) * t) for i in range(3)]
        pygame.draw.line(surf, color, (0, y), (w, y))
    return surf


def make_wheel(radius, font):
    """Draws the steering wheel at 2x size so it stays smooth when rotozoom shrinks it each frame."""
    r = radius * 2
    size = r * 2 + 8
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    c = (size // 2, size // 2)
    rim_w = int(r * 0.17)
    inner = r - rim_w

    # leather rim with a soft highlight
    pygame.draw.circle(surf, (14, 15, 19), c, r)
    pygame.draw.circle(surf, (38, 40, 48), c, r - 4)
    pygame.draw.circle(surf, (58, 61, 72), c, r - rim_w // 3, 5)
    pygame.draw.circle(surf, (14, 15, 19), c, inner + 4)
    pygame.draw.circle(surf, (0, 0, 0, 0), c, inner)

    # grip ridges around the rim
    for deg in range(0, 360, 8):
        if -110 < deg - 360 < -70 or -110 < deg < -70:
            continue
        pygame.draw.line(surf, (28, 30, 36), polar(c, inner + 8, deg), polar(c, r - 8, deg), 3)

    # red center marker at 12 o'clock so you can see how far it's turned
    marker = [polar(c, inner + 2, d) for d in range(-97, -82)] + [polar(c, r - 2, d) for d in range(-83, -98, -1)]
    pygame.draw.polygon(surf, RED, marker)

    # three spokes
    hub_r = int(r * 0.30)
    for deg, w1, w2 in ((180, 92, 60), (0, 92, 60), (90, 110, 70)):
        d = (math.cos(math.radians(deg)), math.sin(math.radians(deg)))
        p = (-d[1], d[0])
        a, b = hub_r - 10, inner + 6
        pts = [
            (c[0] + d[0] * a + p[0] * w1 / 2, c[1] + d[1] * a + p[1] * w1 / 2),
            (c[0] + d[0] * b + p[0] * w2 / 2, c[1] + d[1] * b + p[1] * w2 / 2),
            (c[0] + d[0] * b - p[0] * w2 / 2, c[1] + d[1] * b - p[1] * w2 / 2),
            (c[0] + d[0] * a - p[0] * w1 / 2, c[1] + d[1] * a - p[1] * w1 / 2),
        ]
        pygame.draw.polygon(surf, (72, 76, 88), pts)
        pygame.draw.polygon(surf, (104, 110, 126), pts, 4)

    # hub
    pygame.draw.circle(surf, (14, 15, 19), c, hub_r + 6)
    pygame.draw.circle(surf, (34, 36, 44), c, hub_r)
    pygame.draw.circle(surf, ACCENT, c, hub_r - 10, 6)
    pygame.draw.circle(surf, (22, 24, 30), c, hub_r - 16)
    label = font.render('FLOAT', True, TEXT)
    surf.blit(label, label.get_rect(center=c))
    return surf


def make_shadow(radius):
    size = radius * 2 + 80
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(surf, (0, 0, 0, 150), (size // 2, size // 2), radius + 6)
    # cheap blur: shrink then grow back
    small = pygame.transform.smoothscale(surf, (size // 10, size // 10))
    return pygame.transform.smoothscale(small, (size, size))


def make_glow(radius, color):
    size = radius * 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    for i in range(radius, 0, -4):
        alpha = int(26 * (1 - i / radius) ** 2)
        pygame.draw.circle(surf, (*color, alpha), (radius, radius), i)
    return surf


def draw_dot(surf, color, pos, r):
    x, y = round(pos[0]), round(pos[1])
    pygame.draw.circle(surf, color, (x, y), r)


def draw_gauge(screen, center, radius, wheel_deg, font_small):
    # tick marks across the full steering range
    for deg in range(-WHEEL_LOCK_DEG, WHEEL_LOCK_DEG + 1, 15):
        major = deg % 45 == 0
        a = polar(center, radius - (10 if major else 6), deg - 90)
        b = polar(center, radius + 2, deg - 90)
        pygame.draw.aaline(screen, (90, 96, 116) if major else (55, 60, 74), a, b)

    for deg, text in ((-WHEEL_LOCK_DEG, 'L'), (WHEEL_LOCK_DEG, 'R')):
        label = font_small.render(text, True, SUBTEXT)
        screen.blit(label, label.get_rect(center=polar(center, radius + 20, deg - 90)))

    # filled arc from center to the current angle
    track_r = radius + 10
    for deg in range(-WHEEL_LOCK_DEG, WHEEL_LOCK_DEG + 1, 2):
        draw_dot(screen, (36, 40, 52), polar(center, track_r, deg - 90), 3)
    step = 1 if wheel_deg >= 0 else -1
    for deg in range(0, round(wheel_deg) + step, step):
        draw_dot(screen, ACCENT, polar(center, track_r, deg - 90), 3)
    draw_dot(screen, TEXT, polar(center, track_r, wheel_deg - 90), 6)
    draw_dot(screen, ACCENT, polar(center, track_r, wheel_deg - 90), 4)


def draw_arrow(screen, center, direction, size, color):
    # direction is -1 for a left arrow, 1 for a right arrow
    x, y = center
    s = size / 2
    pts = [(x + direction * s, y), (x, y - s), (x, y - s * 0.45), (x - direction * s, y - s * 0.45),
           (x - direction * s, y + s * 0.45), (x, y + s * 0.45), (x, y + s)]
    pygame.draw.polygon(screen, color, pts)


def draw_hazard(screen, center, size, color):
    x, y = center
    outer = [(x, y - size * 0.55), (x + size * 0.55, y + size * 0.4), (x - size * 0.55, y + size * 0.4)]
    inner = [(x, y - size * 0.18), (x + size * 0.27, y + size * 0.24), (x - size * 0.27, y + size * 0.24)]
    pygame.draw.polygon(screen, color, outer, 3)
    pygame.draw.polygon(screen, color, inner, 2)


def draw_card(screen, rect, title, font_label):
    pygame.draw.rect(screen, CARD, rect, border_radius=16)
    pygame.draw.rect(screen, CARD_EDGE, rect, 1, border_radius=16)
    label = font_label.render(title, True, SUBTEXT)
    screen.blit(label, (rect.x + 18, rect.y + 14))


def draw_pill(screen, text, font, color, right_x, center_y, filled):
    label = font.render(text, True, (12, 14, 20) if filled else color)
    rect = label.get_rect()
    rect.inflate_ip(24, 10)
    rect.midright = (right_x, center_y)
    if filled:
        pygame.draw.rect(screen, color, rect, border_radius=rect.height // 2)
    else:
        pygame.draw.rect(screen, color, rect, 2, border_radius=rect.height // 2)
    screen.blit(label, label.get_rect(center=rect.center))


def main():
    pygame.init()
    pygame.display.set_caption('FLOAT Car Controller')
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    font_hub = pygame.font.SysFont('segoeui', 44, bold=True)
    font_big = pygame.font.SysFont('segoeui', 46, bold=True)
    font_mid = pygame.font.SysFont('segoeui', 20, bold=True)
    font_label = pygame.font.SysFont('segoeui', 14, bold=True)
    font_small = pygame.font.SysFont('segoeui', 14)

    background = make_gradient(WIDTH, HEIGHT, BG_TOP, BG_BOTTOM)
    wheel_img = make_wheel(WHEEL_RADIUS, font_hub)
    shadow = make_shadow(WHEEL_RADIUS)
    glow = make_glow(WHEEL_RADIUS + 120, ACCENT)

    link = CarLink(PORT, BAUD)

    wheel_deg = 0.0
    dragging = False
    horn_held = False
    last_mouse_angle = 0.0
    l_was_down = False
    headlights_on = True  # the car starts with headlights on

    # turn signals: a/d turn a blinker on until the turn is finished, s toggles hazards
    a_was_down = False
    d_was_down = False
    s_was_down = False
    turn_started = False  # set once the wheel leaves straight while a blinker is on
    left_signal_on = False
    right_signal_on = False
    hazards_on = False
    signal_events = []  # only 1 signal character fits per packet, so extras wait for the next one

    running = True
    while running:
        dt = clock.tick(FPS) / 1000

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                dx, dy = event.pos[0] - WHEEL_CENTER[0], event.pos[1] - WHEEL_CENTER[1]
                if math.hypot(dx, dy) <= HUB_RADIUS:
                    horn_held = True  # pressing the middle of the wheel honks like a real car
                elif math.hypot(dx, dy) <= WHEEL_RADIUS + 30:
                    dragging = True
                    last_mouse_angle = math.degrees(math.atan2(dy, dx))
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging = False
                horn_held = False
            elif event.type == pygame.WINDOWFOCUSLOST:
                # the mouse release can get lost if you click another window, so never leave the horn stuck on
                dragging = False
                horn_held = False
            elif event.type == pygame.MOUSEMOTION and not dragging:
                dx, dy = event.pos[0] - WHEEL_CENTER[0], event.pos[1] - WHEEL_CENTER[1]
                over_hub = math.hypot(dx, dy) <= HUB_RADIUS
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if over_hub else pygame.SYSTEM_CURSOR_ARROW)
            elif event.type == pygame.MOUSEMOTION and dragging:
                dx, dy = event.pos[0] - WHEEL_CENTER[0], event.pos[1] - WHEEL_CENTER[1]
                angle = math.degrees(math.atan2(dy, dx))
                # wrap the change into -180..180 so crossing the left side doesn't jump
                delta = (angle - last_mouse_angle + 180) % 360 - 180
                last_mouse_angle = angle
                wheel_deg = max(-WHEEL_LOCK_DEG, min(WHEEL_LOCK_DEG, wheel_deg + delta))

        # arrow keys turn the wheel, otherwise it springs back to center like a real car
        left = keyboard.is_pressed('left') and not keyboard.is_pressed('right')
        right = keyboard.is_pressed('right') and not keyboard.is_pressed('left')
        if left:
            wheel_deg = approach(wheel_deg, -WHEEL_LOCK_DEG, KEY_TURN_SPEED * dt)
        elif right:
            wheel_deg = approach(wheel_deg, WHEEL_LOCK_DEG, KEY_TURN_SPEED * dt)
        elif not dragging:
            wheel_deg = approach(wheel_deg, 0, RETURN_SPEED * dt)
        steer = steer_value(wheel_deg)

        # logs inputs for driving
        c2 = 'x'
        if (keyboard.is_pressed('up') and not keyboard.is_pressed('down')):
            c2 = 'w'
        if (keyboard.is_pressed('down') and not keyboard.is_pressed('up')):
            c2 = 's'

        # horn
        c3 = 'x'
        if (keyboard.is_pressed('h') or horn_held):
            c3 = 'h'

        # switches headlights by keeping last input stored to only send 1 data packet at a time
        c4 = 'x'
        l_is_down = keyboard.is_pressed('l')
        if (l_is_down and not l_was_down):
            c4 = 'l'
            headlights_on = not headlights_on
        l_was_down = l_is_down

        # turn signals and hazards work like the headlights: the character is only sent once when the
        # key is pressed, otherwise 'x'
        a_is_down = keyboard.is_pressed('a')
        if (a_is_down and not a_was_down):
            signal_events.append('a')
        a_was_down = a_is_down

        d_is_down = keyboard.is_pressed('d')
        if (d_is_down and not d_was_down):
            signal_events.append('d')
        d_was_down = d_is_down

        s_is_down = keyboard.is_pressed('s')
        if (s_is_down and not s_was_down):
            signal_events.append('s')
        s_was_down = s_is_down

        c5 = signal_events.pop(0) if signal_events else 'x'

        # arduino code waits until \n to process the message to make sure the whole thing is recieved
        packet = build_packet(steer, c2, c3, c4, c5)
        link.send(packet)
        servo_angle = packet[0] + 35  # the angle the car will actually write to the steering servo

        # the blinker variables are just for the dashboard and copy exactly what carProject.ino does with
        # the packet: whichever signal key was sent last wins, and a blinker turns off once the steering
        # has left straight and come back (the turn is finished), no matter if it was the keys or the wheel
        if (c5 == 'a'):
            left_signal_on, right_signal_on, hazards_on = True, False, False
        elif (c5 == 'd'):
            left_signal_on, right_signal_on, hazards_on = False, True, False
        elif (c5 == 's'):
            left_signal_on, right_signal_on, hazards_on = False, False, not hazards_on
        if (c5 == 'a' or c5 == 'd'):
            turn_started = False
        if (left_signal_on or right_signal_on):
            if (packet[0] != STEER_CENTER):
                turn_started = True
            elif (turn_started):
                left_signal_on = right_signal_on = False

        # ---------- drawing ----------
        screen.blit(background, (0, 0))
        screen.blit(glow, glow.get_rect(center=WHEEL_CENTER))
        screen.blit(shadow, shadow.get_rect(center=(WHEEL_CENTER[0] + 6, WHEEL_CENTER[1] + 14)))

        rotated = pygame.transform.rotozoom(wheel_img, -wheel_deg, 0.5)
        screen.blit(rotated, rotated.get_rect(center=WHEEL_CENTER))
        if c3 == 'h':
            # light up the horn button while honking
            pygame.draw.circle(screen, AMBER, WHEEL_CENTER, HUB_RADIUS - 3, 6)
            honk = font_label.render('HONK', True, AMBER)
            screen.blit(honk, honk.get_rect(center=(WHEEL_CENTER[0], WHEEL_CENTER[1] + HUB_RADIUS + 14)))
        draw_gauge(screen, WHEEL_CENTER, WHEEL_RADIUS + 34, wheel_deg, font_small)

        title = font_mid.render('FLOAT CAR CONTROLLER', True, TEXT)
        screen.blit(title, (28, 22))
        hint = font_small.render('Drag the wheel or use the arrow keys', True, SUBTEXT)
        screen.blit(hint, (28, 48))

        panel_x, panel_w = 620, 312

        # steering card
        card = pygame.Rect(panel_x, 28, panel_w, 150)
        draw_card(screen, card, 'STEERING', font_label)
        value = font_big.render(f'{servo_angle}°', True, TEXT)
        screen.blit(value, (card.x + 18, card.y + 30))
        unit = font_small.render(f'{STEER_MAX + 35} – 35', True, SUBTEXT)
        screen.blit(unit, (card.x + 24 + value.get_width(), card.y + 58))
        if steer > STEER_CENTER:
            direction, color = 'LEFT', ACCENT
        elif steer < STEER_CENTER:
            direction, color = 'RIGHT', ACCENT
        else:
            direction, color = 'STRAIGHT', SUBTEXT
        draw_pill(screen, direction, font_label, color, card.right - 18, card.y + 62, steer != STEER_CENTER)

        bar = pygame.Rect(card.x + 18, card.y + 108, card.width - 36, 10)
        pygame.draw.rect(screen, (40, 44, 58), bar, border_radius=5)
        mid_x = bar.centerx
        pos_x = bar.x + (STEER_MAX - steer) / STEER_MAX * bar.width
        fill = pygame.Rect(min(mid_x, pos_x), bar.y, abs(pos_x - mid_x), bar.height)
        if fill.width:
            pygame.draw.rect(screen, ACCENT, fill, border_radius=5)
        pygame.draw.line(screen, SUBTEXT, (mid_x, bar.y - 4), (mid_x, bar.bottom + 3), 2)
        draw_dot(screen, TEXT, (pos_x, bar.centery), 8)
        for text, x, anchor in (('L', bar.x, 'topleft'), ('R', bar.right, 'topright')):
            label = font_small.render(text, True, SUBTEXT)
            screen.blit(label, label.get_rect(**{anchor: (x, bar.bottom + 4)}))

        # drive card
        card = pygame.Rect(panel_x, 194, panel_w, 70)
        draw_card(screen, card, 'DRIVE', font_label)
        drive = {'w': ('FORWARD', GREEN), 's': ('REVERSE', AMBER)}.get(c2, ('STOPPED', SUBTEXT))
        draw_pill(screen, drive[0], font_label, drive[1], card.right - 18, card.centery, c2 != 'x')
        keys = font_small.render('Up / Down', True, SUBTEXT)
        screen.blit(keys, (card.x + 18, card.y + 38))

        # horn card
        card = pygame.Rect(panel_x, 280, panel_w, 70)
        draw_card(screen, card, 'HORN', font_label)
        draw_pill(screen, 'HONK' if c3 == 'h' else 'OFF', font_label, AMBER if c3 == 'h' else SUBTEXT,
                  card.right - 18, card.centery, c3 == 'h')
        keys = font_small.render('Hold H', True, SUBTEXT)
        screen.blit(keys, (card.x + 18, card.y + 38))

        # headlights card
        card = pygame.Rect(panel_x, 366, panel_w, 70)
        draw_card(screen, card, 'HEADLIGHTS', font_label)
        draw_pill(screen, 'ON' if headlights_on else 'OFF', font_label, AMBER if headlights_on else SUBTEXT,
                  card.right - 18, card.centery, headlights_on)
        keys = font_small.render('Press L to toggle', True, SUBTEXT)
        screen.blit(keys, (card.x + 18, card.y + 38))

        # signals card
        blink_on = (pygame.time.get_ticks() // 400) % 2 == 0
        left_lit = (left_signal_on or hazards_on) and blink_on
        right_lit = (right_signal_on or hazards_on) and blink_on
        off_color = (58, 63, 80)
        card = pygame.Rect(panel_x, 452, panel_w, 70)
        draw_card(screen, card, 'SIGNALS', font_label)
        keys = font_small.render('A / D blinkers,  S hazards', True, SUBTEXT)
        screen.blit(keys, (card.x + 18, card.y + 38))
        draw_arrow(screen, (card.right - 112, card.centery), -1, 26, AMBER if left_lit else off_color)
        draw_hazard(screen, (card.right - 72, card.centery + 1), 30,
                    RED if hazards_on and blink_on else off_color)
        draw_arrow(screen, (card.right - 32, card.centery), 1, 26, AMBER if right_lit else off_color)

        # big blinkers on either side of the wheel
        for direction, lit in ((-1, left_lit), (1, right_lit)):
            pos = (WHEEL_CENTER[0] + direction * (WHEEL_RADIUS + 50), WHEEL_CENTER[1] - WHEEL_RADIUS - 40)
            draw_arrow(screen, pos, direction, 38, AMBER if lit else (34, 37, 48))

        # connection card
        card = pygame.Rect(panel_x, 538, panel_w, 70)
        draw_card(screen, card, 'CONNECTION', font_label)
        if link.connected:
            status, color = f'{PORT} connected', GREEN
        else:
            blink = (pygame.time.get_ticks() // 500) % 2 == 0
            status, color = f'Looking for car on {PORT}...', RED if blink else (120, 40, 50)
        draw_dot(screen, color, (card.x + 24, card.y + 47), 5)
        label = font_small.render(status, True, TEXT)
        screen.blit(label, (card.x + 38, card.y + 37))

        footer = font_small.render('Close the window to stop the car', True, SUBTEXT)
        screen.blit(footer, (panel_x, 626))

        pygame.display.flip()

    # leave the car straight and stopped when closing, and switch the hazards off if they are still on
    if hazards_on:
        signal_events.append('s')
    for c5 in signal_events or ['x']:
        link.send(build_packet(STEER_CENTER, 'x', 'x', 'x', c5))
        time.sleep(1 / FPS)
    link.close()
    pygame.quit()


if __name__ == '__main__':
    main()
