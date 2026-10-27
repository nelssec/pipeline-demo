#!/usr/bin/env python3
"""Move a Dockerfile's PHP to the PHP2Shell-fixed release.

PHP2Shell (CVE-2026-109618, CVE-2026-109619) is fixed upstream in 8.5.12, 8.4.27, 8.3.36
and 8.2.35, and in Ubuntu 24.04 php8.3 8.3.6-0ubuntu0.24.04.13 (USN-8948-1). `qscanner
patch` only rewrites python, java and golang manifests, so the PHP bump is done here.

Two pins are recognised:
  FROM php:<x.y.z>[-variant]               official image tag
  ARG PHP_PKG_VERSION=<ubuntu version>     Ubuntu package build (php/Dockerfile)

Usage: bump-php-base.py [--check] DOCKERFILE

Prints key=value lines (current, fixed, changed) for $GITHUB_OUTPUT. With --check the
Dockerfile is not modified. Exits 2 when the PHP branch has no fixed release.
"""
import re
import sys

UPSTREAM_FIXED = {
    (8, 5): (8, 5, 12),
    (8, 4): (8, 4, 27),
    (8, 3): (8, 3, 36),
    (8, 2): (8, 2, 35),
}

# Ubuntu build prefix -> first fixed build number.
UBUNTU_FIXED = {
    "8.3.6-0ubuntu0.24.04.": 13,
}

FROM_RE = re.compile(r"^(\s*FROM\s+(?:docker\.io/)?(?:library/)?php:)(\d+)\.(\d+)\.(\d+)(-\S+)?(.*)$", re.IGNORECASE)
ARG_RE = re.compile(r"^(\s*ARG\s+PHP_PKG_VERSION=)(\S+?)(\d+)(\s*)$")


def bump_upstream(m):
    prefix, major, minor, patch, variant, rest = m.groups()
    version = (int(major), int(minor), int(patch))
    target = UPSTREAM_FIXED.get(version[:2])
    current = "%d.%d.%d" % version
    if target is None:
        return current, None, None
    fixed = "%d.%d.%d" % max(version, target)
    return current, fixed, "%s%s%s%s\n" % (prefix, fixed, variant or "", rest)


def bump_ubuntu(m):
    prefix, base, build, rest = m.groups()
    current = base + build
    first_fixed = UBUNTU_FIXED.get(base)
    if first_fixed is None:
        return current, None, None
    fixed = base + str(max(int(build), first_fixed))
    return current, fixed, "%s%s%s\n" % (prefix, fixed, rest)


def main(argv):
    check = "--check" in argv
    paths = [a for a in argv if not a.startswith("--")]
    if len(paths) != 1:
        print(__doc__, file=sys.stderr)
        return 64
    path = paths[0]
    with open(path) as f:
        lines = f.readlines()

    current = fixed = None
    for i, line in enumerate(lines):
        stripped = line.rstrip("\n")
        for regex, bump in ((FROM_RE, bump_upstream), (ARG_RE, bump_ubuntu)):
            m = regex.match(stripped)
            if not m:
                continue
            current, fixed, new_line = bump(m)
            if fixed is None:
                print("current=%s" % current)
                print("::error::PHP %s has no known PHP2Shell fix" % current, file=sys.stderr)
                return 2
            if fixed != current:
                lines[i] = new_line

    if current is None:
        print("::error::no php:<x.y.z> image or PHP_PKG_VERSION pin found in %s" % path, file=sys.stderr)
        return 1

    changed = current != fixed
    if changed and not check:
        with open(path, "w") as f:
            f.writelines(lines)
    print("current=%s" % current)
    print("fixed=%s" % fixed)
    print("changed=%s" % str(changed).lower())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
