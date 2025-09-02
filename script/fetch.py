#!/usr/bin/env python3

from db import add_objects
from datatypes import FetchedData

import argparse
import base64
from dataclasses import asdict
import json
from os import environ
import requests
from sys import stdout
from typing import Dict, List, Optional, Tuple

from ruamel.yaml import YAML


def astronomyapi_access() -> Tuple[str, str]:

    return (environ.get('ASTRONOMYAPI_ID', ''),
            environ.get('ASTRONOMYAPI_SECRET', ''))


def astronomyapi_get(ep: str,
                     params: Dict,
                     app_id: str,
                     app_secret: str) -> List[Dict]:

    URL = 'https://api.astronomyapi.com/api/v2'

    auth_data = f'{app_id}:{app_secret}'
    auth_encoded = base64.b64encode(auth_data.encode()).decode()

    headers = {
        'Authorization': f'Basic {auth_encoded}'
    }

    resp = requests.get(url=f'{URL}/{ep}',
                        params=params,
                        headers=headers)

    resp.raise_for_status()
    return resp.json()['data']


def astronomyapi_search(name: str,
                        app_id: str,
                        app_secret: str) -> Optional[Dict]:

    data = astronomyapi_get(ep='search',
                            params={
                                'term': name,
                                'match_type': 'exact'
                            },
                            app_id=app_id,
                            app_secret=app_secret)
    if data:
        return data[0]
    return None


def map_data(data: Dict) -> FetchedData:

    pos = data['position']['equatorial']
    res = FetchedData(name=data['name'],
                      ra=pos['rightAscension']['string'],
                      decl=pos['declination']['string'],
                      constellation=data['position']['constellation']['short'],
                      type=data['type']['name'])

    res.subtype = data['subType']['name']
    if res.type.lower().endswith('star'):
        res.spectral_class = data['subType']['id']

    all_names = [d['name'] for d in data['crossIdentification']]
    res.alias = [n for n in all_names if n != res.name]

    return res


def fetch(name: str,
          app_id: str,
          app_secret: str) -> Optional[FetchedData]:

    assert app_id
    assert app_secret

    try:
        data = astronomyapi_search(name, app_id=app_id, app_secret=app_secret)
    except Exception:
        print(f'Unable to fetch data for {name}')
        return None

    if data:
        return map_data(data)

    return None


def main():

    parser = argparse.ArgumentParser()
    parser.description = 'Fetch astronomyapi.com'

    parser.add_argument('object')
    parser.add_argument('-j', '--json', action='store_true')
    args = parser.parse_args()

    app_id, secret = astronomyapi_access()
    if not app_id:
        print('Please define ASTRONOMYAPI_ID and ASTRONOMYAPI_SECRET environment variables')
        return 1

    fetched = fetch(args.object, app_id=app_id, app_secret=secret)
    if not fetched:
        print(f'No object found: {args.object}')
        return 0

    d = asdict(fetched)
    if not d['spectral_class']:
        del d['spectral_class']

    if args.json:
        print(json.dumps(d, indent=2) + '\n')
    else:
        yaml = YAML(typ='safe')
        yaml.sort_base_mapping_type_on_output = False
        yaml.dump(d, stream=stdout)


if __name__ == "__main__":
    main()
