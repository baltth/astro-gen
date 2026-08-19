#!/usr/bin/env python3

from astro_gen import add
from astro_gen.datatypes import ObjectData
from astro_gen.main import arg_parser

from datetime import datetime
from pathlib import Path
from typing import Dict
import pytest


IMG_DATE = datetime(2026, 8, 16, 23, 30)


# A typical return value of proc_image.split_cmd() for a single object.

def split_data(**overrides) -> Dict:

    data = {
        'img_date': IMG_DATE,
        'first_name': 'C47',
        'first_img': 'c47-20260816.jpg',
        'cropped_img': 'c47-na-20260816.jpg'
    }
    data.update(overrides)
    return data


@pytest.fixture
def project_root(tmp_path) -> str:
    """A project folder without a meta file."""

    (tmp_path / 'docs' / 'img').mkdir(parents=True)
    (tmp_path / 'docs' / 'scan').mkdir()
    return str(tmp_path)


@pytest.fixture
def meta_file(project_root) -> str:
    """Add a meta file to the project."""

    p = Path(project_root) / 'static' / 'meta.yaml'
    p.parent.mkdir()
    p.write_text('copyright: Jane Doe\n')
    return str(p.resolve())


@pytest.fixture
def split_mock(mocker):
    return mocker.patch.object(add.proc_image, 'split_cmd', return_value=split_data())


@pytest.fixture
def copyright_mock(mocker):
    return mocker.patch.object(add.proc_image, 'copyright_cmd')


@pytest.fixture
def cp_mock(mocker):
    return mocker.patch.object(add, 'cp')


@pytest.fixture
def db_mock(mocker):
    return mocker.patch.object(add, 'db')


@pytest.fixture
def fetch_mock(mocker):
    """Patch the fetch module with credentials set and a single object found."""

    m = mocker.patch.object(add, 'fetch')
    m.astronomyapi_access.return_value = ('the-id', 'the-secret')
    m.fetch.side_effect = lambda name, **kwargs: ObjectData(name=name)
    return m


# _add_images()

def test_add_images(project_root, split_mock):

    data = add._add_images(project_root=project_root,
                           img='./orig/cluster.jpg',
                           x_offset=10,
                           y_offset=-20,
                           scale=0.5,
                           first_object='C47',
                           second_object='Alpha UMi',
                           full_page=True,
                           simple=True)

    assert data == split_data()

    kwargs = split_mock.call_args.kwargs
    assert kwargs['source_image'] == './orig/cluster.jpg'
    # the images are written into the site image folder
    assert kwargs['dest'] == str(Path(project_root, 'docs', 'img').resolve())
    assert kwargs['x_offset'] == 10
    assert kwargs['y_offset'] == -20
    assert kwargs['scale'] == pytest.approx(0.5)
    assert kwargs['first_object'] == 'C47'
    assert kwargs['second_object'] == 'Alpha UMi'
    assert kwargs['full_page'] is True
    assert kwargs['simple'] is True
    # never interactive
    assert kwargs['show'] is False
    # no meta file in the project, no copyright is added
    assert kwargs['copyright_file'] == ''


def test_add_images_defaults(project_root, split_mock):

    add._add_images(project_root=project_root, img='./orig/cluster.jpg')

    kwargs = split_mock.call_args.kwargs
    assert kwargs['x_offset'] == 0
    assert kwargs['y_offset'] == 0
    assert kwargs['scale'] == pytest.approx(1.0)
    assert kwargs['first_object'] == ''
    assert kwargs['second_object'] == ''
    assert kwargs['full_page'] is False
    assert kwargs['simple'] is False


def test_add_images_with_meta_file(project_root, meta_file, split_mock):

    add._add_images(project_root=project_root, img='./orig/cluster.jpg')

    # the meta file of the project provides the copyright data
    assert split_mock.call_args.kwargs['copyright_file'] == meta_file


def test_add_images_no_scan(project_root, split_mock, copyright_mock, cp_mock):

    data = add._add_images(project_root=project_root, img='./orig/cluster.jpg')

    assert 'scan' not in data
    copyright_mock.assert_not_called()
    cp_mock.assert_not_called()


