from pyconfig.build import LEGACY_MODE

def process():
    if not LEGACY_MODE:
        return use_new()
    return use_legacy()

def use_new():
    return 1
def use_legacy():
    return 0
