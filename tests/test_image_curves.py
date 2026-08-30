#!/usr/bin/env python3

from astro_gen import image_curves
from astro_gen.image_curves import Curves, CURVE_LEN

from PIL import Image
from PIL.Image import Image as ImageT
from typing import List, Tuple
import pytest

LINEAR_LUT = list(range(CURVE_LEN))


def samples() -> List[float]:
    """The normalized sample points of a populated curve."""
    return [x / CURVE_LEN for x in range(CURVE_LEN)]


def inverting_xy_curve() -> List[Tuple[float, float]]:
    """A full length inverting curve as a list of points."""
    return list(zip(samples(), reversed(samples())))


def image_of(pixels: List[Tuple[int, int, int]]) -> ImageT:
    """An 1 pixel high RGB image of the given pixels."""
    img = Image.new(mode='RGB', size=(len(pixels), 1))
    img.putdata(pixels)
    return img


# Curves.linear()

def test_curves_linear():

    assert image_curves.populate(Curves.linear()) == LINEAR_LUT


# Curves.invert()

def test_curves_invert():

    assert image_curves.populate(Curves.invert()) == list(reversed(LINEAR_LUT))


def test_curves_invert_is_its_own_inverse():

    inv = Curves.invert()
    assert inv(inv(0.0)) == pytest.approx(0.0)
    assert inv(inv(0.5)) == pytest.approx(0.5)


# Curves.highlights()

def test_curves_highlights_zero_strength_is_linear():

    assert image_curves.populate(Curves.highlights(0)) == LINEAR_LUT


def test_curves_highlights_positive_brightens():

    lut = image_curves.populate(Curves.highlights(1.0))
    assert all(v >= lin for v, lin in zip(lut, LINEAR_LUT))
    assert any(v > lin for v, lin in zip(lut, LINEAR_LUT))
    # the ends are pinned by the mask
    assert lut[0] == 0
    assert lut[-1] == CURVE_LEN - 1


def test_curves_highlights_negative_darkens_the_highlights_only():

    lut = image_curves.populate(Curves.highlights(-1.0))
    # below a specific threshold the curve is untouched
    assert lut[:70] == LINEAR_LUT[:70]
    assert all(v <= lin for v, lin in zip(lut, LINEAR_LUT))
    assert any(v < lin for v, lin in zip(lut, LINEAR_LUT))


def test_curves_highlights_strength_is_limited():

    with pytest.raises(AssertionError):
        Curves.highlights(1.5)
    with pytest.raises(AssertionError):
        Curves.highlights(-1.5)


def test_curves_highlights_input_is_limited():

    with pytest.raises(AssertionError):
        Curves.highlights(0.5)(1.5)
    with pytest.raises(AssertionError):
        Curves.highlights(-0.5)(-0.5)


# Curves.shadows()

def test_curves_shadows_zero_strength_is_linear():

    assert image_curves.populate(Curves.shadows(0)) == LINEAR_LUT


def test_curves_shadows_positive_brightens_the_shadows_only():

    lut = image_curves.populate(Curves.shadows(1.0))
    # above a specific threshold the curve is untouched
    assert lut[180:] == LINEAR_LUT[180:]
    assert all(v >= lin for v, lin in zip(lut, LINEAR_LUT))
    assert any(v > lin for v, lin in zip(lut, LINEAR_LUT))


def test_curves_shadows_negative_darkens():

    lut = image_curves.populate(Curves.shadows(-1.0))
    assert all(v <= lin for v, lin in zip(lut, LINEAR_LUT))
    assert any(v < lin for v, lin in zip(lut, LINEAR_LUT))
    # the ends are pinned by the mask
    assert lut[0] == 0
    assert lut[-1] == CURVE_LEN - 1


def test_curves_shadows_strength_is_limited():

    with pytest.raises(AssertionError):
        Curves.shadows(1.5)
    with pytest.raises(AssertionError):
        Curves.shadows(-1.5)


def test_curves_shadows_input_is_limited():

    with pytest.raises(AssertionError):
        Curves.shadows(0.5)(1.5)
    with pytest.raises(AssertionError):
        Curves.shadows(-0.5)(-0.5)


