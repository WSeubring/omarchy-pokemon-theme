"""Render a TOML section the way the generated overrides want it.

Both `shell.background.toml` and `shell.lock.toml` are a `[section]` line, an
optional provenance header and a block of key = value rows padded to a common
width. The padding is cosmetic but the header placement is not: the splice in
`omarchy-theme-set-templates` re-emits the section line above whatever follows,
so the header has to sit under it.
"""


def section(name, rows, header=""):
    """rows: sequence of (key, already-rendered value)."""
    width = max(len(key) for key, _ in rows)
    lines = ["[%s]" % name]
    if header:
        lines.append(header.rstrip("\n"))
    for key, value in rows:
        lines.append("%-*s = %s" % (width, key, value))
    return "\n".join(lines) + "\n"


def quote(value):
    """A bare TOML string. Values here are hex colours, effect names and slugs."""
    return '"%s"' % value
