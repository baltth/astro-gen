#!/usr/bin/env python3

from astro_gen import db, project
from astro_gen.datatypes import ObjectData

from pathlib import Path
from ruamel.yaml import YAML
from typing import Callable, Dict
import pytest


# The db files are edited manually as well, therefore they contain
# comments and empty lines - keep those in the fixtures to be able
# to check round-trip editing.

SKETCH_DB = """\
# Sketch 'db' - list of sketches

sketches:

  - full: 2026/c47-alpha-umi-20260816.jpg
    scan: 2026/cluster_double_star.jpg
    sub:
      - 2026/c47-20260816.jpg
      - 2026/alpha-umi-20260816.jpg
    _cmd:
      - astro-gen ./examle add -i ./orig/cluster_double_star.jpg

  - full: 2026/gassendi-20260816.jpg
    notes: |
      [sketch notes]
"""

OBS_DB = """\
# Observation 'db' - list of observations

observations:

  - name: C47
    img: 2026/c47-20260816.jpg
    date: 2025-07-15 23:30
    nelm: 5.2
    seeing: 8
    ap: 150
    mag: 120
    fov: 0.6

  - name:
      - C47
      - Alpha UMi
    img: 2026/c47-alpha-umi-20260816.jpg
    date: 2025-07-16 00:15
    nelm: 5.2
    ap: 150
    mag: 120
    text: |
      [observation notes]
    data:
      PA: ~150°
"""

OBJECTS_DB = """\
# Object 'db' - map of object data

objects:

  Alpha UMi:
    constellation: UMi
    type: double star
    aka:
      - Polaris
    components:
      Alpha UMi A:
        name: HD 8890
        desc: Binary with a yellow main sequence supergiant primary
        spectral_class: F7Ib + F6V
      ~ B:
        desc: Main sequence star
    fetched:
      HD 8890:
        type: Star
        subtype: Main Sequence Supergiant
        ra: 02h 31m 47s

  Archimedes:
    constellation: Moon
    type: crater
    data:
      size: 81 km

  C47:
    constellation: Del
    type: globular cluster
    desc: Globular cluster
"""


@pytest.fixture
def project_root(tmp_path: Path) -> str:
    """A project directory with all three db files populated."""

    db_dir = tmp_path / 'db'
    db_dir.mkdir()
    (db_dir / 'sketch.yml').write_text(SKETCH_DB, encoding='utf-8')
    (db_dir / 'obs.yml').write_text(OBS_DB, encoding='utf-8')
    (db_dir / 'objects.yml').write_text(OBJECTS_DB, encoding='utf-8')
    return str(tmp_path)


@pytest.fixture
def write_yaml(tmp_path: Path) -> Callable[[str, str], str]:
    """Factory writing an arbitrary yaml file, returns its path."""

    def _write(name: str, content: str) -> str:
        p = tmp_path / name
        p.write_text(content, encoding='utf-8')
        return str(p)

    return _write


def read_back(file: str) -> db.YamlDict:
    return YAML().load(Path(file))


# load()

def test_load(project_root: str):

    data = db.load(project.sketch_db(project_root))
    assert isinstance(data, db.YamlDict)
    assert list(data.keys()) == ['sketches']


def test_load_rejects_non_mapping(write_yaml):

    file = write_yaml('list.yml', '- a\n- b\n')
    with pytest.raises(AssertionError):
        db.load(file)


def test_load_missing_file(project_root: str):

    with pytest.raises(FileNotFoundError):
        db.load(str(Path(project_root) / 'db' / 'no-such.yml'))


# sketches()

def test_sketches_raw(project_root: str):

    raw = db.sketches_raw(project_root)
    assert [r['full'] for r in raw] == ['2026/c47-alpha-umi-20260816.jpg',
                                        '2026/gassendi-20260816.jpg']
    # raw data keeps the entries not present in SketchData
    assert '_cmd' in raw[0].keys()


