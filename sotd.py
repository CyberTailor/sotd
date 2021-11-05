#!/usr/bin/env python3
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: WTFPL
# SPDX-FileCopyrightText: 2021 Anna <cyber@sysrq.in>
# No warranty.

import mimetypes
import os
import random
import sqlite3
import sys
import urllib.parse

from collections import OrderedDict
from datetime import date
from fnmatch import fnmatch
from functools import cached_property
from pathlib import Path


class Redirect(Exception):
    def __init__(self, url: str):
        super().__init__()
        self.url: str = url


class Failure(RuntimeError):
    pass


class CGIError(RuntimeError):
    pass


class PermanentFailure(RuntimeError):
    pass


class NotFound(RuntimeError):
    pass


def enabled_servers() -> list[str]:
    names = []
    for line in Path(app.dataroot / "registry").open():
        parts = list(filter(None, line.split()))
        if len(parts) != 2 or parts[0].startswith("#"):
            continue
        if parts[1] not in names:
            names.append(parts[1])

    names.sort()
    return names


def display_server_page(data, lang, feature_desc) -> None:
    def display(field: str, format_str="{0}", fallback=None):
        val = data[field] or fallback
        if val is not None:
            print(format_str.format(val), end="\n\n")

    def display_lang():
        if lang is not None:
            print("> Written in", lang.strip(), end="\n\n")

    def display_features():
        if not feature_desc:
            return
        print("Features:")
        for feature in feature_desc:
            print("*", feature)
        print()

    print("20 text/gemini\r")
    print("# Gemini Server of the Day is ...")

    display("logo", format_str="```ASCII Art\n{0}\n```")
    display("screen_name", format_str="## {0}", fallback=data["name"])
    display_lang()
    display("description")
    display("homepage", format_str="🏠 Homepage:\n=> {0}")
    display_features()
    display("repology", format_str="=> {0} 📦 Repology: packaging status")

    print("--", end="\n\n")
    print(f"=> ./{data['name']} ⚓ Permanent link to this page")
    print("=> ./random 🔀 Random server")
    print("=> ./info/README.gmi ℹ️ About this thing")


class CGIHandler:
    """ Syntax sugar """
    def __init__(self):
        self.routes = OrderedDict()

    @cached_property
    def path(self) -> str:
        path_info = os.getenv("PATH_INFO", default="/")
        return urllib.parse.unquote(path_info) or "/"

    @cached_property
    def script_name(self) -> str:
        return os.getenv("SCRIPT_NAME", default="")

    @cached_property
    def dataroot(self) -> Path:
        dataroot_env = os.getenv("SOTD_DATAROOT")
        if dataroot_env:
            dataroot = Path(dataroot).expanduser()
        else:
            dataroot = Path.cwd().parent / "info"

        if not dataroot.is_dir():
            raise CGIError("Invalid SOTD_DATAROOT")

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

        raise NotFound("UFO landed and left these words here")


app = CGIHandler()

@app.route("/info/registry")
def sotd_registry() -> None:
    """ Should be kept private (contains email addresses) """
    raise PermanentFailure("Access denied")

@app.route("/info")
@app.route("/info/*")
def sotd_info() -> None:
    """ Serve info files """
    path = app.dataroot / Path(app.path).relative_to("/info")
    if not path.exists():
        raise NotFound("No such file or directory")
    if not path.is_relative_to(app.dataroot):
        raise PermanentFailure("Access denied")

    if path.is_file():
        mimetypes.add_type("text/gemini", ".gmi")
        mimetypes.add_type("text/gemini", ".gemini")
        mimetypes.add_type("application/x-sqlite3", ".db")
        mime = mimetypes.guess_type(path, strict=False)[0] or "text/plain"
        response = bytes(f"20 {mime}\r\n", encoding="utf-8")
        response += path.read_bytes()
        sys.stdout.buffer.write(response)
    elif path.is_dir():
        if not app.path.endswith("/"):
            raise Redirect(app.path + "/")

        print("20 text/gemini\r")
        print("# Index of", app.path, end="\n\n")
        print("=> ..")
        for item in path.iterdir():
            print("=>", item.name, end="/\n" if item.is_dir() else "\n")
    else:
        raise Failure("Cannot display this file")

@app.route("/")
def sotd() -> None:
    """ Page that changes once a day """
    # a bit of personalization C:
    favorite_number = float(os.getenv("FAVORITE_NUMBER", default="0"))
    random.seed(date.today().toordinal() + favorite_number)
    sotd_random()

@app.route("/random")
def sotd_random() -> None:
    """ Page that changes on every requst """
    sotd_server_page(is_random=True)

@app.route("/*")
def sotd_server_page(is_random: bool = False) -> None:
    """ Server info page """
    if len(Path(app.path).parts) > 2:
        raise NotFound("UFO landed and left these words here")

    if is_random:
        name = random.choice(enabled_servers())
    else:
        name = Path(app.path).parts[1]
        if name not in enabled_servers():
            raise NotFound("No appropriate server info found")

    con = sqlite3.connect(app.dataroot / "sotd.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    cur.execute("SELECT * FROM servers WHERE name=?", (name,))
    data = cur.fetchone()
    if data is None:
        raise NotFound("No server info found")

    lang_name = None
    if data["lang"] is not None:
        cur.execute("SELECT screen_name FROM languages "
                    "WHERE name=?", (data["lang"],))
        lang = cur.fetchone()
        if lang is not None:
            lang_name = lang["screen_name"] or data["lang"].capitalize()

    cur.execute("SELECT feature_name FROM server_features "
                "WHERE server_name=?", (data["name"],))
    features = [row["feature_name"] for row in cur]
    feature_desc = []
    for feat in features:
        cur.execute("SELECT description FROM features WHERE name=?", (feat,))
        desc = cur.fetchone()
        if desc is not None:
            feature_desc.append(desc["description"] or feat)

    con.close()

    display_server_page(data, lang_name, feature_desc or None)

if __name__ == "__main__":
    try:
        app.exec()
    except Redirect as redirect:
        print(31, redirect.url, end="\r\n")
    except Failure as err:
        print(40, *err.args, end="\r\n")
    except CGIError as err:
        print(42, *err.args, end="\r\n")
    except PermanentFailure as err:
        print(50, *err.args, end="\r\n")
    except NotFound as err:
        print(51, *err.args, "\r\n")
    except (OSError, RuntimeError, SystemError, sqlite3.Error) as err:
        raise CGIError("Internal server error") from err
