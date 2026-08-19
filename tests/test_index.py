#!/usr/bin/env python3

from astro_gen import index
from astro_gen import pages
from astro_gen.datatypes import Object, ObsData


# raw_data()

def test_raw_data():

    obs_db = [ObsData(names=['C47'], date='2026-08-16 23:30')]
    object_db = {'C47': Object(name='C47', constellation='Del', type='globular cluster')}

    raw = index.raw_data(obs_db, object_db)
    assert len(raw) == 1
    assert raw[0]['name'] == 'C47'
    assert raw[0]['obj'] == object_db['C47']
    assert raw[0]['row'] == pages.index_row('C47', ['C47'], '2026-08-16', object_db['C47'])


def test_raw_data_entry_per_name():

    obs_db = [ObsData(names=['C47', 'Alpha UMi'], date='2026-08-16')]
    object_db = {'C47': Object(name='C47'), 'Alpha UMi': Object(name='Alpha UMi')}

    raw = index.raw_data(obs_db, object_db)
    # an entry for each observed object, sorted by name
    assert [d['name'] for d in raw] == ['Alpha UMi', 'C47']
    # both link to the common observation page
    assert all(d['row'][2] == '../obs/2026/c47-alpha-umi-2026-08-16.md' for d in raw)


def test_raw_data_sorted_naturally():

    obs_db = [ObsData(names=['M110', 'M13', 'M3'], date='2026-08-16')]
    object_db = {n: Object(name=n) for n in ['M110', 'M13', 'M3']}

    assert [d['name'] for d in index.raw_data(obs_db, object_db)] == ['M3', 'M13', 'M110']


def test_raw_data_latest_observation_wins():

    obs_db = [ObsData(names=['C47'], date='2026-08-16'),
              ObsData(names=['C47'], date='2025-01-02')]
    object_db = {'C47': Object(name='C47')}

    raw = index.raw_data(obs_db, object_db)
    # a single entry, pointing to the latest observation
    assert len(raw) == 1
    assert raw[0]['row'][2] == '../obs/2026/c47-2026-08-16.md'


def test_raw_data_no_data():

    assert index.raw_data([], {}) == []


# get_type()

def test_get_type_stars():

    assert index.get_type(Object(type='star')) == 'Stars'
    assert index.get_type(Object(type='double star')) == 'Stars'
    assert index.get_type(Object(type='variable star')) == 'Stars'


def test_get_type_moon():

    assert index.get_type(Object(type='crater')) == 'Moon'
    # anything on the Moon belongs here
    assert index.get_type(Object(constellation='Moon', type='mountain range')) == 'Moon'


def test_get_type_stars_win_over_moon():

    # a star seen next to the Moon is still a star
    assert index.get_type(Object(constellation='Moon', type='star')) == 'Stars'


def test_get_type_other():

    assert index.get_type(Object(type='planet')) == 'Other'
    assert index.get_type(Object(type='comet')) == 'Other'
    assert index.get_type(Object(type='asterism')) == 'Other'


def test_get_type_deep_space_is_the_default():

    assert index.get_type(Object(type='globular cluster')) == 'Deep space'
    assert index.get_type(Object(type='spiral galaxy')) == 'Deep space'
    assert index.get_type(Object()) == 'Deep space'


def test_get_type_matches_whole_words_only():

    # 'stars' or 'craters' are not the keywords looked for
    assert index.get_type(Object(type='cluster of stars')) == 'Deep space'


# sort_categories()

def test_sort_categories():

    res = index.sort_categories({'Stars': 1, 'Deep space': 2}.items())
    assert list(res.keys()) == ['Deep space', 'Stars']
    assert res['Stars'] == 1


def test_sort_categories_moon_and_other_are_last():

    data = {'Other': 1, 'Moon': 2, 'Stars': 3, 'Deep space': 4}.items()
    assert list(index.sort_categories(data).keys()) == \
        ['Deep space', 'Stars', 'Moon', 'Other']


def test_sort_categories_no_data():

    assert index.sort_categories([]) == {}


# collect()

def obj_data(obj: Object) -> dict:
    """A `raw_data()` item with the object name used as the row."""
    return {'name': obj.name, 'obj': obj, 'row': [obj.name]}


def test_collect():

    data = [obj_data(Object(name='C47', type='globular cluster')),
            obj_data(Object(name='Alpha UMi', type='double star')),
            obj_data(Object(name='Archimedes', type='crater'))]

    assert index.collect(data, key=index.get_type) == {
        'Deep space': [['C47']],
        'Stars': [['Alpha UMi']],
        'Moon': [['Archimedes']]
    }


def test_collect_keeps_category_order():

    data = [obj_data(Object(name='Archimedes', type='crater')),
            obj_data(Object(name='Jupiter', type='planet')),
            obj_data(Object(name='C47', type='globular cluster'))]

    assert list(index.collect(data, key=index.get_type).keys()) == \
        ['Deep space', 'Moon', 'Other']


def test_collect_sorts_rows_of_a_category():

    data = [obj_data(Object(name='M31', type='galaxy')),
            obj_data(Object(name='C47', type='globular cluster')),
            obj_data(Object(name='M3', type='globular cluster'))]

    assert index.collect(data, key=index.get_type)['Deep space'] == \
        [['C47'], ['M3'], ['M31']]


def test_collect_sorts_index_rows_by_name():

    obj = Object(name='M3', type='globular cluster')
    rows = [pages.index_row(n, n, '2026-08-16', obj) for n in ['M31', 'M3', 'C47']]
    data = [{'name': r[1], 'obj': obj, 'row': r} for r in rows]

    # the leading column of an index row is empty, the name decides
    assert [r[1] for r in index.collect(data, key=index.get_type)['Deep space']] == \
        ['C47', 'Messier 3', 'Messier 31']


def test_collect_custom_key():

    data = [obj_data(Object(name='C47', constellation='Del')),
            obj_data(Object(name='Alpha UMi', constellation='UMi'))]

    assert index.collect(data, key=lambda o: o.constellation) == {
        'Del': [['C47']],
        'UMi': [['Alpha UMi']]
    }


def test_collect_no_data():

    assert index.collect([], key=index.get_type) == {}


# subpage()

def test_subpage():

    assert index.subpage('Categories', ['- item']) == ['## Categories', '', '- item', '']


def test_subpage_no_content():

    assert index.subpage('Categories', []) == ['## Categories', '', '']


# index_content()

def test_index_content():

    obs_db = [ObsData(names=['C47'], date='2026-08-16')]
    object_db = {'C47': Object(name='C47', constellation='Del', type='globular cluster')}

    assert index.index_content(obs_db, object_db) == [
        '## Categories',
        '',
        '#### Deep space',
        '',
        '- [C47](../obs/2026/c47-2026-08-16.md) - globular cluster in Delphinus',
        '',
        '',
        '## By constellation',
        '',
        '#### Delphinus',
        '',
        '- [C47](../obs/2026/c47-2026-08-16.md) - globular cluster in Delphinus',
        '',
        ''
    ]


def test_index_content_unknown_constellation_is_other():

    obs_db = [ObsData(names=['Archimedes'], date='2026-08-16')]
    object_db = {'Archimedes': Object(name='Archimedes', constellation='Moon',
                                      type='crater')}

    md = index.index_content(obs_db, object_db)
    # the Moon is no constellation
    assert md[md.index('## By constellation') + 2] == '#### Other'


def test_index_content_no_data():

    assert index.index_content([], {}) == [
        '## Categories', '', '',
        '## By constellation', '', ''
    ]