def test_sketches(project_root: str):

    sk = db.sketches(project_root)
    assert len(sk) == 2

    assert sk[0].full == '2026/c47-alpha-umi-20260816.jpg'
    assert sk[0].scan == '2026/cluster_double_star.jpg'
    assert sk[0].sub == ['2026/c47-20260816.jpg', '2026/alpha-umi-20260816.jpg']
    assert sk[0].notes == ''
    # '_cmd' is not part of SketchData, it's dropped silently
    assert not hasattr(sk[0], '_cmd')

    # missing optional fields fall back to the defaults
    assert sk[1].full == '2026/gassendi-20260816.jpg'
    assert sk[1].scan == ''
    assert sk[1].sub == []
    assert sk[1].notes == '[sketch notes]\n'


# observations()

def test_observations_raw(project_root: str):

    raw = db.observations_raw(project_root)
    assert len(raw) == 2
    # 'name' is untouched, no 'names' yet
    assert raw[0]['name'] == 'C47'
    assert 'names' not in raw[0].keys()


def test_observations(project_root: str):

    obs = db.observations(project_root)
    assert len(obs) == 2

    # single 'name' is wrapped into a list
    assert obs[0].names == ['C47']
    assert obs[0].img == '2026/c47-20260816.jpg'
    assert obs[0].date == '2025-07-15 23:30'
    assert obs[0].nelm == pytest.approx(5.2)
    assert obs[0].seeing == 8
    assert obs[0].ap == 150
    assert obs[0].mag == 120
    # 'fov' is stringified to keep the formatting of the db file
    assert obs[0].fov == '0.6'
    assert obs[0].data == {}

    # a list of 'name's is taken as is
    assert obs[1].names == ['C47', 'Alpha UMi']
    assert obs[1].seeing == 0
    # missing 'fov' stays the default, no stringification
    assert obs[1].fov == ''
    assert obs[1].text == '[observation notes]\n'
    assert obs[1].data == {'PA': '~150°'}


# objects()

def test_objects_raw(project_root: str):

    raw = db.objects_raw(project_root)
    assert list(raw.keys()) == ['Alpha UMi', 'Archimedes', 'C47']
    # raw entries have no 'name' injected yet
    assert 'name' not in raw['C47'].keys()


def test_objects(project_root: str):

    objs = db.objects(project_root)
    assert list(objs.keys()) == ['Alpha UMi', 'Archimedes', 'C47']

    # the db key is used as name
    assert objs['C47'].name == 'C47'
    assert objs['C47'].constellation == 'Del'
    assert objs['C47'].type == 'globular cluster'
    assert objs['C47'].desc == 'Globular cluster'
    assert objs['C47'].components == {}
    assert objs['C47'].fetched == {}

    assert objs['Archimedes'].data == {'size': '81 km'}

    a_umi = objs['Alpha UMi']
    assert a_umi.aka == ['Polaris']
    assert list(a_umi.components.keys()) == ['Alpha UMi A', '~ B']
    # an explicit component 'name' is kept ...
    assert a_umi.components['Alpha UMi A'].name == 'HD 8890'
    # ... a missing one defaults to the component key
    assert a_umi.components['~ B'].name == '~ B'
    assert isinstance(a_umi.fetched['HD 8890'], ObjectData)
    assert a_umi.fetched['HD 8890'].name == 'HD 8890'
    assert a_umi.fetched['HD 8890'].subtype == 'Main Sequence Supergiant'


# save()

def test_save_roundtrip_keeps_comments(project_root: str):

    file = project.obs_db(project_root)
    original = Path(file).read_text(encoding='utf-8')

    db.save(file, db.load(file))

    assert Path(file).read_text(encoding='utf-8') == original


def test_save_creates_file(tmp_path: Path):

    file = str(tmp_path / 'out.yml')
    db.save(file, {'objects': {'M31': {'type': 'galaxy'}}})

    assert read_back(file) == {'objects': {'M31': {'type': 'galaxy'}}}


# update_in_list() / add_to_list()

