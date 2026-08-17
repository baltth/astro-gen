#!/usr/bin/env python3

from astro_gen import pages
from astro_gen.datatypes import Object, ObjectData, ObsData

from typing import List


def col_of(data: List[str]) -> List[str]:
    """Trivial `make_col` for md_table(): the data item is the column itself."""
    return list(data)


# emph()

def test_emph():

    assert pages.emph('C47') == '_C47_'


# md_table()

def test_md_table():

    tab = pages.md_table([['1', '2'], ['3', '4']], col_of, ['A', 'B'])
    assert tab == [
        'A | 1 | 3',
        '-|-|-',
        'B | 2 | 4',
        ''
    ]


def test_md_table_drops_empty_columns():

    # the first cell of a column is its 'header', it doesn't make the column non-empty
    tab = pages.md_table([['1', '2'], ['3', '']], col_of, ['A', 'B'])
    assert tab == [
        'A | 1',
        '-|-',
        'B | 2',
        ''
    ]


def test_md_table_drops_empty_rows():

    tab = pages.md_table([['1', '', '3']], col_of, ['A', 'B', 'C'])
    assert tab == [
        'A | 1',
        '-|-',
        'C | 3',
        ''
    ]


def test_md_table_no_data_is_no_table():

    # no columns at all
    assert pages.md_table([], col_of, ['A', 'B']) == []
    # all columns empty
    assert pages.md_table([['1', '']], col_of, ['A', 'B']) == []
    # only the column header row remains
    assert pages.md_table([['1']], col_of, ['A']) == []
    # the column header row is empty, only the row headers would remain
    assert pages.md_table([['', 'x']], col_of, ['A', 'B']) == []


def test_md_table_normalizes_cells():

    # line breaks would break the markdown table
    tab = pages.md_table([['x', 'a\nb  ']], col_of, ['A', 'B'])
    assert tab[2] == 'B | a b'


def test_md_table_empty_cell_placeholder():

    # the placeholder keeps a row alive, it's rendered as a space
    tab = pages.md_table([['x', pages.EMPTY_CELL_PLACEHOLDER]], col_of, ['A', 'B'])
    assert tab[2] == 'B |  '


# obs_table()

def test_obs_table():

    data = ObsData(names=['C47'], date='2026-08-16 23:30', loc='Apajpuszta',
                   nelm=5.2, seeing=8, ap=150, mag=120, fov='0.6')
    assert pages.obs_table(data) == [
        'Object | C47',
        '-|-',
        'Observed at | Apajpuszta, 2026-08-16 23:30',
        'NELM | ~ 5.2',
        'Seeing | 8',
        'Aperture | 150 mm',
        'Magnification | 120x',
        'FOV | 0.6°',
        ''
    ]


def test_obs_table_multiple_names():

    data = ObsData(names=['C47', 'Alpha UMi'], date='2026-08-16', loc='Apajpuszta')
    tab = pages.obs_table(data)
    assert tab[0] == 'Objects | C47, Alpha Ursae Minoris'


def test_obs_table_missing_data_is_dropped():

    data = ObsData(names=['C47'], date='2026-08-16', loc='Apajpuszta')
    assert pages.obs_table(data) == [
        'Object | C47',
        '-|-',
        'Observed at | Apajpuszta, 2026-08-16',
        ''
    ]


def test_obs_table_fov_degrees():

    def fov_of(fov: str) -> str:
        tab = pages.obs_table(ObsData(names=['C47'], date='d', loc='l', fov=fov))
        return tab[-2]

    # a bare number gets the degree sign
    assert fov_of('0.6') == 'FOV | 0.6°'
    assert fov_of('0.6 ') == 'FOV | 0.6°'
    # an unit is already present, keep as is
    assert fov_of('1 deg') == 'FOV | 1 deg'
    assert fov_of("30'") == "FOV | 30'"


def test_obs_table_custom_data():

    data = ObsData(names=['C47'], date='2026-08-16', loc='Apajpuszta',
                   data={'PA': '~150°'})
    assert pages.obs_table(data) == [
        'Object | C47',
        '-|-',
        'Observed at | Apajpuszta, 2026-08-16',
        '**Other data** |  ',
        'PA | ~150°',
        ''
    ]


# mark_fetched()

