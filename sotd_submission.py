#!/usr/bin/env python3
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: WTFPL
# SPDX-FileCopyrightText: 2021 Anna <cyber@sysrq.in>
# No warranty.

import email
import email.parser
import email.policy
import os
import sqlite3
import sys
import time
import urllib.parse

from dataclasses import dataclass, field
from email.errors import MessageError
from email.headerregistry import UniqueSingleAddressHeader
from email.message import EmailMessage
from fnmatch import fnmatch
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

    def __init__(self, msg_: EmailMessage, dataroot_: Path, logger_: GmiLogger):
        """
        auth() method has to be called after creating an instance

        :raises BadInput: on failed 'Subject' checks
        """

        self.commands: dict = {}
        self.logger: GmiLogger = logger_
        self.dataroot: Path = dataroot_
        self.msg: EmailMessage = msg_

        if not self.msg["Subject"]:
            raise BadInput("Error: empty subject")

        self.name: str
        self.cmd: str
        try:
            self.name, self.cmd = map(str.strip, self.msg["Subject"].split("/"))
        except ValueError as err:
            raise BadInput("Error: invalid action: '{msg[Subject]}'"
                           .format(msg=self.msg)) from err

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

    @cached_property
    def addr_from(self) -> str:
        """ Email address parsed from the 'From:' header """
        try:
            dest = dict(defects=[])
            UniqueSingleAddressHeader.parse(self.msg["From"], dest)

            return dest["groups"][0].addresses[0].addr_spec
        except (LookupError, AttributeError) as err:
            raise BadInput("Error: invalid email address") from err

    @cached_property
    def editable_names(self) -> list[str]:
        """ List of names, for which email address matches with glob from the registry """
        return [entry.name for entry in self.registry
                if entry.enabled and fnmatch(self.addr_from, entry.email_glob)]

    @cached_property
    def msg_contents(self) -> list[str]:
        """ Message contents, split by newlines """
        for part in self.msg.walk():
            if part.get_content_type() not in ("text/plain", "text/gemini"):
                continue
            return list(filter(None, part.get_content().rstrip().split("\n")))

        raise BadInput("Error: only text/plain and text/gemini MIME types "
                       "are supported")

    @cached_property
    def is_new(self) -> bool:
        """ True when there're no matching entries in the database """
        cursor.execute("SELECT * FROM servers WHERE name=?", (bot.name,))
        if cursor.fetchone() is None:
            return True
        return False

    def auth(self) -> None:
        if "DKIM-Signature" not in self.msg:
            raise AuthorizationFailed("Update rejected: missing DKIM signature")
        if "X-Spam" in self.msg:
            raise AuthorizationFailed("Update rejected: marked as spam")

        if not self.is_new and self.name not in self.editable_names:
            raise AuthorizationFailed("Update rejected: email address mismatch")

    def command(self, cmd: str):
        """ Register a function as the handler for cmd """
        def decorator(f: Callable):
            self.commands[cmd] = f
            return f

        return decorator

    def process(self) -> None:
        """ Find matching handler, run it and and write database """
        self.logger.print(f"=> ../{self.name}")

        try:
            function = self.commands[self.cmd]
        except LookupError as err:
            raise BadInput(f"Error: unknown action: '{self.cmd}'") from err

        reg_entry = RegistryEntry(self.addr_from, self.name)
        if reg_entry not in self.registry:
            self.logger.print("> Notice: your submission won't be displayed "
                              "until manual verification")
            with open(self.dataroot / "registry", "a") as file:
                print(reg_entry, file=file)

        if self.is_new:
            self.logger.print(f"* new server: {self.name}")
            cursor.execute("INSERT INTO servers(name) VALUES (?)", (bot.name,))

        function()

        connection.commit()
        connection.close()
        self.logger.finish("Success")


dataroot = Path(os.getenv("SOTD_DATAROOT", default="/var/gemini/sotd/info"))
if len(sys.argv) > 1:
    dataroot = Path(sys.argv[1])

logger = GmiLogger(dataroot / "log.gmi")

# enable strict policy so emails with e.g. invalid 'From:'
# headers are rejected
parser = email.parser.Parser(policy=email.policy.strict)
try:
    msg = parser.parse(sys.stdin if not debug else os.fdopen(3))
except MessageError:
    logger.finish("Error while parsing email message")
    sys.exit(0 if not debug else 1)

try:
    bot = BotHandler(msg, dataroot, logger)
except BadInput as error:
    logger.finish(*error.args)
    sys.exit(0 if not debug else 1)

@bot.command("screen_name")
def cmd_oneline(validate: Optional[Callable] = None) -> None:
    if not bot.msg_contents:
        logger.print(f"* delete {bot.cmd}")
        cursor.execute(f"UPDATE servers SET {bot.cmd}=NULL "
                        "WHERE name=?", (bot.name,))
        return

    text = bot.msg_contents[0].strip()  # first line
    logger.print(f"* set {bot.cmd} to {text}")
    if validate is not None:
        validate(text)
    cursor.execute(f"UPDATE servers SET '{bot.cmd}'=? "
                    "WHERE name=?", (text, bot.name))

def validate_url(url: str) -> urllib.parse.ParseResult:
    u = urllib.parse.urlsplit(url)
    if u.scheme and u.netloc:
        return u
    raise BadInput("Invalid URL:", url)

@bot.command("homepage")
def cmd_url() -> None:
    cmd_oneline(validate_url)

@bot.command("repology")
def cmd_repology() -> None:
    def validate_repology(url: str) -> None:
        u = validate_url(url)
        if u.netloc != "repology.org":
            raise BadInput("Invalid repology.org URL:", url)

    cmd_oneline(validate_repology)

if __name__ == "__main__":
    connection = sqlite3.connect(dataroot / "sotd.db")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    # FIXME: foreign key mismatch - "server_features" referencing "servers"
    # cursor.execute("PRAGMA foreign_keys = ON")

    try:
        bot.auth()
        bot.process()
    except (AuthorizationFailed, BadInput) as error:
        logger.finish(*error.args)
        sys.exit(0 if not debug else 1)
    # except sqlite3.Error as error:
        # logger.finish("SQL Error:", *error.args)
        # sys.exit(0 if not debug else 1)
    except (OSError, RuntimeError, SystemError):
        logger.finish("Internal server error")
        sys.exit(0 if not debug else 1)
