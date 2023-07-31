import os

from inspect import isclass
from pkgutil import iter_modules
from importlib import import_module

from .action import Action
from .emote import Emote

ACTION_DICT = {}
EMOTE_DICT = {}

# iterate through the modules in the current package
package_dir = os.path.abspath(__file__)
for (_, module_name, _) in iter_modules([str(package_dir)]):

    # import the module and iterate through its attributes
    module = import_module(f"{__name__}.{module_name}")
    for attribute_name in dir(module):
        attribute = getattr(module, attribute_name)

        if isclass(attribute):            
            # Add the class to this package's variables
            globals()[attribute_name] = attribute
            if issubclass(attribute, Action) and attribute_name != 'Action':
                ACTION_DICT.update({attribute_name.lower(): attribute})
            elif issubclass(attribute, Emote) and attribute_name != 'Emote':
                EMOTE_DICT.update({attribute_name.lower(): attribute})
