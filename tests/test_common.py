#!/usr/bin/env python3

from astro_gen import common
from astro_gen.datatypes import Object


# to_greek()

def test_to_greek():

    assert common.to_greek('alpha') == 'α'
    assert common.to_greek('Beta') == 'β'
    assert common.to_greek('SIGMA') == 'σ'


def test_to_greek_unknown_is_kept():

    assert common.to_greek('xyz') == 'xyz'
    assert common.to_greek('') == ''


# greek_name()

def test_greek_name():

    assert common.greek_name('Alpha UMi') == 'α UMi'
    assert common.greek_name('mu Cep') == 'μ Cep'


def test_greek_name_no_greek_part():

    assert common.greek_name('Polaris Ori') == 'Polaris Ori'


def test_greek_name_only_two_word_names_are_converted():

    # a single word is not a designation
    assert common.greek_name('M31') == 'M31'
    # component designations are left alone
    assert common.greek_name('Alpha UMi A') == 'Alpha UMi A'


def test_greek_name_list():

    assert common.greek_name(['Alpha UMi', 'C47']) == ['α UMi', 'C47']
    assert common.greek_name([]) == []


# pretty_name()

def test_pretty_name_constellation_to_genitive():

    assert common.pretty_name('Alpha UMi') == 'Alpha Ursae Minoris'
    assert common.pretty_name('17 Cyg') == '17 Cygni'
    # only the last word is checked, component designations are kept as is
    assert common.pretty_name('Alpha UMi A') == 'Alpha UMi A'


def test_pretty_name_messier():

    assert common.pretty_name('M1') == 'Messier 1'
    assert common.pretty_name('M31') == 'Messier 31'
    assert common.pretty_name('M110') == 'Messier 110'
    # more than 3 digits is not a Messier object
    assert common.pretty_name('M1234') == 'M1234'


def test_pretty_name_unknown_is_kept():

    assert common.pretty_name('C47') == 'C47'
    assert common.pretty_name('Archimedes') == 'Archimedes'


def test_pretty_name_list():

    assert common.pretty_name(['C47', 'M31']) == ['C47', 'Messier 31']


# names_to_list()

def test_names_to_list():

    assert common.names_to_list('C47') == ['C47']
    assert common.names_to_list('C47, Alpha UMi') == ['C47', 'Alpha UMi']
    # separator without space works too
    assert common.names_to_list('C47,Alpha UMi') == ['C47', 'Alpha UMi']


# traditional_name()

def test_traditional_name_greek():

    assert common.traditional_name('Alpha UMi') == 'α UMi'


def test_traditional_name_struve():

    assert common.traditional_name('STF 1234') == 'Σ 1234'
    assert common.traditional_name('STFA 1') == 'Σ I 1'
    assert common.traditional_name('STFB 1') == 'Σ II 1'
    assert common.traditional_name('STT 500') == 'OΣ 500'
    assert common.traditional_name('STTA 5') == 'OΣΣ 5'


def test_traditional_name_struve_variants():

    # the space is optional
    assert common.traditional_name('STF1234') == 'Σ 1234'
    # matching is case insensitive, the result is upper case
    assert common.traditional_name('stf 1234') == 'Σ 1234'
    # components are kept
    assert common.traditional_name('STF 1234 AB') == 'Σ 1234 AB'
    assert common.traditional_name('STF 1234 A,B') == 'Σ 1234 A,B'


def test_traditional_name_unknown_is_kept():

    assert common.traditional_name('C47') == 'C47'
    # 'ST?' prefixes without a known designation are kept as is
    assert common.traditional_name('stx 5') == 'stx 5'


def test_traditional_name_list():

    assert common.traditional_name(['Alpha UMi', 'STF 1234', 'C47']) == \
        ['α UMi', 'Σ 1234', 'C47']


# pretty_name_str()

def test_pretty_name_str():

    assert common.pretty_name_str('M31') == 'Messier 31'


def test_pretty_name_str_list_is_joined():

    assert common.pretty_name_str(['C47', 'Alpha UMi']) == 'C47, Alpha Ursae Minoris'


# short_desc()

def test_short_desc_with_constellation():

    obj = Object(name='C47', constellation='Del', type='globular cluster')
    assert common.short_desc(obj) == 'globular cluster in Delphinus'


def test_short_desc_with_other_location():

    obj = Object(name='Archimedes', constellation='Moon', type='crater')
    assert common.short_desc(obj) == 'crater in Moon'


def test_short_desc_missing_data():

    assert common.short_desc(Object()) == ''
    assert common.short_desc(Object(type='globular cluster')) == 'globular cluster'


# md_link() / md_image()

def test_md_link():

    assert common.md_link('C47', './c47.md') == '[C47](./c47.md)'


def test_md_link_with_desc():

    assert common.md_link('C47', './c47.md', 'Globular cluster') == \
        '[C47](./c47.md "Globular cluster")'


def test_md_image():

    assert common.md_image('C47', './c47.jpg') == '![C47](./c47.jpg)'
    assert common.md_image('C47', './c47.jpg', 'Sketch') == '![C47](./c47.jpg "Sketch")'


# name_slug()

def test_name_slug():

    assert common.name_slug('Alpha UMi') == 'alpha-umi'
    assert common.name_slug('C47') == 'c47'


def test_name_slug_list():

    assert common.name_slug(['C47', 'Alpha UMi']) == 'c47-alpha-umi'


def test_name_slug_transliterates():

    assert common.name_slug('α UMi') == 'a-umi'


# file_basename() and friends

def test_file_basename():

    assert common.file_basename('C47', '2026-08-16') == 'c47-2026-08-16'
    assert common.file_basename(['C47', 'Alpha UMi'], '2026-08-16') == \
        'c47-alpha-umi-2026-08-16'


def test_file_basename_with_time():

    assert common.file_basename('C47', '2026-08-16 23:30') == 'c47-2026-08-16-23-30'


def test_sketch_name():

    assert common.sketch_name('C47', '2026-08-16') == 'c47-2026-08-16.jpg'


def test_obs_page_name():

    assert common.obs_page_name(['C47', 'Alpha UMi'], '2026-08-16') == \
        'c47-alpha-umi-2026-08-16.md'


# obs_day()

def test_obs_day_without_time():

    assert common.obs_day('2026-08-16') == '2026-08-16'


def test_obs_day_before_midnight():

    assert common.obs_day('2026-08-16 23:30') == '2026-08-16'
    assert common.obs_day('2026-08-16T12:00') == '2026-08-16'


def test_obs_day_after_midnight():

    assert common.obs_day('2026-08-17 00:15') == '2026-08-16'
    assert common.obs_day('2026-08-17 11:59') == '2026-08-16'


# get_constellation()

def test_get_constellation():

    assert common.get_constellation('Alpha UMi') == 'UMi'


def test_get_constellation_none():

    # no constellation in the name
    assert common.get_constellation('Alpha Polaris') == ''
    # a bare constellation id is not a designation
    assert common.get_constellation('UMi') == ''
    assert common.get_constellation('C47') == ''
    assert common.get_constellation('') == ''
