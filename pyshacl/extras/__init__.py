# -*- coding: utf-8 -*-
#
from functools import lru_cache
import sys
from warnings import warn

if sys.version_info[:2] < (3, 12):
    from importlib_metadata import PackageNotFoundError, metadata
else:
    from importlib.metadata import PackageNotFoundError, metadata


# In dev mode, the extras-loader doesn't check if extension is installed before loading it.
# This is useful when testing, when we're working on a codebase of a library that is not yet installed.
dev_mode = False


extras_requirements = {"js": ["pyduktape2"], "http": ["sanic", "sanic-ext", "sanic-cors"]}


@lru_cache()
def check_extra_installed(extra_name: str):
    if dev_mode:
        return True
    # first check if pyshacl is installed using the normal means
    try:
        this_mdata = metadata('pyshacl')
    except PackageNotFoundError:
        # Hmm, it thinks pyshacl isn't installed. Can't even check for extras
        return None
    try:
        has_extras = this_mdata.json['provides_extra']
    except LookupError:
        # Can't check metadata for extras for some reason?
        return None
    if extra_name not in has_extras:
        warn(Warning(f"Extra \"{extra_name}\" doesn't exist in this version of pyshacl."))
        return False
    if extra_name not in extras_requirements:
        warn(Warning(f"Extra \"{extra_name}\" cannot be checked in this version of pyshacl."))
    all_reqs = extras_requirements[extra_name]
    for req in all_reqs:
        try:
            _ = metadata(req)
        except PackageNotFoundError:
            warn(Warning(f"Extra \"{extra_name}\" is not satisfied because requirement {req} is not installed."))
            return False
    return True