def test_add_images_scan_with_meta_file(project_root,
                                        meta_file,
                                        split_mock,
                                        copyright_mock,
                                        cp_mock):

    data = add._add_images(project_root=project_root,
                           img='./orig/cluster.jpg',
                           scan='./orig/scanned.jpg')

    # the scan is registered by its file name, below the folder of its year
    assert data['scan'] == '2026/scanned.jpg'

    # it's copied to the scan folder of the site with a copyright note
    kwargs = copyright_mock.call_args.kwargs
    assert kwargs['source_image'] == './orig/scanned.jpg'
    assert kwargs['copyright_file'] == meta_file
    assert kwargs['out'] == f'{Path(project_root, "docs").resolve()}/scan/2026/scanned.jpg'
    assert kwargs['show'] is False

    cp_mock.assert_not_called()


def test_add_images_scan_without_meta_file(project_root,
                                           split_mock,
                                           copyright_mock,
                                           cp_mock):

    data = add._add_images(project_root=project_root,
                           img='./orig/cluster.jpg',
                           scan='./orig/scanned.jpg')

    assert data['scan'] == '2026/scanned.jpg'
    copyright_mock.assert_not_called()

    # the scan is copied as-is
    cp_mock.assert_called_once_with(
        './orig/scanned.jpg',
        f'{Path(project_root, "docs").resolve()}/scan/2026/scanned.jpg')


def test_add_images_scan_folder_is_created(project_root,
                                           split_mock,
                                           cp_mock):
    """The scan folder of the year has to be created before copying into it."""

    scan_dir = Path(project_root, 'docs', 'scan', '2026')
    assert not scan_dir.is_dir()

    add._add_images(project_root=project_root,
                    img='./orig/cluster.jpg',
                    scan='./orig/scanned.jpg')

    assert scan_dir.is_dir()


def test_add_images_scan_folder_is_created_with_meta_file(project_root,
                                                          meta_file,
                                                          split_mock,
                                                          copyright_mock):
    """The scan folder of the year is created for the copyright variant too."""

    scan_dir = Path(project_root, 'docs', 'scan', '2026')
    assert not scan_dir.is_dir()

    add._add_images(project_root=project_root,
                    img='./orig/cluster.jpg',
                    scan='./orig/scanned.jpg')

    assert scan_dir.is_dir()


def test_add_images_scan_folder_exists(project_root,
                                       split_mock,
                                       cp_mock):
    """An existing scan folder is no error."""

    Path(project_root, 'docs', 'scan', '2026').mkdir(parents=True)

    data = add._add_images(project_root=project_root,
                           img='./orig/cluster.jpg',
                           scan='./orig/scanned.jpg')

    assert data['scan'] == '2026/scanned.jpg'


def test_add_images_scan_of_other_year(project_root,
                                       split_mock,
                                       cp_mock):
    """The scan follows the date of the source image."""

    split_mock.return_value = split_data(img_date=datetime(2025, 1, 2, 21, 0))

    data = add._add_images(project_root=project_root,
                           img='./orig/cluster.jpg',
                           scan='./orig/scanned.jpg')

    assert data['scan'] == '2025/scanned.jpg'
    assert Path(project_root, 'docs', 'scan', '2025').is_dir()
    cp_mock.assert_called_once_with(
        './orig/scanned.jpg',
        f'{Path(project_root, "docs").resolve()}/scan/2025/scanned.jpg')


# _add_sketch()

def test_add_sketch(db_mock):

    data = split_data(second_name='Alpha UMi',
                      second_img='alpha-umi-20260816.jpg',
                      scan='scanned.jpg')

    add._add_sketch(root='/the/root', data=data, cmd='astro-gen /the/root add -i x.jpg')

    db_mock.add_sketch.assert_called_once_with(
        root='/the/root',
        full='c47-na-20260816.jpg',
        scan='scanned.jpg',
        sub=['c47-20260816.jpg', 'alpha-umi-20260816.jpg'],
        cmd=['astro-gen /the/root add -i x.jpg'])


