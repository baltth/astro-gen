#!/usr/bin/env python3

import common

from typing import Dict, List, Union


def obs_table(names: List[str],
              date: str,
              loc: str,
              nelm: int,
              ap: int,
              mag: int,
              fov: float) -> List[str]:

    names_cell = ', '.join(common.pretty_name(names))

    md: List[str] = []

    if len(names) > 1:
        md += [f'Objects | {names_cell}']
    else:
        md += [f'Object | {names_cell}']

    md += [
        '-|-',
        f'Observed at | {loc}, {date}',
        f'NELM | ~ {nelm / 10.0}',
        f'Aperture | {ap} mm',
        f'Magnification | {mag}x',
        f'FOV | {fov} \u00b0',
        ''
    ]

    return md


def header(title: str,
           names: List[str]) -> List[str]:

    def name_tags(name: str) -> List[str]:
        tags: List[str] = []
        greek = common.greek_name(name)
        if greek != name:
            tags.append(greek)
        pretty = common.pretty_name(name)
        if pretty != name:
            tags.append(pretty)
        return tags

    md = [f'# {title}',
          '',
          common.md_link('Back to index', '../main.md'),
          '']

    for n in names:
        tags = [f'_{t}_' for t in name_tags(n)]
        if tags:
            md += [' | '.join(tags) + '  ']

    md += ['']

    return md


def body(title: str,
         img: str,
         table: List[str],
         text: str) -> str:

    md = [
        common.md_image(title, f'{img}'),
        ''
    ]
    md += table

    if text:
        md += text.splitlines()

    return md + ['']


def footer(notes: str = '', links: Dict[str, str] = {}) -> List[str]:

    md: List[str] = []

    if notes:
        md += [f'> {n}' for n in notes.splitlines()] + ['']

    if links:
        md += ['## Links', ''] + [f'- {common.md_link(k, v)}' for k, v in links.items()]

    return md


def observation(names: Union[str, List[str]],
                img: str,
                date: str,
                nelm: int,
                ap: int,
                mag: int,
                fov: float,
                text: str,
                notes: str = '',
                loc: str = '',
                links: Dict[str, str] = {}) -> str:

    if isinstance(names, str):
        names = [names]

    title = ', '.join(names)

    o_table = obs_table(
        names=names,
        date=date,
        loc=loc,
        nelm=nelm,
        ap=ap,
        mag=mag,
        fov=fov)

    md = header(title, names)
    md += body(title=title,
               img=img,
               table=o_table,
               text=text)
    md += footer(notes=notes, links=links)

    return '\n'.join(md) + '\n'
