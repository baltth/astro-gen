#!/usr/bin/env python3

from . import common
from . import project

from pathlib import Path
import re
from typing import List, Set, Tuple


LINK_PATTERN = re.compile(r'!?\[(?P<text>[^\]]*)\]\((?P<url>[^)\s]+)(?:\s+"[^"]*")?\)')


def links_of(content: str) -> List[Tuple[int, str, str]]:

    res = []
    for i, l in enumerate(content.splitlines(), start=1):
        res += [(i, m.group('text'), m.group('url')) for m in LINK_PATTERN.finditer(l)]
    return res


def is_external(url: str) -> bool:
    return url.startswith(('http://', 'https://', 'mailto:'))


def anchors_of(content: str) -> Set[str]:
    return {common.md_anchor(line.lstrip('#').strip())
            for line in content.splitlines() if line.startswith('#')}


def check_links(root: str, file: str) -> List[Tuple[str, str, str]]:

    root_dir = Path(root).resolve()
    site_dir = Path(project.site_root(root))
    page_path = (root_dir / file).resolve()

    broken = []

    def add_broken(line: int, name: str, link: str):
        broken.append((f'{page_path.relative_to(root_dir)}:{line}', name, link))

    content = page_path.read_text(encoding='utf8')
    links = links_of(content)
    for line, name, link in links:
        if is_external(link):
            continue

        target, _, anchor = link.partition('#')
        if not target:
            if f'#{anchor}' not in anchors_of(content):
                add_broken(line, name, link)
            continue

        resolved = (page_path.parent / target).resolve()
        if not resolved.is_file() or not resolved.is_relative_to(site_dir):
            add_broken(line, name, link)

    return broken


def check(root: str) -> bool:

    all_ok: bool = True
    root_dir = Path(project.site_root(root))

    files = [f for f in root_dir.rglob(pattern="*.md") if '_site' not in str(f)]
    for f in files:
        broken = check_links(root, str(f))
        for loc, name, link in broken:
            print(f"In file {loc}: invalid link '{name}' to '{link}'")
            all_ok = False

    return all_ok
