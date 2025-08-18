#!/usr/bin/env python3

import common

from typing import Dict, List, Union


def emph(s: str) -> str:
    return f'_{s}_'


def short_desc(obj_data: Dict) -> str:
    return f'{obj_data['type']} in '


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


def tag_line(name: str,
             object_data: Dict) -> str:

    def name_tags(n: str) -> List[str]:
        tags: List[str] = []
        greek = common.greek_name(n)
        if greek != n:
            tags.append(greek)
        pretty = common.pretty_name(n)
        if pretty != n:
            tags.append(pretty)
        return tags

    tags = [emph(t) for t in name_tags(name)]

    alias = object_data.get('aka', [])
    tags += [emph(a) for a in alias]

    sd = common.short_desc(object_data)
    if sd:
        if not tags:        # At least a name should be present before the desc
            tags += [emph(name)]

        sd = emph(sd[0].upper() + sd[1:])
        tags.append(sd)

    return ' | '.join(tags)


def subtitle(title: str) -> str:

    return f'## {title}'


def header(title: str) -> List[str]:

    links = common.md_link('Main page', '../pages/index.md') + ' | ' + common.md_link('Index', '../pages/obj_index.md')

    return [
        f'# {title}',
        '',
        links,
        ''
    ]


def footer(notes: str = '', links: Dict[str, str] = {}) -> List[str]:

    md: List[str] = []

    if notes:
        md += [f'> {n}' for n in notes.splitlines()] + ['']

    if links:
        md += [subtitle('Links'), ''] + [f'- {common.md_link(k, v)}' for k, v in links.items()]

    return md


def join(content: List[str]) -> str:

    return '\n'.join(content) + '\n'


def page(title: str,
         content: List[str],
         notes: str = '',
         links: Dict[str, str] = {}) -> str:

    md = header(title)
    md += content
    md += footer(notes=notes, links=links)

    return join(md)


def obs_body(title: str,
             names: List[str],
             img: str,
             table: List[str],
             text: str,
             object_data: Dict) -> List[str]:

    md = [tag_line(n, object_data.get(n, {})) + '  ' for n in names]
    md += [
        '',
        common.md_image(title, f'{img}'),
        ''
    ]
    md += table

    if text:
        md += text.splitlines()

    return md + ['']


def log_row(names: Union[str, List[str]], date: str) -> List[str]:

    pretty_name = common.pretty_name_str(names)
    date_prefix = date + ':'
    url = common.obs_page_url(names, date)
    return [date_prefix, pretty_name, url, '']


def index_row(obj_name: str,
              all_names: Union[str, List[str]],
              date: str,
              obj_data: Dict) -> List[str]:

    pretty_name: str = common.pretty_name(obj_name)
    url = common.obs_page_url(all_names, date)
    desc = common.short_desc(obj_data)
    return ['', pretty_name, url, f'- {desc}']


def index_data(data: Union[List, Dict]) -> List[str]:

    def list_line(d: List) -> str:
        assert d
        assert isinstance(d[0], str)
        if len(d) > 1:
            assert len(d) == 4
            link_text = d[1]
            url = d[2]
            l = [d[0], common.md_link(link_text, url), d[3]]
            text = ' '.join([t for t in l if t])
        else:
            text = d[0]
        return f'- {text}'

    if isinstance(data, list):
        assert isinstance(data[0], list)
        return [list_line(d) for d in data]

    assert isinstance(data, dict)
    md: List[str] = []
    for k, v in data.items():
        assert isinstance(k, str)
        md += [f'#### {k}', ''] + index_data(v) + ['']

    return md


def observation_page(names: Union[str, List[str]],
                     img: str,
                     date: str,
                     nelm: int,
                     ap: int,
                     mag: int,
                     fov: float,
                     text: str,
                     notes: str = '',
                     loc: str = '',
                     links: Dict[str, str] = {},
                     object_data: Dict = {}) -> str:

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

    md = obs_body(title=title,
                  names=names,
                  img=img,
                  table=o_table,
                  text=text,
                  object_data=object_data)
    return page(title=title,
                content=md,
                notes=notes,
                links=links)


def index_page(title: str,
               data: Union[List, Dict],
               notes: str = '',
               links: Dict[str, str] = {}) -> str:

    return page(title=title,
                content=index_data(data),
                notes=notes,
                links=links)
