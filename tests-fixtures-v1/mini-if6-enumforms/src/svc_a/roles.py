# svc_a component — Python frozenset forms (IF-6 named-set, frozenset form).
ROLES = frozenset({"admin", "user"})        # diverges from svc_b.ROLES (missing guest) -> FIRES
PERMS = frozenset({"r", "w"})               # identical to svc_b.PERMS -> same-value, must NOT fire
