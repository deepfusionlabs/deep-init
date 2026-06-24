from pynew.mode import MODE
from pyflags.defs import REBOUND

def use():
    if MODE:
        do_mode()
    if REBOUND:
        do_rebound()

def do_mode():
    pass
def do_rebound():
    pass
