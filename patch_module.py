from collections import defaultdict
import importlib
import sys

class ModulePatchRegister:
    register = defaultdict(list)
    @classmethod
    def register_patch(cls, mod_name, func):
        cls.register[mod_name].append(func)

    @classmethod
    def is_module_patched(cls, name):
        return name in cls.register

    @classmethod
    def get_module_patches(cls, name):
        return cls.register[name]
    
class PatchMetaPathFinder:
    def __init__(self):
        self.skip = set()
        
    def find_module(self, name, path):
        if name in self.skip:
           return None
        self.skip.add(name)
        return PatchModuleLoader(self)

class PatchModuleLoader:
    def __init__(self, finder):
        self._finder = finder

    def load_module(self, name):
        mod = importlib.import_module(name)
        if ModulePatchRegister.is_module_patched(name):
            for patch in ModulePatchRegister.get_module_patches(name):
                patch(mod)
        self._finder.skip.remove(name)
        return mod

sys.meta_path.insert(0, PatchMetaPathFinder())

def when_importing(modname):
    def decorated(func):
        if modname in sys.modules:
            func(sys.modules[modname])
        else:
            ModulePatchRegister.register_patch(modname, func)
    return decorated


# For demo purpose
@when_importing("threading")
def warn(mod):
    print "Warning, you are entering dangerous territory!"

@when_importing("math")
def new_math(mod):
    def new_abs(num):
        return num if num<0 else -num
    mod.abs = new_abs