def match_full(x: Dict, y: Dict) -> bool:
    return x['full'] == y['full']


def test_update_in_list_hit(project_root: str):

    sdb = db.load(project.sketch_db(project_root))
    sk_list = sdb['sketches']

    updated = db.update_in_list(sk_list,
                                {'full': '2026/gassendi-20260816.jpg', 'scan': 'craters.jpg'},
                                match_full)
    assert updated
    assert len(sk_list) == 2
    assert sk_list[1]['scan'] == 'craters.jpg'
    # fields not present in the update are kept
    assert sk_list[1]['notes'] == '[sketch notes]\n'


def test_update_in_list_miss(project_root: str):

    sdb = db.load(project.sketch_db(project_root))
    sk_list = sdb['sketches']

    assert not db.update_in_list(sk_list, {'full': 'm31-20260816.jpg'}, match_full)
    assert len(sk_list) == 2


def test_add_to_list(project_root: str):

    file = project.sketch_db(project_root)
    sdb = db.load(file)
    db.add_to_list(sdb['sketches'], {'full': 'm31-20260816.jpg'})
    db.save(file, sdb)

    written = Path(file).read_text(encoding='utf-8')
    assert read_back(file)['sketches'][-1]['full'] == 'm31-20260816.jpg'
    # the new entry is separated by an empty line
    assert written.endswith('\n\n  - full: m31-20260816.jpg\n')


# add_sketch()

def test_add_sketch_new(project_root: str):

    db.add_sketch(project_root,
                  full='m31-saturn-20260816.jpg',
                  scan='galaxy_planet.jpg',
                  sub=['m31-20260816.jpg', 'saturn-20260816.jpg'],
                  cmd=['astro-gen . add -i x.jpg'])

    sketches = read_back(project.sketch_db(project_root))['sketches']
    assert len(sketches) == 3
    assert sketches[-1] == {'full': 'm31-saturn-20260816.jpg',
                            'scan': 'galaxy_planet.jpg',
                            'sub': ['m31-20260816.jpg', 'saturn-20260816.jpg'],
                            '_cmd': ['astro-gen . add -i x.jpg']}


def test_add_sketch_optional_fields_omitted(project_root: str):

    db.add_sketch(project_root, full='m31-20260816.jpg')

    sketches = read_back(project.sketch_db(project_root))['sketches']
    assert sketches[-1] == {'full': 'm31-20260816.jpg'}


def test_add_sketch_existing_is_updated(project_root: str):

    db.add_sketch(project_root,
                  full='2026/gassendi-20260816.jpg',
                  scan='craters.jpg')

    sketches = read_back(project.sketch_db(project_root))['sketches']
    # no new entry, matched by 'full'
    assert len(sketches) == 2
    assert sketches[1]['scan'] == 'craters.jpg'
    assert sketches[1]['notes'] == '[sketch notes]\n'


# add_obs()

def test_add_obs_new(project_root: str):

    db.add_obs(project_root, name='M31', date='2026-08-15')

    obs = read_back(project.obs_db(project_root))['observations']
    assert len(obs) == 3

    entry = obs[-1]
    assert list(entry.keys()) == ['name', 'img', 'date', 'loc',
                                  'nelm', 'seeing', 'ap', 'mag', 'fov', 'text']
    assert entry['name'] == 'M31'
    assert entry['img'] == '2026/m31-20260815.jpg'
    assert entry['date'] == '2026-08-15'
    # all measurement fields are added empty, to be filled manually
    assert entry['loc'] == ''
    assert entry['text'] == ''
    for k in ['nelm', 'seeing', 'ap', 'mag', 'fov']:
        assert entry[k] == pytest.approx(0)


def test_add_obs_multiple_names(project_root: str):

    db.add_obs(project_root, name='M31, Saturn', date='2026-08-15')

    entry = read_back(project.obs_db(project_root))['observations'][-1]
    # more than one name is stored as a list
    assert entry['name'] == ['M31', 'Saturn']
    assert entry['img'] == '2026/m31-saturn-20260815.jpg'