def test_add_sketch_single_object(db_mock):

    add._add_sketch(root='/the/root', data=split_data(), cmd='the cmd')

    kwargs = db_mock.add_sketch.call_args.kwargs
    # the missing second image is dropped
    assert kwargs['sub'] == ['c47-20260816.jpg']
    # as is the missing scan
    assert kwargs['scan'] == ''


def test_add_sketch_full_page(db_mock):

    data = split_data()
    del data['first_img']

    add._add_sketch(root='/the/root', data=data, cmd='the cmd')

    assert db_mock.add_sketch.call_args.kwargs['sub'] == []


def test_add_sketch_cmd_from_argv(db_mock, monkeypatch):

    monkeypatch.setattr(add.sys, 'argv', ['astro-gen', '/the/root', 'add', '-i', 'the img.jpg'])

    add._add_sketch(root='/the/root', data=split_data())

    # the invocation is recorded, quoted to stay reusable
    assert db_mock.add_sketch.call_args.kwargs['cmd'] == \
        ['astro-gen /the/root add -i \'the img.jpg\'']


# _add_observation()

def test_add_observation(db_mock):

    add._add_observation(root='/the/root', name='C47', img_date=IMG_DATE)

    # the time of the image is dropped, the date is stored in ISO format
    db_mock.add_obs.assert_called_once_with('/the/root',
                                            name='C47',
                                            date='2026-08-16')


# _add_objects()

def test_add_objects(db_mock, fetch_mock):

    add._add_objects(root='/the/root', name='C47')

    fetch_mock.fetch.assert_called_once_with('C47',
                                             app_id='the-id',
                                             app_secret='the-secret')
    db_mock.add_objects.assert_called_once_with('/the/root',
                                                name='C47',
                                                fetched={'C47': ObjectData(name='C47')})


def test_add_objects_without_credentials(db_mock, fetch_mock):

    fetch_mock.astronomyapi_access.return_value = ('', '')

    add._add_objects(root='/the/root', name='C47')

    # the object is added even without fetched data
    fetch_mock.fetch.assert_not_called()
    db_mock.add_objects.assert_called_once_with('/the/root', name='C47', fetched={})


# add()

def test_add(project_root, split_mock, db_mock, fetch_mock):

    add.add(project_root=project_root,
            img='./orig/cluster.jpg',
            first_object='C47',
            cmd='the cmd')

    split_mock.assert_called_once()
    db_mock.add_sketch.assert_called_once()
    db_mock.add_obs.assert_called_once_with(project_root, name='C47', date='2026-08-16')
    db_mock.add_objects.assert_called_once_with(project_root,
                                                name='C47',
                                                fetched={'C47': ObjectData(name='C47')})


def test_add_two_objects(project_root, split_mock, db_mock, fetch_mock):

    add.add(project_root=project_root,
            img='./orig/cluster.jpg',
            first_object='C47',
            second_object='Alpha UMi',
            cmd='the cmd')

    # a single sketch with an observation of both objects
    db_mock.add_sketch.assert_called_once()
    assert [c.kwargs['name'] for c in db_mock.add_obs.call_args_list] == ['C47', 'Alpha UMi']
    assert [c.kwargs['name'] for c in db_mock.add_objects.call_args_list] == ['C47', 'Alpha UMi']


def test_add_no_objects(project_root, split_mock, db_mock, fetch_mock):

    add.add(project_root=project_root, img='./orig/cluster.jpg', cmd='the cmd')

    # the sketch is added, but there's nothing to observe
    db_mock.add_sketch.assert_called_once()
    db_mock.add_obs.assert_not_called()
    db_mock.add_objects.assert_not_called()


# fetch_astronomyapi_on_demand()

def test_fetch_astronomyapi_on_demand(fetch_mock):

    assert add.fetch_astronomyapi_on_demand('C47') == {'C47': ObjectData(name='C47')}


def test_fetch_astronomyapi_on_demand_multiple_names(fetch_mock):

    data = add.fetch_astronomyapi_on_demand('C47, Alpha UMi')

    # each name is fetched separately
    assert data == {'C47': ObjectData(name='C47'),
                    'Alpha UMi': ObjectData(name='Alpha UMi')}
    assert [c.args[0] for c in fetch_mock.fetch.call_args_list] == ['C47', 'Alpha UMi']


