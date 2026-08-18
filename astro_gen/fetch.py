#!/usr/bin/env python3

from .datatypes import ObjectData

import base64
from os import environ
import requests
from typing import Dict, List, Optional, Tuple


def astronomyapi_access() -> Tuple[str, str]:

    return (environ.get('ASTRONOMYAPI_ID', ''),
            environ.get('ASTRONOMYAPI_SECRET', ''))


def _astronomyapi_get(ep: str,
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
                        headers=headers,
                        timeout=10)

    resp.raise_for_status()
    return resp.json()['data']


def _astronomyapi_search(name: str,
                         app_id: str,
                         app_secret: str) -> Optional[Dict]:

    data = _astronomyapi_get(ep='search',
                             params={
                                'term': name,
                                'match_type': 'exact'
                             },
                             app_id=app_id,
                             app_secret=app_secret)
    if data:
        return data[0]
    return None


def _map_data(data: Dict) -> ObjectData:

    pos = data['position']['equatorial']
    res = ObjectData(name=data['name'],
                     ra=pos['rightAscension']['string'],
                     dec=pos['declination']['string'],
                     constellation=data['position']['constellation']['short'],
                     type=data['type']['name'])

    subtype = data.get('subType') or {}
    res.subtype = subtype.get('name') or ''
    if res.type.lower().endswith('star'):
        res.spectral_class = subtype.get('id') or ''

    all_names = [d['name'] for d in data['crossIdentification']]
    res.aka = [n for n in all_names if n != res.name]

    return res


def fetch(name: str,
          app_id: str,
          app_secret: str) -> Optional[ObjectData]:

    assert app_id
    assert app_secret

    try:
        data = _astronomyapi_search(name, app_id=app_id, app_secret=app_secret)
    except Exception:
        print(f'Unable to fetch data for {name}')
        return None

    if data:
        return _map_data(data)

    return None
