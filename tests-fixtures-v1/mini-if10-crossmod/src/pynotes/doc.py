from pyflags.defs import STRFLAG
# example:  if STRFLAG:  (documentation only)

def doc(cfg):
    log("guarded by if STRFLAG")
    if cfg.flag:
        return 1
    return 0

def log(_):
    pass
