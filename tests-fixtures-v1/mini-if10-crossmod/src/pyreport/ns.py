import pyflags.defs as F

def ns():
    if F.NEW_CHECKOUT:
        return 1
    return 0
