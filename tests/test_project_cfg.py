#!/usr/bin/env python3

from astro_gen import project_cfg

import pytest

DEFAULT_CUTOUTS = ['100%x100%']


def test_default_cutouts():

    assert project_cfg.cutouts({}) == DEFAULT_CUTOUTS
    # image settings without cutouts
    assert project_cfg.cutouts({'images': {}}) == DEFAULT_CUTOUTS


def test_default_cutouts_from_meta():

    assert project_cfg.cutouts({'images': {'cutouts': ['100%x50%']}}) == ['100%x50%']


def test_default_cutouts_empty_list_is_kept():

    # an explicitly empty list means no cutouts, not the defaults
    assert project_cfg.cutouts({'images': {'cutouts': []}}) == []


def test_default_cutouts_malformed_meta():

    with pytest.raises(AssertionError):
        project_cfg.cutouts({'images': 'no-settings-here'})
    with pytest.raises(AssertionError):
        project_cfg.cutouts({'images': {'cutouts': '100%x50%'}})
