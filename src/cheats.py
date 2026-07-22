
import win32api


class Cheats:
    def __init__(self, config):
        self.cfg = config
        self.move_x, self.move_y = (0, 0)
        self.previous_x, self.previous_y = (0, 0)
        self.recoil_offset = 0

        # Aim starts enabled, but movement is only calculated while one of the
        # configured aim keys is physically held. F2 remains a master toggle.
        self.aim_state = True
        self.recoil_state = False

    def toggle_aim(self):
        self.aim_state = not self.aim_state

        if not self.aim_state:
            self.previous_x, self.previous_y = (0, 0)

        print(f"AIM: {self.aim_state}")

    def toggle_recoil(self):
        self.recoil_state = not self.recoil_state
        print(f"RECOIL: {self.recoil_state}")

    def get_aim_state(self):
        # F2 can disable aim globally.
        if not self.aim_state:
            return False

        # "off" means aim does not require a held key.
        if self.cfg.aim_keys[0] == "off":
            return True

        # Otherwise, aim is active only while a configured key is held.
        return any(
            win32api.GetAsyncKeyState(key) < 0
            for key in self.cfg.aim_keys
        )

    def calculate_aim(self, state, target):
        if not state or target is None:
            return

        x, y = target
        x *= self.cfg.speed
        y *= self.cfg.speed * self.cfg.y_speed_multiplier

        x = (
            (1 - self.cfg.aim_smoothing_factor) * self.previous_x
            + self.cfg.aim_smoothing_factor * x
        )
        y = (
            (1 - self.cfg.aim_smoothing_factor) * self.previous_y
            + self.cfg.aim_smoothing_factor * y
        )

        self.previous_x, self.previous_y = (x, y)
        self.move_x, self.move_y = (x, y)

    def apply_recoil(self, state, delta_time):
        if not state or delta_time == 0:
            self.recoil_offset = 0
            return

        mouse1_down = win32api.GetAsyncKeyState(0x01) < 0

        if self.cfg.recoil_mode == "move" and mouse1_down:
            self.move_x += self.cfg.recoil_x * delta_time
            self.move_y += self.cfg.recoil_y * delta_time

        elif self.cfg.recoil_mode == "offset":
            self._update_recoil_offset(delta_time)

    def _update_recoil_offset(self, delta_time):
        mouse1_down = win32api.GetAsyncKeyState(0x01) < 0

        if mouse1_down:
            self.recoil_offset += self.cfg.recoil_y * delta_time
            self.recoil_offset = min(
                self.recoil_offset,
                self.cfg.max_offset,
            )
        else:
            self.recoil_offset -= (
                self.cfg.recoil_recover * delta_time
            )
            self.recoil_offset = max(self.recoil_offset, 0)