def test_mark_fetched():

    assert pages.mark_fetched('Star') == 'Star ' + pages.DATA_NOTE
    assert pages.mark_fetched('') == ''


# get_annotated_data()

def test_get_annotated_data_marks_fetched_fields():

    obj = Object(name='Alpha UMi',
                 components={'Alpha UMi A': ObjectData(name='HD 8890', desc='Binary')},
                 fetched={'HD 8890': ObjectData(type='Star', ra='02h 31m 47s')})

    data = pages.get_annotated_data(obj)
    comp = data['Alpha UMi A']
    # values coming from the fetched data are marked
    assert comp['type'] == 'Star ' + pages.DATA_NOTE
    assert comp['ra'] == '02h 31m 47s ' + pages.DATA_NOTE
    # user-defined values are untouched
    assert comp['desc'] == 'Binary'


# merge_general_data()

def test_merge_general_data_single_entry_is_renamed():

    assert pages.merge_general_data({'_': {'a': 'x'}}, 'C47') == {'C47': {'a': 'x'}}


def test_merge_general_data_merged_to_matching_name():

    # the general data is the last entry, see get_all_data_of()
    data = {'C47': {'a': '', 'b': 'y'},
            'Other': {},
            '_': {'a': 'x', 'b': ''}}
    assert pages.merge_general_data(data, 'C47') == {'C47': {'a': 'x', 'b': 'y'},
                                                     'Other': {}}


def test_merge_general_data_merged_to_first_entry():

    # the object name is not among the keys, the first entry is used
    data = {'First': {'a': ''},
            'Second': {'a': ''},
            '_': {'a': 'x'}}
    assert pages.merge_general_data(data, 'C47') == {'First': {'a': 'x'},
                                                     'Second': {'a': ''}}


def test_merge_general_data_existing_values_are_kept():

    data = {'C47': {'a': 'own'}, '_': {'a': 'general'}}
    assert pages.merge_general_data(data, 'C47') == {'C47': {'a': 'own'}}


def test_merge_general_data_no_general_entry():

    data = {'C47': {'a': 'x'}}
    assert pages.merge_general_data(data, 'C47') == data


# make_desc_from_types()

def test_make_desc_from_types():

    assert pages.make_desc_from_types({'type': 'Star',
                                       'subtype': 'Main Sequence Supergiant'}) == \
        'Main sequence supergiant star'


def test_make_desc_from_types_cluster_is_not_repeated():

    assert pages.make_desc_from_types({'type': 'Open Cluster',
                                       'subtype': 'Medium sized cluster'}) == \
        'Medium sized cluster'


def test_make_desc_from_types_equal_type_and_subtype():

    assert pages.make_desc_from_types({'type': 'star', 'subtype': 'star'}) == 'Star'


def test_make_desc_from_types_partial_data():

    assert pages.make_desc_from_types({'type': 'Star'}) == 'Star'
    # the missing type leaves a trailing space, it's normalized by md_table()
    assert pages.make_desc_from_types({'subtype': 'Spiral galaxy'}).strip() == 'Spiral galaxy'


def test_make_desc_from_types_no_data():

    assert pages.make_desc_from_types({}) == ''
    assert pages.make_desc_from_types({'desc': 'Globular cluster'}) == ''


# preprocess_data()

def test_preprocess_data():

    obj = Object(name='C47', constellation='Del', type='globular cluster',
                 desc='Globular cluster', data={'size': '12\''})

    assert pages.preprocess_data(obj) == {
        'C47': {
            'pretty_name': 'C47',
            'desc': 'Globular cluster',
            'ra': '',
            'dec': '',
            'mag': '',
            'spectral_class': '',
            'size': '12\''
        }
    }


def test_preprocess_data_desc_is_generated_from_types():

    obj = Object(name='Archimedes', constellation='Moon', type='crater')
    assert pages.preprocess_data(obj)['Archimedes']['desc'] == 'Crater'


def test_preprocess_data_generated_desc_is_marked_when_fetched():

    obj = Object(name='HD 8890',
                 fetched={'HD 8890': ObjectData(type='Star',
                                                subtype='Main Sequence Supergiant')})
    desc = pages.preprocess_data(obj)['HD 8890']['desc']
    # the mark is moved to the end of the composed description
    assert desc == 'Main sequence supergiant star ' + pages.DATA_NOTE


