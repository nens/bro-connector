from main.settings.base import MODULES

BRO_TYPES = ()

for module in MODULES:
    BRO_TYPES += ((f"{module}".upper(), f"{module}".upper()),)

BRO_HANDLERS = (("KvK", "KvK"), ("Shape", "Shape"))
