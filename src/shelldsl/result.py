"""Explicit process results and text-to-structure conversions."""

import csv
import io
import json


class Result(object):
    """The completed result of one command or pipeline."""

    def __init__(self, argv, stdout, stderr, code):
        self.argv = tuple(argv)
        self.stdout = stdout
        self.stderr = stderr
        self.code = code

    @property
    def ok(self):
        return self.code == 0

    @property
    def text(self):
        return self.stdout

    @property
    def lines(self):
        return self.stdout.splitlines()

    def raise_for_status(self):
        if not self.ok:
            from .errors import CommandError
            raise CommandError(
                "command failed with exit code %s" % self.code,
                self.argv,
            )
        return self

    def json(self):
        return json.loads(self.stdout)

    def csv(self, header=False):
        rows = list(csv.reader(io.StringIO(self.stdout)))
        if not header:
            return rows
        if not rows:
            return []
        return [dict(zip(rows[0], row)) for row in rows[1:]]

    def tsv(self, columns=None):
        rows = list(csv.reader(io.StringIO(self.stdout), delimiter="\t"))
        if columns is None:
            return rows
        return [dict(zip(columns, row)) for row in rows]

    def kv(self, sep="="):
        values = {}
        for line in self.lines:
            if sep in line:
                key, value = line.split(sep, 1)
                values[key] = value
        return values
