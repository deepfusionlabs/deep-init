from pyflags.defs import ROLLOUT

def view():
    ROLLOUT = load_rollout()
    if ROLLOUT:
        return show()
    return None

def load_rollout():
    return True
def show():
    return 1
