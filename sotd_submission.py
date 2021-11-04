#!/usr/bin/env python3
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: WTFPL
# SPDX-FileCopyrightText: 2021 Anna <cyber@sysrq.in>
# No warranty.

import os
import sys
import time

from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Callable, Optional

# When set, 1) reads from file descriptor "3" instead of stdin to make debugging
# with pdb possible; 2) returns exit status 1 on errors.
debug: bool = os.getenv("SOTD_DEBUG") is not None


class AuthorizationFailed(RuntimeError):
    pass


class BadInput(RuntimeError):
    pass


@dataclass(frozen=True)
class RegistryEntry:
    email_glob: str
    name: str
    enabled: bool = field(compare=False, default=False)

    def __str__(self) -> str:
        pre = "" if self.enabled else "#"
        return f"{pre}{self.email_glob}\t{self.name}"


class GmiLogger:
    """ text/gemini public log writer """

    def __init__(self, path: Path):
        self.log: list[str] = ["### " + time.asctime(time.gmtime())]
        self.path: Path = path
        self.path.touch()

        self._finished: bool = False

    def print(self, *args: object) -> None:
        """ Log a text line """
        self.log.append(" ".join(map(str, args)))

    def finish(self, *log_msg: object) -> None:
        """
        Prepend new entry to the log file.
        Final log message will be displayed as a quote line.
        """
        if self._finished:
            raise RuntimeError("GmiLogger.finish() called twice")

        self.print(">", *log_msg, "\n")
        with open(self.path) as log_file:
            self.log.extend(list(map(str.strip, log_file.readlines())))
        with open(self.path, "w") as log_file:
            for line in self.log:
                print(line, file=log_file)

        self._finished = True


class BotHandler:
    """ Main application logic """

    def __init__(self, dataroot_: Path, logger_: GmiLogger):
        self.commands: dict = {}
        self.logger: GmiLogger = logger_
        self.dataroot: Path = dataroot_

    @cached_property
    def registry(self) -> list[RegistryEntry]:
        """ Email address globs and names from the registry file """
        reg = []
        for line in Path(self.dataroot / "registry").open():
            parts = line.split()
            if len(parts) == 3 and parts[0] == "#":  # contains false positives
                reg.append(RegistryEntry(parts[1], parts[2], enabled=False))
            elif len(parts) == 2:
                is_enabled = not parts[0].startswith("#")
                reg.append(RegistryEntry(parts[0], parts[1], enabled=is_enabled))

        return reg

    def command(self, cmd: str):
        """ Register a function as the handler for cmd """
        def decorator(f: Callable):
            self.commands[cmd] = f
            return f

        return decorator

    def process(self) -> None:
        """ Find matching handler, run it and and write database """
        try:
            function = self.commands[self.cmd]
        except LookupError as err:
            raise BadInput(f"Error: unknown action: '{self.cmd}'") from err

        function()

        self.logger.finish("Success")


dataroot = Path(os.getenv("SOTD_DATAROOT", default="/var/gemini/sotd/info"))
if len(sys.argv) > 1:
    dataroot = Path(sys.argv[1])

logger = GmiLogger(dataroot / "log.gmi")

try:
    bot = BotHandler(dataroot, logger)
except BadInput as error:
    logger.finish(*error.args)
    sys.exit(0 if not debug else 1)
