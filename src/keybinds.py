
import win32api
from time import sleep


class KeybindManager:
    """Handles keyboard and physical mouse-button state checking."""

    def __init__(self, config):
        self.cfg = config
        self.delay = 0.25

    def check_key_binds(self, cheats):
        """
        Check the reload, toggle and exit keys.

        Returns True when the configuration should be reloaded.
        """
        if win32api.GetAsyncKeyState(
            self.cfg.key_reload_config
        ) < 0:
            return True

        if win32api.GetAsyncKeyState(
            self.cfg.key_toggle_aim
        ) < 0:
            cheats.toggle_aim()
            sleep(self.delay)

        if win32api.GetAsyncKeyState(
            self.cfg.key_toggle_recoil
        ) < 0:
            cheats.toggle_recoil()
            sleep(self.delay)

        if win32api.GetAsyncKeyState(
            self.cfg.key_exit
        ) < 0:
            print("Exiting")
            raise SystemExit(0)

        return False

    def get_trigger_state(self):
        return (
            win32api.GetAsyncKeyState(self.cfg.key_trigger) < 0
        )

    def get_rapid_fire_state(self):
        # A value of None means key_rapid_fire was set to "off".
        return (
            self.cfg.key_rapid_fire is not None
            and win32api.GetAsyncKeyState(
                self.cfg.key_rapid_fire
            ) < 0
        )