def test_fetch_astronomyapi_on_demand_skips_missing(fetch_mock):

    fetch_mock.fetch.side_effect = \
        lambda name, **kwargs: ObjectData(name=name) if name == 'C47' else None

    assert add.fetch_astronomyapi_on_demand('C47, No Such Object') == \
        {'C47': ObjectData(name='C47')}


@pytest.mark.parametrize('access', [('', 'the-secret'), ('', '')])
def test_fetch_astronomyapi_on_demand_without_credentials(access, fetch_mock):

    fetch_mock.astronomyapi_access.return_value = access

    assert add.fetch_astronomyapi_on_demand('C47') == {}
    fetch_mock.fetch.assert_not_called()


# fetch_objects()

def test_fetch_objects(db_mock, fetch_mock):

    add.fetch_objects(project_root='/the/root', obj='C47')

    fetch_mock.fetch.assert_called_once_with('C47',
                                             app_id='the-id',
                                             app_secret='the-secret')
    db_mock.add_objects.assert_called_once_with(root='/the/root',
                                                name='C47',
                                                fetched={'C47': ObjectData(name='C47')},
                                                fetch_map={'C47': {'C47': 'C47'}},
                                                refresh=True)


def test_fetch_objects_by_alias(db_mock, fetch_mock):

    add.fetch_objects(project_root='/the/root', obj='C47', name='NGC 6934')

    # the alias is fetched ...
    assert fetch_mock.fetch.call_args.args == ('NGC 6934',)
    kwargs = db_mock.add_objects.call_args.kwargs
    # ... and stored for the object under its own name
    assert kwargs['name'] == 'C47'
    assert kwargs['fetched'] == {'NGC 6934': ObjectData(name='NGC 6934')}
    assert kwargs['fetch_map'] == {'C47': {'NGC 6934': 'NGC 6934'}}


def test_fetch_objects_as_component(db_mock, fetch_mock):

    add.fetch_objects(project_root='/the/root',
                      obj='Alpha UMi',
                      name='Polaris B',
                      component='B')

    # the fetched data is mapped to the component of the object
    assert db_mock.add_objects.call_args.kwargs['fetch_map'] == \
        {'Alpha UMi': {'B': 'Polaris B'}}


def test_fetch_objects_no_data(db_mock, fetch_mock, capsys):

    fetch_mock.fetch.return_value = None
    fetch_mock.fetch.side_effect = None

    add.fetch_objects(project_root='/the/root', obj='No Such Object')

    db_mock.add_objects.assert_not_called()
    assert 'No data for No Such Object' in capsys.readouterr().out


def test_fetch_objects_without_credentials(db_mock, fetch_mock, capsys):

    fetch_mock.astronomyapi_access.return_value = ('', '')

    add.fetch_objects(project_root='/the/root', obj='C47')

    db_mock.add_objects.assert_not_called()
    assert 'No data for C47' in capsys.readouterr().out


# reproc()

ADD_CMD = 'astro-gen ./example add -i ./orig/cluster.jpg -o1 C47 -x 10 --simple'
REGEN_CMD = 'astro-gen ./example regen'


def sketch_entry(full: str = 'c47-na-20260816.jpg', **overrides) -> Dict:

    entry = {'full': full, '_cmd': [ADD_CMD]}
    entry.update(overrides)
    return entry


@pytest.fixture
def sketches_mock(db_mock):
    """Return a single reprocessable sketch by default."""

    db_mock.sketches_raw.return_value = [sketch_entry()]
    return db_mock.sketches_raw


def test_reproc(project_root, sketches_mock, split_mock, db_mock):

    add.reproc(project_root=project_root, arg_parser=arg_parser())

    # the recorded command line is replayed
    kwargs = split_mock.call_args.kwargs
    assert kwargs['source_image'] == './orig/cluster.jpg'
    assert kwargs['first_object'] == 'C47'
    assert kwargs['x_offset'] == 10
    assert kwargs['simple'] is True
    assert kwargs['full_page'] is False

    # the sketch is updated, keeping the original command
    assert db_mock.add_sketch.call_args.kwargs['cmd'] == [ADD_CMD]
    # the observations and objects are left untouched
    db_mock.add_obs.assert_not_called()
    db_mock.add_objects.assert_not_called()