# Curves.ambient()

def test_curves_ambient_zero_strength_is_linear():

    assert image_curves.populate(Curves.ambient(0)) == LINEAR_LUT


def test_curves_ambient_positive_lifts_the_darks_and_pulls_the_lights():

    lut = image_curves.populate(Curves.ambient(1.0))
    assert lut[64] > LINEAR_LUT[64]
    assert lut[192] < LINEAR_LUT[192]
    # the ends are pinned by the mask
    assert lut[0] == 0
    assert lut[-1] == CURVE_LEN - 1


def test_curves_ambient_negative_is_the_opposite():

    lut = image_curves.populate(Curves.ambient(-1.0))
    assert lut[64] < LINEAR_LUT[64]
    assert lut[192] > LINEAR_LUT[192]


def test_curves_ambient_strength_is_limited():

    with pytest.raises(AssertionError):
        Curves.ambient(1.5)
    with pytest.raises(AssertionError):
        Curves.ambient(-1.5)


def test_curves_ambient_input_is_limited():

    with pytest.raises(AssertionError):
        Curves.ambient(0.5)(1.5)


# Curves._mask()

def test_curves_mask():

    # the mask fades out the adjustment at both ends
    assert Curves._mask(0.0) == pytest.approx(0.0, abs=1e-6)
    assert Curves._mask(1.0) == pytest.approx(0.0, abs=1e-6)
    assert Curves._mask(0.5) == pytest.approx(1.0)
    assert Curves._mask(0.25) == pytest.approx(Curves._mask(0.75))


# Curves.combine()

def test_curves_combine_single_curve_is_returned_as_is():

    c = Curves.linear()
    assert Curves.combine(c) is c


def test_curves_combine_applies_the_curves_in_order():

    half = (lambda x: x / 2)
    lift = (lambda x: x + 0.25)

    assert Curves.combine(half, lift)(0.5) == pytest.approx(0.5)
    assert Curves.combine(lift, half)(0.5) == pytest.approx(0.375)


def test_curves_combine_more_than_two_curves():

    lift = (lambda x: x + 0.1)
    assert Curves.combine(lift, lift, lift)(0.1) == pytest.approx(0.4)


def test_curves_combine_inverse_pair_is_linear():

    c = Curves.combine(Curves.invert(), Curves.invert())
    assert image_curves.populate(c) == LINEAR_LUT


# is_normal_range()

def test_is_normal_range():

    assert image_curves.is_normal_range([0.0, 0.5, 1.0])
    assert not image_curves.is_normal_range([0, 128, 255])


def test_is_normal_range_threshold():

    assert image_curves.is_normal_range([1.09])
    assert not image_curves.is_normal_range([1.1])


def test_is_normal_range_empty():

    assert not image_curves.is_normal_range([])


def test_is_normal_range_of_points_checks_the_x_values():

    assert image_curves.is_normal_range([(0.0, 0.0), (1.0, 1.0)])
    assert not image_curves.is_normal_range([(0, 0), (255, 255)])
    # only the x coordinates matter
    assert image_curves.is_normal_range([(0.0, 0.0), (1.0, 255.0)])


# _clamp()

def test_clamp():

    assert image_curves._clamp(0, -1, 10) == 0
    assert image_curves._clamp(0, 5, 10) == 5
    assert image_curves._clamp(0, 50, 10) == 10


# normalize()

def test_normalize():

    assert image_curves.normalize([0, 128, 256]) == [0.0, 0.5, 1.0]


def test_normalize_clamps_to_the_normal_range():

    assert image_curves.normalize([-256, 512]) == [0.0, 1.0]


def test_normalize_normalized_input_is_kept():

    lut = [0.0, 0.5, 1.0]
    assert image_curves.normalize(lut) == lut


# denormalize()

def test_denormalize():

    assert image_curves.denormalize([0.0, 0.5, 1.0]) == [0, 128, CURVE_LEN - 1]


def test_denormalize_rounds_to_the_nearest():

    assert image_curves.denormalize([1 / 512, 0.9 / CURVE_LEN]) == [1, 1]


def test_denormalize_denormalized_input_is_kept():

    lut = [0, 128, 255]
    assert image_curves.denormalize(lut) == lut


