#!/usr/bin/env python3

import common
from datatypes import ObsData, Object, SketchData
import db
import index
import pages
import project

import argparse
from copy import copy
from natsort import natsorted
from pathlib import Path
from typing import Dict, List, Tuple, Union
import yaml


DEFAULT_LOCATION = 'Dunaharaszti, HU'

project_root: str = ''

def load_meta() -> Dict:
    with open(project.meta_file(project_root), encoding='utf8') as f:
        data = yaml.safe_load(f)
        assert isinstance(data, dict)
        return data


def write_file(cat: str, name: str, content: str):

    doc_root = Path(project.site_root(project_root))
    out_path = doc_root / cat / name
    out_path.write_text(content, encoding='utf8')


def sketch_of_obs(sketch_db: List[SketchData], obs: ObsData) -> SketchData:

    res = [s for s in sketch_db if obs.img in s.sub or obs.img == s.full]

    assert len(res) == 1
    return res[0]


def object_data(object_db: Dict[str, Object], names: List[str]) -> Dict[str, Object]:

    return {n: object_db[n] for n in names if n in object_db.keys()}


def all_observations_of(name: str, obs_db: List[ObsData]) -> List[ObsData]:

    return [obs for obs in obs_db if name in obs.names]


def get_prev_next_obs_index(ref: ObsData, obs_list: List[ObsData]) -> Tuple[int, int]:

    if len(obs_list) < 2:
        return (-1, -1)

    i = obs_list.index(ref)
    prev_i = i - 1 if i > 0 else -1
    next_i = i + 1 if i < len(obs_list) - 1 else -1
    return (prev_i, next_i)


def other_obs_link_data(obs: ObsData) -> Tuple[str, str, str]:
    date = common.obs_day(obs.date)
    return (common.pretty_name_str(obs.names), date, project.obs_page_url(obs.names, date))


def get_nav_links(obs: ObsData,
                  obs_db: List[ObsData]) -> Dict[str, str]:

    other_obs_before = []
    other_obs_after = []
    for n in obs.names:
        other_obs = all_observations_of(n, obs_db=obs_db)
        if other_obs:
            other_obs = natsorted(other_obs, key=lambda o: o.date)
            prev_i, next_i = get_prev_next_obs_index(obs, other_obs)
            if prev_i >= 0:
                other_obs_before.append(other_obs_link_data(other_obs[prev_i]))
            if next_i >= 0:
                other_obs_after.append(other_obs_link_data(other_obs[next_i]))

    def other_links(other: List[Tuple], prefix: str) -> Dict[str, str]:
        return {f'{prefix}: {o[0]} on {o[1]}': o[2] for o in other}

    links = {}
    if other_obs_before:
        links.update(other_links(other_obs_before, 'Previous'))

    if other_obs_after:
        links.update(other_links(other_obs_after, 'Next'))

    return links


def get_links_notes(obs: ObsData,
                    sketch_db: List[SketchData]) -> Tuple[Dict, str]:

    sketch = sketch_of_obs(sketch_db, obs)
    links = {
        'Full sketch': project.image_url(sketch.full)
    }

    if sketch.scan:
        links['Original sketch'] = project.scan_url(sketch.scan)

    return (links, sketch.notes)


def obs_page_name(obs: ObsData) -> str:
    return common.obs_page_name(obs.names, common.obs_day(obs.date))


def generate_obs(obs: ObsData,
                 obs_db: List[ObsData],
                 sketch_db: List[SketchData],
                 object_db: Dict[str, Object],
                 meta: Dict):

    img = project.image_url(obs.img)

    nav_links = get_nav_links(obs=obs, obs_db=obs_db)
    content_links, notes = get_links_notes(obs=obs, sketch_db=sketch_db)
    content_links.update(nav_links)

    data = copy(obs)
    data.loc = obs.loc if obs.loc else meta.get('default_location', 'somewhere...')

    content = pages.observation_page(obs_data=data,
                                     img=img,
                                     notes=notes,
                                     nav_links=nav_links,
                                     content_links=content_links,
                                     object_data=object_data(object_db, data.names))

    write_file('obs', obs_page_name(data), content)


def obs_log_data(obs_db: List[ObsData], from_main: bool) -> List:

    def row(date: str, names: List[str]) -> List[str]:
        obs_day = common.obs_day(date)
        return pages.log_row(names, obs_day, from_main)
    
    rev_sorted_data = sorted(((o.date, o.names) for o in obs_db), reverse=True)
    return [row(o[0], o[1]) for o in rev_sorted_data]


def generate_obs_log(obs_db: List[ObsData]):

    content = pages.index_page(title='All observations',
                               data=obs_log_data(obs_db, from_main=False))
    write_file('pages', 'log.md', content)


def generate_index(obs_db: List[ObsData], object_db: Dict[str, Object]):

    content = pages.page(title='Index',
                         content=index.index_content(obs_db=obs_db, object_db=object_db),
                         toc_level=2)
    write_file('pages', 'obj_index.md', content)


def load_md(file: str) -> List[str]:

    print(f'Loading {file} ...')

    try:
        text = Path(file).read_text(encoding='utf8')
        return text.splitlines()
    except Exception:
        print(f'Unable to read {file}, skipping content')
        return []


def generate_main(obs_db: List[ObsData]):

    latest_obs = obs_log_data(obs_db, from_main=True)[:10]

    main_pre = load_md(project.main_pre_file(project_root))
    main_post = load_md(project.main_post_file(project_root))

    content = main_pre + pages.SEPARATOR

    content += [
        pages.subtitle('Latest'),
        ''
    ] + pages.index_data(latest_obs) + pages.SEPARATOR

    content += [
        f'## {common.md_link('All observations', 'pages/log.md')}',
        '',
        f'## {common.md_link('Index', 'pages/obj_index.md')}',
        ''
    ] + pages.SEPARATOR

    content += main_post

    write_file('', 'index.md', pages.join(content))


def regen(obs_db: List[ObsData], sketch_db: List[SketchData], object_db: Dict[str, Object]):

    print('Generating ...')

    meta = load_meta()

    for obs in obs_db:
        generate_obs(obs=obs,
                     obs_db=obs_db,
                     sketch_db=sketch_db,
                     object_db=object_db,
                     meta=meta)

    generate_obs_log(obs_db)
    generate_index(obs_db=obs_db, object_db=object_db)
    generate_main(obs_db)


def load(db_file: str) -> Union[Dict, List]:

    print(f'Loading {db_file} ...')

    with open(db_file, encoding='utf8') as f:
        data = yaml.safe_load(f)
        assert isinstance(data, dict) or isinstance(data, list)
        return data


def main():

    parser = argparse.ArgumentParser()
    parser.description = 'Regenerate pages'
    parser.add_argument('project_root', help='Root folder of project to generate')
    args = parser.parse_args()

    print(f'Project path: {args.project_root}')

    sketches = db.sketches(args.project_root)
    observations = db.observations(args.project_root)
    objects = db.objects(args.project_root)

    global project_root
    project_root = args.project_root

    regen(obs_db=observations,
          sketch_db=sketches,
          object_db=objects)

    print('Done')


if __name__ == "__main__":
    main()
