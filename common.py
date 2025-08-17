#!/usr/bin/env python3

import constellations

import unicodedata
from pathlib import Path
from slugify import slugify
from typing import List, Dict, Union


PROJECT_ROOT = Path(__file__).parent.parent.resolve()


def to_greek(val: str) -> str:

    try:
        key = f'GREEK SMALL LETTER {val.upper()}'
        return unicodedata.lookup(key)
    except Exception:
        return val


def greek_name(name: Union[str, List[str]]) -> Union[str, List[str]]:

    if isinstance(name, list):
        return [greek_name(n) for n in name]

    split_name = name.split()
    if len(split_name) != 2:
        return name
    maybe_greek = to_greek(split_name[0])
    name_end = ' '.join(split_name[1:])
    return f'{maybe_greek} {name_end}'


def pretty_name(name: Union[str, List[str]]) -> Union[str, List[str]]:

    if isinstance(name, list):
        return [pretty_name(n) for n in name]

    split_name = name.split()
    if constellations.is_constellation(split_name[-1]):
        name_start = ' '.join(split_name[0:-1])
        return f'{name_start} {constellations.genitive(split_name[-1])}'
    return name


def pretty_name_str(name: Union[str, List[str]]) -> str:

    pn = pretty_name(name)
    if isinstance(pn, list):
        return ', '.join(pn)
    return pn


def short_desc(obj_data: Dict) -> str:
    if not obj_data:
        return ''
    return f'{obj_data['type']} in {constellations.name(obj_data['constellation'])}'


def md_link(text: str, url: str, desc: str = '') -> str:
    l = f'[{text}]({url}'
    if desc:
        l += f' "{desc}")'
    else:
        l += ')'
    return l


def md_image(text: str, url: str, desc: str = '') -> str:
    return f'!{md_link(text, url, desc)}'


def name_slug(obj: Union[str, List[str]]) -> str:
    if isinstance(obj, list):
        name = ','.join(obj)
    else:
        name = obj

    return slugify(name)


def file_basename(obj: Union[str, List[str]], date: str) -> str:
    return slugify(f'{name_slug(obj)}-{date}')


def sketch_name(obj: Union[str, List[str]], date: str) -> str:
    return f'{file_basename(obj, date)}.jpg'


def obs_page_name(obj: Union[str, List[str]], date: str) -> str:
    return f'{file_basename(obj, date)}.md'


def obs_page_url(obj: Union[str, List[str]], date: str) -> str:
    return f'../obs/{obs_page_name(obj, date)}'


def image_url(file: str) -> str:
    return f'../img/{file}'


def scan_url(file: str) -> str:
    return f'../scan/{file}'
