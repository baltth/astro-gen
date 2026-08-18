#!/usr/bin/env python3

from astro_gen import fetch

from typing import Dict, Optional
import pytest
import requests


# A trimmed down response entry of the 'search' endpoint,
# keeping the fields used by map_data().

def search_entry(**overrides) -> Dict:

    entry = {
        'name': 'Polaris',
        'type': {
            'name': 'Star'
        },
        'subType': {
            'name': 'Main Sequence Supergiant',
            'id': 'F7Ib'
        },
        'position': {
            'equatorial': {
                'rightAscension': {'string': '02h 31m 47s'},
                'declination': {'string': '89° 15\' 51"'}
            },
            'constellation': {
                'short': 'UMi',
                'name': 'Ursa Minor'
            }
        },
        'crossIdentification': [
            {'name': 'Polaris'},
            {'name': 'HD 8890'},
            {'name': 'Alpha UMi'}
        ]
    }
    entry.update(overrides)
    return entry


class FakeResponse:
    """Minimal stand-in for requests.Response."""

    def __init__(self, payload: Dict, error: Optional[Exception] = None):
        self.payload = payload
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self) -> Dict:
        return self.payload


@pytest.fixture
def get_mock(mocker):
    """Patch requests.get, returning a single search entry by default."""

    return mocker.patch.object(fetch.requests,
                               'get',
                               return_value=FakeResponse({'data': [search_entry()]}))


# astronomyapi_access()

def test_astronomyapi_access(monkeypatch):

    monkeypatch.setenv('ASTRONOMYAPI_ID', 'the-id')
    monkeypatch.setenv('ASTRONOMYAPI_SECRET', 'the-secret')

    assert fetch.astronomyapi_access() == ('the-id', 'the-secret')


def test_astronomyapi_access_unset(monkeypatch):

    monkeypatch.delenv('ASTRONOMYAPI_ID', raising=False)
    monkeypatch.delenv('ASTRONOMYAPI_SECRET', raising=False)

    # missing credentials fall back to empty strings
    assert fetch.astronomyapi_access() == ('', '')


# astronomyapi_get()

def test_astronomyapi_get(get_mock):

    data = fetch._astronomyapi_get(ep='search',
                                   params={'term': 'Polaris'},
                                   app_id='the-id',
                                   app_secret='the-secret')

    # the payload is unwrapped from 'data'
    assert data == [search_entry()]

    kwargs = get_mock.call_args.kwargs
    assert kwargs['url'] == 'https://api.astronomyapi.com/api/v2/search'
    assert kwargs['params'] == {'term': 'Polaris'}
    assert kwargs['timeout'] == 10
    # credentials are passed as base64 encoded basic auth
    assert kwargs['headers'] == {'Authorization': 'Basic dGhlLWlkOnRoZS1zZWNyZXQ='}


def test_astronomyapi_get_raises_on_http_error(mocker):

    error = requests.HTTPError('401 Unauthorized')
    mocker.patch.object(fetch.requests,
                        'get',
                        return_value=FakeResponse({}, error=error))

    with pytest.raises(requests.HTTPError):
        fetch._astronomyapi_get(ep='search',
                                params={},
                                app_id='the-id',
                                app_secret='the-secret')


# astronomyapi_search()

def test_astronomyapi_search(get_mock):

    data = fetch._astronomyapi_search('Polaris',
                                      app_id='the-id',
                                      app_secret='the-secret')

    assert data == search_entry()
    # an exact search of the requested term
    assert get_mock.call_args.kwargs['params'] == {'term': 'Polaris',
                                                   'match_type': 'exact'}


def test_astronomyapi_search_first_match_wins(mocker):

    entries = [search_entry(name='Polaris'), search_entry(name='Polaris B')]
    mocker.patch.object(fetch.requests,
                        'get',
                        return_value=FakeResponse({'data': entries}))

    data = fetch._astronomyapi_search('Polaris',
                                      app_id='the-id',
                                      app_secret='the-secret')
    assert data['name'] == 'Polaris'


def test_astronomyapi_search_no_match(mocker):

    mocker.patch.object(fetch.requests,
                        'get',
                        return_value=FakeResponse({'data': []}))

    assert fetch._astronomyapi_search('No Such Object',
                                      app_id='the-id',
                                      app_secret='the-secret') is None


# map_data()

def test_map_data():

    obj = fetch._map_data(search_entry())

    assert obj.name == 'Polaris'
    assert obj.ra == '02h 31m 47s'
    assert obj.dec == '89° 15\' 51"'
    # the short form of the constellation is used
    assert obj.constellation == 'UMi'
    assert obj.type == 'Star'
    assert obj.subtype == 'Main Sequence Supergiant'
    # the subtype id of a star is its spectral class
    assert obj.spectral_class == 'F7Ib'
    # the own name is dropped from the cross identifications
    assert obj.aka == ['HD 8890', 'Alpha UMi']


def test_map_data_missing_subtype_name():

    obj = fetch._map_data(search_entry(subType={'name': None, 'id': None}))

    assert obj.subtype == ''
    assert obj.spectral_class == ''


@pytest.mark.parametrize('subtype', [None, {}])
def test_map_data_no_subtype(subtype):

    # the default entry is a star, exercising the spectral class branch too
    obj = fetch._map_data(search_entry(subType=subtype))

    assert obj.subtype == ''
    assert obj.spectral_class == ''


def test_map_data_subtype_key_absent():

    entry = search_entry()
    del entry['subType']

    obj = fetch._map_data(entry)

    assert obj.subtype == ''
    assert obj.spectral_class == ''


def test_map_data_spectral_class_of_non_star():

    entry = search_entry(type={'name': 'Globular Cluster'},
                         subType={'name': 'Globular Cluster', 'id': 'GCl'})
    obj = fetch._map_data(entry)

    assert obj.type == 'Globular Cluster'
    assert obj.subtype == 'Globular Cluster'
    # the spectral class is meaningful for stars only
    assert obj.spectral_class == ''


def test_map_data_spectral_class_of_double_star():

    entry = search_entry(type={'name': 'Double Star'},
                         subType={'name': 'Double Star', 'id': 'F7Ib + F6V'})

    assert fetch._map_data(entry).spectral_class == 'F7Ib + F6V'


def test_map_data_no_cross_identification():

    obj = fetch._map_data(search_entry(crossIdentification=[]))

    assert obj.aka == []


# fetch()

def test_fetch(get_mock):

    obj = fetch.fetch('Polaris', app_id='the-id', app_secret='the-secret')

    assert obj is not None
    assert obj.name == 'Polaris'
    assert obj.constellation == 'UMi'


def test_fetch_no_match(mocker):

    mocker.patch.object(fetch.requests,
                        'get',
                        return_value=FakeResponse({'data': []}))

    assert fetch.fetch('No Such Object',
                       app_id='the-id',
                       app_secret='the-secret') is None


def test_fetch_swallows_request_error(mocker, capsys):

    mocker.patch.object(fetch.requests,
                        'get',
                        side_effect=requests.ConnectionError('no network'))

    assert fetch.fetch('Polaris', app_id='the-id', app_secret='the-secret') is None
    assert 'Unable to fetch data for Polaris' in capsys.readouterr().out


@pytest.mark.parametrize('app_id, app_secret', [('', 'the-secret'),
                                                ('the-id', ''),
                                                ('', '')])
def test_fetch_requires_credentials(app_id: str, app_secret: str, get_mock):

    with pytest.raises(AssertionError):
        fetch.fetch('Polaris', app_id=app_id, app_secret=app_secret)

    get_mock.assert_not_called()