def test_reproc_all_sketches(project_root, sketches_mock, split_mock, db_mock):

    sketches_mock.return_value = [sketch_entry('a.jpg'), sketch_entry('b.jpg')]

    add.reproc(project_root=project_root, arg_parser=arg_parser())

    assert split_mock.call_count == 2
    assert db_mock.add_sketch.call_count == 2


def test_reproc_all_commands_of_a_sketch(project_root, sketches_mock, split_mock):

    other_cmd = f'{ADD_CMD} -o2 \'Alpha UMi\''
    sketches_mock.return_value = [sketch_entry(_cmd=[ADD_CMD, other_cmd])]

    add.reproc(project_root=project_root, arg_parser=arg_parser())

    assert split_mock.call_count == 2
    assert split_mock.call_args.kwargs['second_object'] == 'Alpha UMi'


def test_reproc_single_sketch(project_root, sketches_mock, split_mock, db_mock):

    sketches_mock.return_value = [sketch_entry('a.jpg'), sketch_entry('b.jpg')]

    # the sketch is matched by file name, regardless of the path
    add.reproc(project_root=project_root,
               arg_parser=arg_parser(),
               sketch='./docs/img/b.jpg')

    split_mock.assert_called_once()
    assert db_mock.add_sketch.call_args.kwargs['full'] == 'c47-na-20260816.jpg'


def test_reproc_unknown_sketch(project_root, sketches_mock, split_mock, capsys):

    add.reproc(project_root=project_root, arg_parser=arg_parser(), sketch='no-such.jpg')

    split_mock.assert_not_called()
    assert 'No sketch found with full name no-such.jpg' in capsys.readouterr().out


def test_reproc_ambiguous_sketch(project_root, sketches_mock, split_mock, capsys):

    sketches_mock.return_value = [sketch_entry('a.jpg'), sketch_entry('a.jpg')]

    add.reproc(project_root=project_root, arg_parser=arg_parser(), sketch='a.jpg')

    split_mock.assert_not_called()
    assert 'multiple sketches found with full name a.jpg' in capsys.readouterr().out


@pytest.mark.parametrize('sketch', [sketch_entry(_cmd=[]),
                                    sketch_entry(_cmd=[REGEN_CMD]),
                                    {'full': 'c47-na-20260816.jpg'}])
def test_reproc_sketch_without_add_command(sketch,
                                           project_root,
                                           sketches_mock,
                                           split_mock,
                                           db_mock,
                                           capsys):

    sketches_mock.return_value = [sketch]

    add.reproc(project_root=project_root, arg_parser=arg_parser())

    split_mock.assert_not_called()
    db_mock.add_sketch.assert_not_called()
    assert 'Skipping, sketch has no command data' in capsys.readouterr().out


def test_reproc_continues_on_error(project_root,
                                   sketches_mock,
                                   split_mock,
                                   db_mock,
                                   capsys):

    sketches_mock.return_value = [sketch_entry('a.jpg'), sketch_entry('b.jpg')]
    split_mock.side_effect = [FileNotFoundError('./orig/cluster.jpg'), split_data()]

    add.reproc(project_root=project_root, arg_parser=arg_parser())

    # the failing sketch is reported and skipped, the next one is processed
    out = capsys.readouterr().out
    assert 'Unable to execute command' in out
    db_mock.add_sketch.assert_called_once()


def test_reproc_continues_on_malformed_command(project_root,
                                               sketches_mock,
                                               split_mock,
                                               db_mock,
                                               capsys):

    # a hand-edited command line argparse can't parse
    bad_cmd = 'astro-gen ./example add --no-such-option'
    sketches_mock.return_value = [sketch_entry('a.jpg', _cmd=[bad_cmd]),
                                  sketch_entry('b.jpg')]

    add.reproc(project_root=project_root, arg_parser=arg_parser())

    # the exit of the parser doesn't abort the run
    out = capsys.readouterr().out
    assert 'Unable to execute command' in out
    split_mock.assert_called_once()
    db_mock.add_sketch.assert_called_once()
