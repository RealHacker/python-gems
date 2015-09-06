import importlib
import os, sys

cur_path = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(cur_path)
sys.path.insert(0,parentdir)

modules = ["."+os.path.splitext(module_file)[0] for module_file in os.listdir(cur_path)]
for module in modules:
    if "__init__" not in module:
        importlib.import_module(module, __package__)
