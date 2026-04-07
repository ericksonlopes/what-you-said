# ruff: noqa: E402
"""
Import all modules under the `src` package by package name to ensure coverage can
see files that aren't otherwise executed by unit tests. This test will fail if
any module fails to import so import problems are visible in CI.
"""

import importlib
import os
import traceback

import src


def test_import_all_modules():
    root = os.path.dirname(src.__file__)
    failed = []

    for dirpath, dir_names, filenames in os.walk(root):
        for f_name in filenames:
            if not f_name.endswith(".py"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, f_name), root)
            module_name = "src." + os.path.splitext(rel)[0].replace(os.sep, ".")
            try:
                importlib.import_module(module_name)
            except Exception:
                failed.append((module_name, traceback.format_exc()))

    assert not failed, f"Modules failed to import during coverage collection: {failed}"