def test_preprocess_data_components():

    obj = Object(name='Alpha UMi', constellation='UMi', type='double star',
                 components={'Alpha UMi A': ObjectData(name='HD 8890', desc='Binary'),
                             '~ B': ObjectData(desc='Main sequence star')})

    data = pages.preprocess_data(obj)
    assert list(data.keys()) == ['Alpha UMi A', 'Alpha UMi B']
    # a differing component name is kept as the fetched name
    assert data['Alpha UMi A']['fetched_name'] == 'HD 8890'
    assert data['Alpha UMi B']['pretty_name'] == 'Alpha UMi B'


def test_preprocess_data_administrative_keys_are_removed():

    obj = Object(name='C47', constellation='Del', type='globular cluster',
                 subtype='globular cluster')

    data = pages.preprocess_data(obj)['C47']
    for k in ['name', 'type', 'subtype', 'constellation', 'fetched_keys']:
        assert k not in data.keys()


# obj_table()

def test_obj_table():

    obj = Object(name='Alpha UMi', constellation='UMi', type='double star',
                 components={'Alpha UMi A': ObjectData(name='HD 8890',
                                                       desc='Binary',
                                                       spectral_class='F7Ib + F6V'),
                             '~ B': ObjectData(desc='Main sequence star')},
                 fetched={'HD 8890': ObjectData(ra='02h 31m 47s')})

    assert pages.obj_table([obj]) == [
        'Objects | Alpha UMi A | Alpha UMi B',
        '-|-|-',
        'Fetched as | HD 8890 | ',
        'Desc. | Binary | Main sequence star',
        'RA | 02h 31m 47s ' + pages.DATA_NOTE + ' | ',
        'Spectral class | F7Ib + F6V | ',
        '',
        f'{pages.DATA_NOTE} fetched from [astronomyapi.com](http://astronomyapi.com)',
        ''
    ]


def test_obj_table_single_object():

    obj = Object(name='Archimedes', constellation='Moon', type='crater',
                 data={'size': '81 km'})
    assert pages.obj_table([obj]) == [
        'Object | Archimedes',
        '-|-',
        'Desc. | Crater',
        'Size | 81 km',
        ''
    ]


def test_obj_table_multiple_objects():

    objects = [
        Object(name='C47', constellation='Del', type='globular cluster', mag='8.9'),
        Object(name='Archimedes', constellation='Moon', type='crater', data={'size': '81 km'})
    ]
    assert pages.obj_table(objects) == [
        'Objects | C47 | Archimedes',
        '-|-|-',
        'Desc. | Globular cluster | Crater',
        'Magnitude | 8.9 | ',
        'Size |  | 81 km',
        ''
    ]


def test_obj_table_name_and_desc_only_is_no_table():

    # such a table would carry no more info than the tag line
    obj = Object(name='C47', constellation='Del', type='globular cluster',
                 desc='Globular cluster')
    assert pages.obj_table([obj]) == []


def test_obj_table_no_data():

    assert pages.obj_table([]) == []


def test_obj_table_no_fetch_note_without_fetched_data():

    obj = Object(name='C47', constellation='Del', type='globular cluster', mag='8.9')
    tab = pages.obj_table([obj])
    assert not any(pages.DATA_NOTE in row for row in tab)


# tag_line()

def test_tag_line():

    obj = Object(name='Alpha UMi', constellation='UMi', type='double star',
                 aka=['Polaris'])
    assert pages.tag_line('Alpha UMi', obj) == \
        '_Alpha UMi_ -- _α UMi_ -- _Polaris_ -- _Double star in Ursa Minor_'


def test_tag_line_name_is_added_before_desc():

    # the name is not repeated as the title shows it as is
    obj = Object(name='C47', constellation='Del', type='globular cluster')
    assert pages.tag_line('C47', obj) == '_C47_ -- _Globular cluster in Delphinus_'


def test_tag_line_names_only():

    assert pages.tag_line('STF 1234', Object()) == '_Σ 1234_'


def test_tag_line_no_data():

    assert pages.tag_line('C47', Object()) == ''


# subtitle() / fetch_subtitle()

def test_subtitle():

    assert pages.subtitle('Links') == '## Links'
    assert pages.subtitle('Object data', level=4) == '#### Object data'


