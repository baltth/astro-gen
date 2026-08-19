#!/usr/bin/env python3

from astro_gen import check

from pathlib import Path
from typing import List
import pytest


# links_of()

def test_links_of():

    assert check.links_of('see [text](page.md) here') == [(1, 'text', 'page.md')]


def test_links_of_line_numbers_are_one_based():

    content = '# Title\n\n[a](a.md)\n[b](b.md)\n'
    assert check.links_of(content) == [(3, 'a', 'a.md'), (4, 'b', 'b.md')]


def test_links_of_multiple_links_in_a_line():

    assert check.links_of('[a](a.md) and [b](b.md)') == \
        [(1, 'a', 'a.md'), (1, 'b', 'b.md')]


def test_links_of_images():

    assert check.links_of('![C47](../../img/c47.jpg)') == \
        [(1, 'C47', '../../img/c47.jpg')]


def test_links_of_link_with_title():

    assert check.links_of('[C47](c47.md "Globular cluster")') == \
        [(1, 'C47', 'c47.md')]


def test_links_of_empty_text():

    assert check.links_of('[](page.md)') == [(1, '', 'page.md')]


def test_links_of_no_links():

    assert check.links_of('# Title\n\nplain [text] and (parens)\n') == []


# is_external()

def test_is_external():

    assert check.is_external('http://example.com')
    assert check.is_external('https://example.com')
    assert check.is_external('mailto:jane@example.com')


def test_is_external_local_urls():

    assert not check.is_external('page.md')
    assert not check.is_external('../../img/c47.jpg')
    assert not check.is_external('#anchor')


# anchors_of()

def test_anchors_of():

    content = '# Title\n\ntext\n\n## Sub Section\n'
    assert check.anchors_of(content) == {'#title', '#sub-section'}


def test_anchors_of_no_headings():

    assert check.anchors_of('text\n not # a heading\n') == set()


# check_links()

@pytest.fixture
def root(tmp_path) -> Path:
    """A project root with an `outside.md` next to it and a `db` folder inside."""

    (tmp_path / 'outside.md').write_text('# Outside\n')
    root = tmp_path / 'project'
    (root / 'docs').mkdir(parents=True)
    (root / 'db').mkdir()
    (root / 'db' / 'objects.yml').write_text('C47:\n')
    return root


def page(root: Path, content: str, name: str = 'docs/index.md') -> str:
    """Create a page with `content`, return its path relative to `root`."""

    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return name


def broken_links_of(root: Path, file: str) -> List[str]:
    return [link for _, _, link in check.check_links(str(root), file)]


def test_check_links_valid_link(root: Path):

    page(root, '# C47\n', name='docs/obs/2026/c47.md')
    f = page(root, '[C47](obs/2026/c47.md)\n')

    assert check.check_links(str(root), f) == []


def test_check_links_relative_to_the_page(root: Path):

    page(root, '# Index\n')
    f = page(root, '[Index](../../index.md)\n', name='docs/obs/2026/c47.md')

    assert check.check_links(str(root), f) == []


def test_check_links_missing_target(root: Path):

    f = page(root, 'text [C47](obs/2026/c47.md) text\n')

    assert check.check_links(str(root), f) == \
        [('docs/index.md:1', 'C47', 'obs/2026/c47.md')]


def test_check_links_location_is_relative_to_root(root: Path):

    f = page(root, '# C47\n\n![C47](../../img/c47.jpg)\n', name='docs/obs/2026/c47.md')

    loc, _, _ = check.check_links(str(root), f)[0]
    assert loc == 'docs/obs/2026/c47.md:3'


def test_check_links_all_broken_links_are_reported(root: Path):

    f = page(root, '[a](a.md)\n[b](b.md)\n')

    assert broken_links_of(root, f) == ['a.md', 'b.md']


def test_check_links_external_links_are_skipped(root: Path):

    f = page(root, '[Wikipedia](https://en.wikipedia.org/wiki/NGC_6934)\n'
                   '[mail](mailto:jane@example.com)\n')

    assert check.check_links(str(root), f) == []


def test_check_links_anchor_of_the_page(root: Path):

    f = page(root, '# C47\n\n[to the top](#c47)\n')

    assert check.check_links(str(root), f) == []


def test_check_links_missing_anchor_of_the_page(root: Path):

    f = page(root, '# C47\n\n[to M3](#m3)\n')

    assert broken_links_of(root, f) == ['#m3']


def test_check_links_anchor_of_another_page_is_not_verified(root: Path):

    page(root, '# C47\n', name='docs/obs/2026/c47.md')
    f = page(root, '[C47](obs/2026/c47.md#no-such-anchor)\n')

    assert check.check_links(str(root), f) == []


def test_check_links_target_outside_the_project_is_broken(root: Path):

    # the file exists but is not part of the project
    assert (root.parent / 'outside.md').is_file()
    f = page(root, '[Outside](../../outside.md)\n')

    assert broken_links_of(root, f) == ['../../outside.md']


def test_check_links_target_outside_the_site_is_broken(root: Path):

    # the file is part of the project but not of the published site
    assert (root / 'db' / 'objects.yml').is_file()
    f = page(root, '[Objects](../db/objects.yml)\n')

    assert broken_links_of(root, f) == ['../db/objects.yml']


def test_check_links_directory_target_is_broken(root: Path):

    (root / 'docs' / 'obs').mkdir()
    f = page(root, '[Observations](obs)\n')

    assert broken_links_of(root, f) == ['obs']


def test_check_links_no_links(root: Path):

    assert check.check_links(str(root), page(root, '# Index\n')) == []


# check()

def test_check(root: Path, capsys):

    page(root, '# C47\n', name='docs/obs/2026/c47.md')
    page(root, '[C47](obs/2026/c47.md)\n')

    assert check.check(str(root))
    assert capsys.readouterr().out == ''


def test_check_broken_link_is_reported(root: Path, capsys):

    page(root, '# Index\n\n[C47](obs/2026/c47.md)\n')

    assert not check.check(str(root))
    assert capsys.readouterr().out == \
        "In file docs/index.md:3: invalid link 'C47' to 'obs/2026/c47.md'\n"


def test_check_all_pages_are_scanned(root: Path, capsys):

    page(root, '[a](a.md)\n')
    page(root, '[b](b.md)\n', name='docs/obs/2026/c47.md')

    assert not check.check(str(root))
    out = capsys.readouterr().out.splitlines()
    assert len(out) == 2
    assert any('docs/obs/2026/c47.md' in l for l in out)


def test_check_generated_site_is_ignored(root: Path, capsys):

    page(root, '[a](a.md)\n', name='docs/_site/index.md')

    assert check.check(str(root))
    assert capsys.readouterr().out == ''


def test_check_non_markdown_files_are_ignored(root: Path):

    (root / 'docs' / 'index.html').write_text('<a href="missing.html">x</a>\n')

    assert check.check(str(root))


def test_check_no_pages(root: Path):

    assert check.check(str(root))
