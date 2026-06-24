from pyforks import FORKED

def use():
    if FORKED:
        return 1
    return 0
