#!/usr/bin/env python3

import subprocess

APP_NAME = 'astro-gen'


def git_describe_version() -> str:

    COMMAND = ['git', 'describe', '--tags', '--dirty']
    try:
        with subprocess.Popen(COMMAND, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
            assert p.stderr is not None
            assert p.stdout is not None

            p.stderr.close()
            line = p.stdout.readlines()[0].strip().decode()

            # as git describe results are not valid versions according to
            # https://peps.python.org/pep-0440, the extra content after the last tag
            # is converted to a local version identifier using '+':
            # before: 0.1-15-g2d90652-dirty
            # after:  0.1+15-g2d90652-dirty
            return line.replace('-', '+', 1)

    except Exception:

        return "0.0"