# _interpol()

def test_interpol():

    lut = image_curves._interpol([(0.0, 0.0), (1.0, 1.0)], samples=[0.0, 0.25, 1.0])
    assert list(lut) == pytest.approx([0.0, 0.25, 1.0])


def test_interpol_outside_the_curve_is_flat():

    lut = image_curves._interpol([(0.25, 0.5), (0.75, 1.0)], samples=[0.0, -1.0, 2.0])
    assert list(lut) == pytest.approx([0.5, 0.5, 1.0])


# _sample_range_of()

def test_sample_range_of():

    assert list(image_curves._sample_range_of([(0.0, 0.0), (1.0, 1.0)])) == samples()
    assert list(image_curves._sample_range_of([(0, 0), (255, 255)])) == LINEAR_LUT


# _populate_from_xy()

def test_populate_from_xy():

    lut = image_curves._populate_from_xy([(0.0, 0.0), (1.0, 1.0)])
    assert list(lut) == pytest.approx(samples())


def test_populate_from_xy_denormalized_points():

    lut = image_curves._populate_from_xy([(0, 0), (255, 255)])
    assert list(lut) == pytest.approx(LINEAR_LUT)


def test_populate_from_xy_points_are_sorted():

    lut = image_curves._populate_from_xy([(1.0, 1.0), (0.0, 0.0)])
    assert list(lut) == pytest.approx(samples())


def test_populate_from_xy_full_length_curve_is_taken_as_is():

    c = [(x, 0.5) for x in samples()]
    assert image_curves._populate_from_xy(c) == [0.5] * CURVE_LEN


def test_populate_from_xy_needs_at_least_two_points():

    with pytest.raises(AssertionError):
        image_curves._populate_from_xy([(0.0, 0.0)])


def test_populate_from_xy_x_values_shall_be_unique():

    with pytest.raises(AssertionError):
        image_curves._populate_from_xy([(0.0, 0.0), (0.0, 1.0)])


# _populate_from_func()

def test_populate_from_func():

    assert image_curves._populate_from_func(Curves.linear()) == pytest.approx(samples())


# populate_curve_xy()

def test_populate_curve_xy():

    c = list(image_curves.populate_curve_xy([(0.0, 0.0), (1.0, 1.0)]))
    assert len(c) == CURVE_LEN
    assert [p[0] for p in c] == samples()
    assert [p[1] for p in c] == pytest.approx(samples())


def test_populate_curve_xy_needs_points():

    with pytest.raises(AssertionError):
        image_curves.populate_curve_xy(Curves.linear())


# populate()

def test_populate_of_func():

    assert image_curves.populate(Curves.linear()) == LINEAR_LUT


def test_populate_of_full_length_xy_curve():

    assert image_curves.populate(inverting_xy_curve()) == list(reversed(LINEAR_LUT))


def test_populate_of_xy_curve():

    assert image_curves.populate([(0.0, 0.0), (1.0, 1.0)]) == LINEAR_LUT


# apply()

def test_apply_linear_keeps_the_image():

    img = image_of([(0, 0, 0), (10, 20, 30), (255, 255, 255)])
    res = image_curves.apply(img, Curves.linear())
    assert list(res.getdata()) == list(img.getdata())


def test_apply_curve_is_used_for_all_channels():

    img = image_of([(0, 10, 255)])
    res = image_curves.apply(img, Curves.invert())
    assert list(res.getdata()) == [(255, 245, 0)]


def test_apply_keeps_the_input_image():

    img = image_of([(10, 20, 30)])
    res = image_curves.apply(img, Curves.invert())
    assert list(img.getdata()) == [(10, 20, 30)]
    assert res.mode == img.mode
    assert res.size == img.size


def test_apply_of_xy_curve():

    img = image_of([(0, 10, 255)])
    res = image_curves.apply(img, inverting_xy_curve())
    assert list(res.getdata()) == [(255, 245, 0)]


def test_apply_needs_an_rgb_image():

    with pytest.raises(ValueError):
        image_curves.apply(image_of([(10, 20, 30)]).convert(mode='L'), Curves.linear())
