# svc_b component — Python frozenset forms.
ROLES = frozenset({"admin", "user", "guest"})   # has guest; svc_a.ROLES lacks it -> divergent membership
PERMS = frozenset({"r", "w"})                    # identical to svc_a.PERMS -> same-value clone, must NOT fire
