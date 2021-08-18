#!/usr/bin/env python3
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: WTFPL
# SPDX-FileCopyrightText: 2021 Anna <cyber@sysrq.in>
# No warranty.

import os
import random
import sys
import urllib.parse

from collections import OrderedDict
from datetime import date
from fnmatch import fnmatch
from functools import cached_property
from pathlib import Path
from typing import NoReturn


def notfound() -> NoReturn:
    print("51 Not found!\r")
    sys.exit(0)


def cgi_error(msg=None) -> NoReturn:
    print("42 {0}\r".format(msg or "CGI Error"))
    sys.exit(0)


def failure(msg=None) -> NoReturn:
    print("40 {0}\r".format(msg or "Temporary failure!"))
    sys.exit(0)


def is_enabled(directory: Path) -> bool:
    registry = directory.parent / "registry"
    for line in registry.open():
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        if directory.name == line.split()[-1]:
            return True

    return False


def display_server_page(directory: Path) -> None:
    if not is_enabled(directory):
        failure("Untrusted server info")

    print("20 text/gemini\r")
    print("# Gemini Server of the Day is ...")

    print("##", directory.name)

    print("--", end="\n\n")
    print("=> random 🔀 Random server")
    print("=> info/README.gmi ℹ️ About this thing")


class CGIHandler:
    """ Syntax sugar """
    def __init__(self):
        self.routes = OrderedDict()

    @cached_property
    def path(self) -> str:
        path_info = os.getenv("PATH_INFO", default="/")
        return urllib.parse.unquote(path_info) or "/"

    @cached_property
    def dataroot(self) -> Path:
        dataroot_env = os.getenv("SOTD_DATAROOT")
        if dataroot_env:
            dataroot = Path(dataroot).expanduser()
        else:
            dataroot = Path.cwd().parent / "info"

        if not dataroot.is_dir():
            cgi_error("Invalid SOTD_DATAROOT")

        return dataroot

    def route(self, glob: str):
        def decorator(f):
            self.routes[glob] = f
            return f

        return decorator

    def exec(self) -> None:
        for glob, view_function in self.routes.items():
            if fnmatch(self.path, glob):
                return view_function()

        notfound()


app = CGIHandler()

@app.route("/random")
def sotd_random() -> None:
    """ Page that changes on every requst """
    directory = random.choice(filter(lambda x: x.is_dir(),
                                     app.dataroot.iterdir()))
    display_server_page(directory)

if __name__ == "__main__":
    app.exec()
