import time
import logging
from typing import Optional, Dict, List, Tuple
from modules.core.state import state

logger = logging.getLogger(__name__)

class FluidNCLedController:
    """LED Controller that sends M150 commands to FluidNC over Serial/WebSocket connection"""

    def __init__(self):
        self._powered_on = False
        self.brightness = 0.35
        self._color1 = (255, 255, 255)
        self._color2 = (0, 0, 0)
        self._color3 = (0, 0, 0)
        self._current_effect_id = 0
        self._current_palette_id = 0
        self._speed = 128
        self._intensity = 128

    def _send_m150(self, r, g, b):
        if state.conn and state.conn.is_connected():
            scaled_r = int(r * self.brightness)
            scaled_g = int(g * self.brightness)
            scaled_b = int(b * self.brightness)
            # FluidNC custom firmware expects: M150 X<r> Y<g> Z<b>
            cmd = f"M150 X{scaled_r} Y{scaled_g} Z{scaled_b}\n"
            try:
                logger.info(f"Sending FluidNC LED command: {cmd.strip()}")
                state.conn.send(cmd)
            except Exception as e:
                logger.error(f"Failed to send FluidNC M150 command: {e}")

    def set_power(self, state_val: int) -> Dict:
        if state_val == 2:  # Toggle
            self._powered_on = not self._powered_on
        else:
            self._powered_on = bool(state_val)

        if self._powered_on:
            self._send_m150(*self._color1)
        else:
            self._send_m150(0, 0, 0)

        return {
            "connected": True,
            "power_on": self._powered_on,
            "message": f"Power {'on' if self._powered_on else 'off'}"
        }

    def set_brightness(self, value: int) -> Dict:
        self.brightness = max(0.0, min(1.0, value / 100.0))
        if self._powered_on:
            self._send_m150(*self._color1)
        return {
            "connected": True,
            "brightness": value,
            "message": "Brightness updated"
        }

    def set_color(self, r: int, g: int, b: int) -> Dict:
        self._color1 = (r, g, b)
        self._powered_on = True
        self._send_m150(r, g, b)
        return {
            "connected": True,
            "color": [r, g, b],
            "power_on": True,
            "message": "Color set"
        }

    def set_colors(self, color1: Optional[Tuple[int, int, int]] = None,
                   color2: Optional[Tuple[int, int, int]] = None,
                   color3: Optional[Tuple[int, int, int]] = None) -> Dict:
        if color1 is not None:
            self._color1 = color1
        if color2 is not None:
            self._color2 = color2
        if color3 is not None:
            self._color3 = color3

        if self._powered_on:
            self._send_m150(*self._color1)

        return {
            "connected": True,
            "colors": {
                "color1": self._color1,
                "color2": self._color2,
                "color3": self._color3
            },
            "message": "Colors updated"
        }

    def set_effect(self, effect_id: int, speed: Optional[int] = None,
                   intensity: Optional[int] = None) -> Dict:
        self._current_effect_id = effect_id
        if speed is not None:
            self._speed = speed
        if intensity is not None:
            self._intensity = intensity
        
        if self._powered_on:
            if effect_id == 0:
                self._send_m150(*self._color1)
            else:
                self._send_esp150_effect(effect_id)

        effects_map = {0: "Solid", 1: "Breathing", 2: "Pulse", 3: "Wave", 4: "Rainbow", 5: "Flow"}
        return {
            "connected": True,
            "effect_id": effect_id,
            "effect_name": effects_map.get(effect_id, "Unknown"),
            "power_on": True,
            "message": "Effect set"
        }

    def set_palette(self, palette_id: int) -> Dict:
        self._current_palette_id = palette_id
        return {
            "connected": True,
            "palette_id": palette_id,
            "palette_name": "Default",
            "power_on": True,
            "message": "Palette set"
        }

    def set_speed(self, speed: int) -> Dict:
        self._speed = speed
        return {"connected": True, "speed": speed, "message": "Speed updated"}

    def set_intensity(self, intensity: int) -> Dict:
        self._intensity = intensity
        return {"connected": True, "intensity": intensity, "message": "Intensity updated"}

    def check_status(self) -> Dict:
        colors = []
        for col in [self._color1, self._color2, self._color3]:
            colors.append(f"#{col[0]:02x}{col[1]:02x}{col[2]:02x}")
        
        return {
            "connected": state.conn is not None and state.conn.is_connected(),
            "power_on": self._powered_on,
            "num_leds": 0,
            "gpio_pin": 13,
            "brightness": int(self.brightness * 100),
            "current_effect": self._current_effect_id,
            "current_palette": self._current_palette_id,
            "speed": self._speed,
            "intensity": self._intensity,
            "colors": colors,
            "effect_running": False
        }

    def _send_esp150_effect(self, effect_id: int):
        if state.conn and state.conn.is_connected():
            cmd = f"[ESP150]EFFECT={effect_id}\n"
            try:
                logger.info(f"Sending FluidNC LED effect command: {cmd.strip()}")
                state.conn.send(cmd)
            except Exception as e:
                logger.error(f"Failed to send FluidNC ESP150 effect command: {e}")

    def get_effects(self) -> List[Tuple[int, str]]:
        return [
            (0, "Solid"),
            (1, "Breathing"),
            (2, "Pulse"),
            (3, "Wave"),
            (4, "Rainbow"),
            (5, "Flow")
        ]

    def get_palettes(self) -> List[Tuple[int, str]]:
        return [(0, "Default")]

    def stop(self):
        pass


def effect_loading(controller: FluidNCLedController) -> bool:
    controller.set_power(1)
    controller.set_color(255, 165, 0)  # Orange
    return True

def effect_idle(controller: FluidNCLedController, effect_settings: Optional[dict] = None) -> bool:
    controller.set_power(1)
    if effect_settings and "color1" in effect_settings:
        c = effect_settings["color1"]
        r = int(c[1:3], 16)
        g = int(c[3:5], 16)
        b = int(c[5:7], 16)
        controller.set_color(r, g, b)
    else:
        controller.set_color(255, 255, 255)
    return True

def effect_connected(controller: FluidNCLedController) -> bool:
    controller.set_power(1)
    controller.set_color(0, 255, 0)  # Green
    time.sleep(1.0)
    controller.set_color(255, 255, 255)
    return True

def effect_playing(controller: FluidNCLedController, effect_settings: Optional[dict] = None) -> bool:
    controller.set_power(1)
    if effect_settings and "color1" in effect_settings:
        c = effect_settings["color1"]
        r = int(c[1:3], 16)
        g = int(c[3:5], 16)
        b = int(c[5:7], 16)
        controller.set_color(r, g, b)
    else:
        controller.set_color(0, 0, 255)  # Blue
    return True
