import os
import sys
import bpy
import importlib
from types import ModuleType

repo_folder = os.path.join(os.path.dirname(__file__), os.pardir)
tests_folder = os.path.join(repo_folder, 'tests')

def deep_reload(m: ModuleType):
    name = m.__name__  # get the name that is used in sys.modules
    name_ext = name + '.'  # support finding sub modules or packages

    def compare(loaded: str):
        return (loaded == name) or loaded.startswith(name_ext)

    all_mods = tuple(sys.modules)  # prevent changing iterable while iterating over it
    sub_mods = filter(compare, all_mods)
    for pkg in sorted(sub_mods, key=lambda item: item.count('.'), reverse=True):
        importlib.reload(sys.modules[pkg])  # reload packages, beginning with the most deeply nested


def reload_addon_source_code(addons, only_unregister=False):
    """"
    Does a full reload of the addons directly from their source code in the repo. This
    tends to be the preferred method of working since stack traces will link back to the
    source code.

    :param list addons: A list of addon names.
    :param bool only_unregister: Whether or not to only unregister the addon code.
    """
    # forces reloading of modules, regeneration of properties, and sends all errors
    # to stderr instead of a dialog
    for addon in addons:
        os.environ[f'{addon.upper()}_DEV'] = '1'
        addon = importlib.import_module(addon)

        addon.unregister()
        deep_reload(addon)

        if not only_unregister:
            addon.register()


def reload_addon_zips(addons):
    """
    Does a full install and reload of the addons from their zip files. This is useful when
    testing the full addon installation, and when you need to see the addon preferences UI which
    is only available when a addon is physically installed.

    :param list addons: A list of addon names.
    """
    sys.path.append(os.path.join(tests_folder, 'utils'))
    from addon_packager import AddonPackager # type: ignore

    # unregister any registered addons
    reload_addon_source_code(addons, only_unregister=True)

    # zip up each addon
    for addon in addons:
        os.environ[f'{addon.upper()}_DEV'] = '1'
        addon_folder_path = os.path.join(repo_folder, 'src', 'addons', addon)
        release_folder_path = os.path.join(repo_folder, 'release')
        addon_packager = AddonPackager(addon, addon_folder_path, release_folder_path)
        addon_packager.zip_addon()
        addon_packager.install_addon()

    bpy.ops.script.reload()