def test_fetch_subtitle():

    assert pages.fetch_subtitle('## Object data') == (2, 'Object data')
    assert pages.fetch_subtitle('  #### Links  ') == (4, 'Links')


def test_fetch_subtitle_no_subtitle():

    assert pages.fetch_subtitle('plain text') == (0, 'plain text')
    assert pages.fetch_subtitle('') == (0, '')


# header()

def test_header():

    assert pages.header('C47', links={}) == [
        '# C47',
        '',
        '[Main page](../index.md) -- [Index](../pages/obj_index.md)',
        ''
    ]


def test_header_with_links():

    md = pages.header('C47', links={'Scan': '../scan/s.jpg'})
    assert md[2].endswith(' -- [Scan](../scan/s.jpg)')


# note_block()

def test_note_block():

    assert pages.note_block('line1\nline2') == ['> line1', '> line2', '']


# footer()

def test_footer_empty():

    assert pages.footer() == []


def test_footer_notes():

    assert pages.footer(notes='note') == ['> note', '']


def test_footer_links():

    assert pages.footer(links={'Ref': 'http://x'}) == [
        '## Links',
        '',
        '- [Ref](http://x)'
    ]


# join()

def test_join():

    assert pages.join(['a', 'b']) == 'a\nb\n'


# table_of_contents()

def test_table_of_contents():

    content = ['# Title', '## First', 'text', '### Second one', '#### Third']
    assert pages.table_of_contents(content, max_level=3) == [
        '- [First](#first)',
        ' - [Second one](#second-one)'
    ]


def test_table_of_contents_default_level():

    content = ['## First', '### Second']
    assert pages.table_of_contents(content) == ['- [First](#first)']


def test_table_of_contents_no_subtitles():

    assert pages.table_of_contents(['text', '# Title']) == []


# page()

def test_page():

    md = pages.page(title='C47',
                    content=['content', ''],
                    notes='note',
                    nav_links={'Scan': '../scan/s.jpg'},
                    content_links={'Ref': 'http://x'})

    assert md == pages.join([
        '# C47',
        '',
        '[Main page](../index.md) -- [Index](../pages/obj_index.md) -- [Scan](../scan/s.jpg)',
        '',
        'content',
        '',
        '> note',
        '',
        '## Links',
        '',
        '- [Ref](http://x)'
    ])


def test_page_toc_is_added_for_long_content():

    content = ['## First'] + ['text'] * 100 + ['## Second']
    md = pages.page(title='Index', content=content, toc_level=2)

    assert '- [First](#first)' in md.splitlines()
    assert '- [Second](#second)' in md.splitlines()


def test_page_no_toc_for_short_content():

    content = ['## First', 'text', '## Second']
    md = pages.page(title='Index', content=content, toc_level=2)

    assert '- [First](#first)' not in md.splitlines()


def test_page_no_toc_by_default():

    content = ['## First'] + ['text'] * 100 + ['## Second']
    md = pages.page(title='Index', content=content)

    assert '- [First](#first)' not in md.splitlines()


def test_page_no_toc_for_single_subtitle():

    content = ['## First'] + ['text'] * 100
    md = pages.page(title='Index', content=content, toc_level=2)

    assert '- [First](#first)' not in md.splitlines()


# obs_body()

def test_obs_body():

    md = pages.obs_body(title='C47',
                        names=['C47'],
                        img='../img/c47.jpg',
                        obs_tab=['Object | C47', '-|-', ''],
                        text='[observation notes]',
                        object_data={'C47': Object(name='C47',
                                                   constellation='Del',
                                                   type='globular cluster',
                                                   desc='Globular cluster')},
                        sketch_notes='[sketch notes]')

    assert md == [
        '_C47_ -- _Globular cluster in Delphinus_  ',
        '',
        '![C47](../img/c47.jpg)',
        '',
        '[observation notes]',
        '',
        'Object | C47',
        '-|-',
        '',
        '',
        '> [sketch notes]',
        ''
    ]


def test_obs_body_optional_parts_are_skipped():

    md = pages.obs_body(title='C47',
                        names=['C47'],
                        img='../img/c47.jpg',
                        obs_tab=[],
                        text='',
                        object_data={},
                        sketch_notes='')

    assert md == [
        '  ',      # no tags for the unknown object, the line break remains
        '',
        '![C47](../img/c47.jpg)',
        '',
        ''
    ]


