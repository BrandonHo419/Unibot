from .rebind_mouse import RebindMouse


def get_mouse_implementation(config):
    print("Using RebindMouse")
    return RebindMouse(config)