#!/usr/bin/env python3

from . import common

from pathlib import Path
from typing import List, Union


# Project layout, paths

def site_root(project_root: str) -> str:
    p = Path(project_root) / 'docs'
    return str(p.resolve())


def site_images(project_root: str) -> str:
    p = Path(site_root(project_root)) / 'img'
    return str(p.resolve())


def sketch_db(root: str) -> str:
    p = Path(root) / 'db' / 'sketch.yml'
    return str(p.resolve())


def obs_db(root: str) -> str:
    p = Path(root) / 'db' / 'obs.yml'
    return str(p.resolve())


def object_db(root: str) -> str:
    p = Path(root) / 'db' / 'objects.yml'
    return str(p.resolve())


def main_pre_file(root: str) -> str:
    p = Path(root) / 'static' / 'main_pre.md'
    return str(p.resolve())


def main_post_file(root: str) -> str:
    p = Path(root) / 'static' / 'main_post.md'
    return str(p.resolve())


def meta_file(root: str) -> str:
    p = Path(root) / 'static' / 'meta.yaml'
    return str(p.resolve())


# Url for generated links in observation pages


def image_url(file: str) -> str:
    return f'../../img/{file}'


def scan_url(file: str) -> str:
    return f'../../scan/{file}'


def obs_page_url(obj: Union[str, List[str]],
                 date: str,
                 from_doc_level: int) -> str:
    assert from_doc_level >= 0 and from_doc_level <= 2

    url = _obs_url(f'{common.obs_year(date)}/{common.obs_page_name(obj, date)}')

    return url.removeprefix('../'*(2 - from_doc_level))


def _obs_url(file: str) -> str:
    return f'../../obs/{file}'