def test_obs_body_with_object_table():

    obj = Object(name='Archimedes', constellation='Moon', type='crater',
                 data={'size': '81 km'})
    md = pages.obs_body(title='Archimedes',
                        names=['Archimedes'],
                        img='../img/archimedes.jpg',
                        obs_tab=[],
                        text='',
                        object_data={'Archimedes': obj},
                        sketch_notes='')

    assert '#### Object data' in md
    assert md[md.index('#### Object data') + 2] == 'Object | Archimedes'
    assert md[-1] == ''


# log_row()

def test_log_row():

    assert pages.log_row(['C47', 'Alpha UMi'], '2026-08-16') == [
        '2026-08-16:',
        'C47, Alpha Ursae Minoris',
        '../obs/c47-alpha-umi-2026-08-16.md',
        ''
    ]


def test_log_row_from_main():

    row = pages.log_row('C47', '2026-08-16', from_main=True)
    assert row[2] == 'obs/c47-2026-08-16.md'


# index_row()

def test_index_row():

    obj = Object(name='C47', constellation='Del', type='globular cluster')
    assert pages.index_row('C47', ['C47', 'Alpha UMi'], '2026-08-16', obj) == [
        '',
        'C47',
        '../obs/c47-alpha-umi-2026-08-16.md',
        '- globular cluster in Delphinus'
    ]


# index_data()

def test_index_data_list():

    data = [pages.log_row('C47', '2026-08-16')]
    assert pages.index_data(data) == ['- 2026-08-16: [C47](../obs/c47-2026-08-16.md)']


def test_index_data_plain_text_item():

    assert pages.index_data([['just text']]) == ['- just text']


def test_index_data_dict_is_grouped():

    data = {'Delphinus': [pages.index_row('C47', 'C47', '2026-08-16',
                                          Object(type='globular cluster'))]}
    assert pages.index_data(data) == [
        '#### Delphinus',
        '',
        '- [C47](../obs/c47-2026-08-16.md) - globular cluster',
        ''
    ]


# observation_page()

def test_observation_page():

    obs = ObsData(names=['C47'], img='c47.jpg', date='2026-08-16 23:30',
                  loc='Apajpuszta', ap=150, mag=120, text='[observation notes]')
    obj = Object(name='C47', constellation='Del', type='globular cluster',
                 desc='Globular cluster')

    md = pages.observation_page(obs,
                                img='../img/c47.jpg',
                                notes='[sketch notes]',
                                nav_links={'Scan': '../scan/s.jpg'},
                                content_links={'Ref': 'http://x'},
                                object_data={'C47': obj})

    assert md == pages.join([
        '# C47',
        '',
        '[Main page](../index.md) -- [Index](../pages/obj_index.md) -- [Scan](../scan/s.jpg)',
        '',
        '_C47_ -- _Globular cluster in Delphinus_  ',
        '',
        '![C47](../img/c47.jpg)',
        '',
        '[observation notes]',
        '',
        'Object | C47',
        '-|-',
        'Observed at | Apajpuszta, 2026-08-16 23:30',
        'Aperture | 150 mm',
        'Magnification | 120x',
        '',
        '',
        '> [sketch notes]',
        '',
        '## Links',
        '',
        '- [Ref](http://x)'
    ])


def test_observation_page_title_of_multiple_objects():

    obs = ObsData(names=['C47', 'Alpha UMi'], date='2026-08-16', loc='Apajpuszta')
    md = pages.observation_page(obs, img='../img/x.jpg')
    assert md.startswith('# C47, Alpha Ursae Minoris\n')


# index_page()

def test_index_page():

    data = {'Delphinus': [pages.index_row('C47', 'C47', '2026-08-16',
                                          Object(type='globular cluster'))]}
    md = pages.index_page('Index', data, notes='[notes]', links={'Ref': 'http://x'})

    assert md == pages.join([
        '# Index',
        '',
        '[Main page](../index.md) -- [Index](../pages/obj_index.md)',
        '',
        '#### Delphinus',
        '',
        '- [C47](../obs/c47-2026-08-16.md) - globular cluster',
        '',
        '> [notes]',
        '',
        '## Links',
        '',
        '- [Ref](http://x)'
    ])
