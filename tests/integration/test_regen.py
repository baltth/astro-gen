#!/usr/bin/env python3

"""
Integration test of the 'regen' command.

The committed content of ./example is copied to a temp dir, the command
is executed on it and the generated markdown files are validated.
The content itself is checked by the unit tests, here we're verifying
that all expected pages are generated with a title and valid links.
"""

from astro_gen import main, project, check

from pathlib import Path
import pytest
import re
from shutil import copytree
from typing import Dict, List, Set, Tuple


EXAMPLE_DIR = Path(__file__).resolve().parents[2] / 'example'

# Content of ./example which is not an input of 'regen':
# huge originals and the local jekyll build artifacts.
NOT_COPIED = {'orig', '_site', '_layout', '.jekyll-cache', '__pycache__',
              'Gemfile', 'Gemfile.lock'}

# Generated content of ./example/docs - it's git-ignored but may be
# present in a working tree, drop it to generate from scratch.
GENERATED_DOC_ENTRIES = {'obs', 'pages', 'index.md'}

# The pages expected for the observations of ./example/db/obs.yml.
# Note the observation _day_ in the names: an observation after midnight
# belongs to the previous day, see common.obs_day().
EXPECTED_OBS_PAGES = {
    '2025/alpha-umi-2025-07-15.md',      # 2025-07-16 00:15
    '2026/alpha-umi-2026-08-01.md',      # 2026-08-02 00:15
    '2026/archimedes-2026-08-09.md',     # 2026-08-10 00:15
    '2026/c-2025-r3-2026-07-31.md',      # 2026-08-01 00:00
    '2025/c47-2025-07-15.md',            # 2025-07-15 23:30
    '2026/gassendi-2026-08-09.md',       # 2026-08-09 22:50
    '2026/m31-2026-08-15.md',            # 2026-08-16 01:00
    '2026/saturn-2026-08-15.md',         # 2026-08-16 01:00
}

EXPECTED_PAGES = {'log.md', 'obj_index.md'}

MAIN_PAGE = 'index.md'

EXPECTED_FILES = {MAIN_PAGE} \
    | {f'pages/{p}' for p in EXPECTED_PAGES} \
    | {f'obs/{p}' for p in EXPECTED_OBS_PAGES}


# Fixtures


def _copy_filter(directory: str, names: List[str]) -> Set[str]:

    ignored = {n for n in names if n in NOT_COPIED}
    if Path(directory).name == 'docs':
        ignored |= {n for n in names if n in GENERATED_DOC_ENTRIES}
    return ignored


@pytest.fixture(scope='module')
def generated_project(tmp_path_factory) -> Path:
    """The example project copied to a temp dir with 'regen' executed on it."""

    root = tmp_path_factory.mktemp('project') / 'example'
    copytree(EXAMPLE_DIR, root, ignore=_copy_filter)

    docs = Path(project.site_root(str(root)))
    assert not list(docs.rglob('*.md')), 'the input must contain no generated pages'

    args = main.arg_parser().parse_args([str(root), 'regen', '--skip-checks'])
    args.func(args)

    return root


@pytest.fixture(scope='module')
def docs_root(generated_project: Path) -> Path:
    return Path(project.site_root(str(generated_project)))


@pytest.fixture(scope='module')
def pages(docs_root: Path) -> Dict[str, str]:
    """All generated pages as {path relative to docs root: content}."""

    return {str(f.relative_to(docs_root)): f.read_text(encoding='utf8')
            for f in docs_root.rglob('*.md')}


# Helpers


LINK_PATTERN = re.compile(r'!?\[(?P<text>[^\]]*)\]\((?P<url>[^)\s]+)(?:\s+"[^"]*")?\)')


def links_of(content: str) -> List[Tuple[str, str]]:
    """All markdown links and images of a page as (text, url) pairs."""

    return [(m.group('text'), m.group('url')) for m in LINK_PATTERN.finditer(content)]


# Tests


def test_expected_files_are_generated(pages: Dict[str, str]):

    assert set(pages.keys()) == EXPECTED_FILES


def test_pages_have_a_title(pages: Dict[str, str]):

    for page, content in pages.items():
        if page == MAIN_PAGE:
            # the main page opens with the content of static/main_pre.md
            continue

        title = content.splitlines()[0]
        assert title.startswith('# ') and title[2:].strip(), f'{page}: {title}'


def test_pages_have_links(pages: Dict[str, str]):

    # guards the link check below against silently checking nothing
    for page, content in pages.items():
        assert links_of(content), f'{page} has no links at all'


def test_all_links_resolve(generated_project: Path):

    assert check.check(str(generated_project))
