from pyflags.defs import NEW_CHECKOUT

def checkout():
    if NEW_CHECKOUT:
        return run_new()
    return run_legacy()

def run_new():
    return 1
def run_legacy():
    return 0