def test_add_obs_single_name_kept_as_string(project_root: str):

    db.add_obs(project_root, name='Alpha UMi', date='2026-08-15')

    entry = read_back(project.obs_db(project_root))['observations'][-1]
    assert entry['name'] == 'Alpha UMi'
    assert entry['img'] == '2026/alpha-umi-20260815.jpg'


def test_add_obs_duplicate_is_skipped(project_root: str):

    file = project.obs_db(project_root)
    original = Path(file).read_text(encoding='utf-8')

    # same name and img as the first fixture entry
    db.add_obs(project_root, name='C47', date='2026-08-16')

    assert Path(file).read_text(encoding='utf-8') == original


# _refresh_with_fetched()

def fetched_m31() -> ObjectData:
    return ObjectData(name='NGC 224',
                      constellation='And',
                      type='Galaxy',
                      subtype='Spiral',
                      ra='00h 43m 20s',
                      dec='41° 21\' 45"')


def test_refresh_with_fetched_fills_empty_fields():

    entry = {'constellation': '', 'type': ''}
    res = db._refresh_with_fetched(entry, fetched_m31())

    assert res['constellation'] == 'And'
    # 'type' is lowercased for the object's own field
    assert res['type'] == 'galaxy'
    # ... but kept as fetched under 'fetched'
    assert res['fetched']['NGC 224']['type'] == 'Galaxy'
    assert res['fetched']['NGC 224']['subtype'] == 'Spiral'


def test_refresh_with_fetched_keeps_existing_fields():

    entry = {'constellation': 'Andromeda', 'type': 'spiral galaxy'}
    res = db._refresh_with_fetched(entry, fetched_m31())

    assert res['constellation'] == 'Andromeda'
    assert res['type'] == 'spiral galaxy'


def test_refresh_with_fetched_does_not_modify_input():

    entry = {'constellation': '', 'type': ''}
    db._refresh_with_fetched(entry, fetched_m31())

    assert entry == {'constellation': '', 'type': ''}


def test_refresh_with_fetched_drops_redundant_keys():

    res = db._refresh_with_fetched({'constellation': '', 'type': ''}, fetched_m31())
    keys = res['fetched']['NGC 224'].keys()

    # redundant or empty fields are not duplicated into the db
    for k in ['name', 'constellation', 'data', 'desc', 'spectral_class', 'mag']:
        assert k not in keys
    assert set(keys) == {'type', 'subtype', 'ra', 'dec', 'aka'}


def test_refresh_with_fetched_keeps_filled_optional_keys():

    fetched = ObjectData(name='HD 8890', type='Star',
                         desc='Supergiant', spectral_class='F7Ib', mag='2.0')
    res = db._refresh_with_fetched({'constellation': 'UMi', 'type': ''}, fetched)

    f = res['fetched']['HD 8890']
    assert f['desc'] == 'Supergiant'
    assert f['spectral_class'] == 'F7Ib'
    assert f['mag'] == '2.0'


def test_refresh_with_fetched_component_reference():

    fetched = ObjectData(name='HD 8890', type='Star')
    res = db._refresh_with_fetched({'constellation': 'UMi', 'type': ''},
                                   fetched,
                                   comp='Alpha UMi A')

    # the component gets a reference to the fetched data set
    assert res['components'] == {'Alpha UMi A': {'name': 'HD 8890'}}
    assert 'HD 8890' in res['fetched'].keys()


def test_refresh_with_fetched_component_same_name():

    fetched = ObjectData(name='HD 8890', type='Star')
    res = db._refresh_with_fetched({'constellation': 'UMi', 'type': ''},
                                   fetched,
                                   comp='HD 8890')

    # no reference needed when the component is named as the fetched object
    assert 'components' not in res.keys()


# add_object()

def object_dict(root: str) -> db.YamlDict:
    return db.load(project.object_db(root))['objects']


