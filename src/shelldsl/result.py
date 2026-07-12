"""Explicit process results and text-to-structure conversions."""

import csv
import io
import json
from .errors import CommandError


class Result:
    """The completed result of one command or pipeline."""

    def __init__(self, argv, stdout, stderr, code):
        self.argv = tuple(argv)
        self.stdout = stdout
        self.stderr = stderr
        self.code = code
        self.ok = self.code == 0
        self.text = self.stdout
        self.lines = self.stdout.splitlines()

    def raise_for_status(self):
        if not self.ok:
            raise CommandError(
                "command failed with exit code %s" % self.code,
                self.argv,
            )
        return self

    def json(self):
        return json.loads(self.stdout)

    def csv(self, header=0):
        rows = list(csv.reader(io.StringIO(self.stdout)))
        if not header:
            return rows
        if not rows:
            return []
        result = []
        for row in rows[1:]:
            result.append(dict(zip(rows[0], row)))
        return result

    def tsv(self, columns=None):
        rows = list(csv.reader(io.StringIO(self.stdout), delimiter="\t"))
        if columns is None:
            return rows
        result = []
        for row in rows:
            result.append(dict(zip(columns, row)))
        return result

    def kv(self, sep="="):
        values = {}
        for line in self.lines:
            if sep in line:
                key, value = line.split(sep, 1)
                values[key] = value
        return values
