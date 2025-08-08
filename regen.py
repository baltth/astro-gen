#!/usr/bin/env python3

import common
import pages

import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Union
import yaml


DEFAULT_LOCATION = 'Dunaharaszti, HU'


def sketch_of_obs(db: List, obs: Dict) -> Dict:

    res = [s for s in db if obs['img'] in s['sub']]

    assert len(res) == 1
    return res[0]


def get_links_notes(sketch_db: List, obs: Dict) -> Tuple[Dict, str]:

    sketch = sketch_of_obs(sketch_db, obs)
    links = {
        'Full sketch': f'../img/{sketch['full']}'
    }

    notes = sketch.get('notes', '')

    scan = sketch.get('scan', '')
    if scan:
        links['Original sketch'] = f'../scan/{scan}'

    return (links, notes)


def generate_obs(obs: Dict, sketch_db: List):

    img = f'../img/{obs['img']}'

    links, notes = get_links_notes(sketch_db=sketch_db, obs=obs)

    content = pages.observation(names=obs['name'],
                                img=img,
                                date=obs['date'],
                                nelm=obs['nelm'],
                                ap=obs['ap'],
                                mag=obs['mag'],
                                fov=obs['fov'],
                                loc=obs.get('loc', DEFAULT_LOCATION),
                                text=obs.get('text', ''),
                                notes=notes,
                                links=links)

    out_path = common.PROJECT_ROOT / 'obs' / Path(common.obs_page_name(obs['name'], obs['date']))
    out_path.write_text(content, encoding='utf8')


def regen(obs_db: Dict, sketch_db: Dict):

    for obs in obs_db['observations']:
        generate_obs(obs=obs, sketch_db=sketch_db)


def load(db: str) -> Union[Dict, List]:

    with open(db) as f:
        data = yaml.safe_load(f)
        assert isinstance(data, dict) or isinstance(data, list)
        return data


def main():

    parser = argparse.ArgumentParser()
    parser.description = 'Regenerate pages'
    parser.add_argument('observation_db')
    parser.add_argument('sketch_db')
    parser.add_argument('-l', '--last', type=int, default=0)
    args = parser.parse_args()

    sketch_db = load(args.sketch_db)
    assert isinstance(sketch_db, list)

    obs_db = load(args.observation_db)
    assert isinstance(obs_db, dict)

    if args.last > 0:
        obs_db['observations'] = obs_db['observations'][-args.last:]

    regen(obs_db, sketch_db)


if __name__ == "__main__":
    main()