def test_add_object_new(project_root: str):

    objs = object_dict(project_root)
    assert db.add_object(objs, 'M31', fetched={})

    assert objs['M31'] == {'constellation': '', 'type': ''}


def test_add_object_constellation_from_name(project_root: str):

    objs = object_dict(project_root)
    assert db.add_object(objs, 'Beta Cyg', fetched={})

    assert objs['Beta Cyg']['constellation'] == 'Cyg'


def test_add_object_inserted_sorted(project_root: str):

    objs = object_dict(project_root)
    db.add_object(objs, 'B Obj', fetched={})
    db.add_object(objs, 'M31', fetched={})

    assert list(objs.keys()) == ['Alpha UMi', 'Archimedes', 'B Obj', 'C47', 'M31']


def test_add_object_existing_is_skipped(project_root: str):

    objs = object_dict(project_root)
    assert not db.add_object(objs, 'C47', fetched={})

    # untouched
    assert objs['C47']['desc'] == 'Globular cluster'
    assert 'fetched' not in objs['C47'].keys()


def test_add_object_refresh_of_existing(project_root: str):

    objs = object_dict(project_root)
    fetched = {'C47': ObjectData(name='C47', constellation='Del', type='Globular Cluster',
                                 ra='20h 34m 11s')}
    assert db.add_object(objs, 'C47', fetched=fetched, refresh=True)

    # the manually edited fields are kept, the fetched data is added
    assert objs['C47']['desc'] == 'Globular cluster'
    assert objs['C47']['type'] == 'globular cluster'
    assert objs['C47']['fetched']['C47']['ra'] == '20h 34m 11s'
    # position is unchanged
    assert list(objs.keys()) == ['Alpha UMi', 'Archimedes', 'C47']


def test_add_object_with_fetch_map(project_root: str):

    objs = object_dict(project_root)
    fetched = {'HD 8890': ObjectData(name='HD 8890', constellation='UMi', type='Star')}
    assert db.add_object(objs, 'Beta Cyg', fetched=fetched,
                         fetch_map={'Beta Cyg A': 'HD 8890'})

    entry = objs['Beta Cyg']
    assert entry['components'] == {'Beta Cyg A': {'name': 'HD 8890'}}
    assert entry['fetched']['HD 8890']['type'] == 'Star'
    # 'constellation' comes from the name, 'type' from the fetched data
    assert entry['constellation'] == 'Cyg'
    assert entry['type'] == 'star'


# add_objects()

def test_add_objects_single(project_root: str):

    db.add_objects(project_root, name='M31')

    objs = read_back(project.object_db(project_root))['objects']
    assert list(objs.keys()) == ['Alpha UMi', 'Archimedes', 'C47', 'M31']


def test_add_objects_comma_separated_list(project_root: str):

    db.add_objects(project_root, name='M31, Saturn')

    objs = read_back(project.object_db(project_root))['objects']
    assert 'M31' in objs.keys()
    assert 'Saturn' in objs.keys()


def test_add_objects_no_write_when_all_present(project_root: str):

    file = project.object_db(project_root)
    original = Path(file).read_text(encoding='utf-8')

    db.add_objects(project_root, name='C47, Archimedes')

    assert Path(file).read_text(encoding='utf-8') == original


def test_add_objects_writes_when_any_added(project_root: str):

    db.add_objects(project_root, name='C47, M31')

    objs = read_back(project.object_db(project_root))['objects']
    assert 'M31' in objs.keys()


def test_add_objects_with_fetch_map(project_root: str):

    fetched = {'HD 8890': ObjectData(name='HD 8890', type='Star')}
    db.add_objects(project_root,
                   name='Beta Cyg',
                   fetched=fetched,
                   fetch_map={'Beta Cyg': {'Beta Cyg A': 'HD 8890'}})

    entry = read_back(project.object_db(project_root))['objects']['Beta Cyg']
    assert entry['components']['Beta Cyg A']['name'] == 'HD 8890'
    assert entry['fetched']['HD 8890']['type'] == 'Star'
