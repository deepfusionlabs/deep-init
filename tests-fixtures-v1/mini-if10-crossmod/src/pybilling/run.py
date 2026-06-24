from pycfg.env import DEBUG
from pycfg.env import MODE2

def run(user):
    if DEBUG:
        b()
    if MODE2 == 'on' and user.is_admin:
        c()

def b():
    pass
def c():
    pass
