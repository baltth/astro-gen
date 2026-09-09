#!/usr/bin/env python3

from argparse import ArgumentParser
from typing import Tuple, List, Callable, Optional, Union
from math import sin, sqrt, floor, pi
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image, ImageChops, ImageDraw
from PIL.Image import Image as ImageT

CURVE_LEN = 256
MAX_LEVEL = CURVE_LEN - 1

# Rec. 709 luminance weights, summing up to exactly 1.0
LUMA_WEIGHTS = (0.2126, 0.7152, 0.0722)

# Luminance below this level fades the gain over to a plain offset,
# see _apply_to_luminance()
GAIN_FADE_LEVEL = 8.0

EPSILON = 1e-6

CurveXY = List[Tuple[float, float]]
CurveFunc = Callable[[float], float]
Curve = Union[CurveXY, CurveFunc]

LookupTable = List[float]

# A per pixel weight of an adjustment: an 'L' image or an integer array
# holds levels of [0, MAX_LEVEL], a float array weights of [0, 1].
Mask = Union[ImageT, np.ndarray]

NORMAL_RANGE_TSH = 1.1

INVERT_CURVE = [(0, 255), (255, 0)]


class Curves:

    @staticmethod
    def linear() -> CurveFunc:
        return lambda x: x

    @staticmethod
    def brightness(strength: float) -> CurveFunc:

        SCALE = 0.2

        def _fn(x: float):
            assert 0 <= x <= 1.0
            val = x + (SCALE * x * strength * Curves._wide_mask(x))
            return _clamp(0, val, 1.0)

        return _fn

    @staticmethod
    def darkness(strength: float) -> CurveFunc:

        SCALE = 0.2

        def _fn(x: float):
            assert 0 <= x <= 1.0
            val = x + (SCALE * (1 - x) * -strength * Curves._wide_mask(x))
            return _clamp(0, val, 1.0)

        return _fn

    @staticmethod
    def highlights(strength: float) -> CurveFunc:

        SCALE = 0.2
        TSH = 0.45

        def _fn(x: float) -> float:
            assert 0 <= x <= 1.0
            if x <= TSH:
                return x
            val = x + (SCALE * (x - TSH) * strength * Curves._wide_mask((x - TSH) / (1 - TSH)))
            return max(val, 0)

        return _fn

    @staticmethod
    def ambient(strength: float) -> CurveFunc:

        def _fn(x: float) -> float:
            assert 0 <= x <= 1.0
            mod = sin(x * 2 * pi)
            return x + (0.15 * mod * strength * Curves._tight_mask(x))
        return _fn

    @staticmethod
    def shadows(strength: float) -> CurveFunc:

        SCALE = 0.2
        TSH = 0.5

        def _fn(x: float) -> float:
            assert 0 <= x <= 1.0
            if x >= TSH:
                return x
            val = x + (SCALE * (TSH - x) * strength * Curves._mid_mask(x / TSH))
            return max(val, 0)

        return _fn

    @staticmethod
    def gate(level: float) -> CurveFunc:
        assert 0.0 <= level <= 50
        level_norm = level / CURVE_LEN
        SCALE = 2

        def _ramp(x: float) -> float:
            return (SCALE * x) - (SCALE - 1) * level_norm

        def _fn(x: float) -> float:
            if x >= level_norm:
                return x
            return _clamp(0, _ramp(x), level_norm)

        return _fn

    @staticmethod
    def _wide_mask(x: float) -> float:
        return sqrt(sin(x * pi))

    @staticmethod
    def _mid_mask(x: float) -> float:
        return sin(x * pi)

    @staticmethod
    def _tight_mask(x: float) -> float:
        """A narrower mask than _mask(), fading out smoothly at both ends."""
        return sin(x * pi) ** 2

    @staticmethod
    def combine(curve: CurveFunc, *args) -> CurveFunc:
        if not args:
            return curve
        rem = Curves.combine(*args)
        return lambda x: rem(curve(x))


def is_normal_range(v: List) -> bool:
    if not v:
        return False
    if isinstance(v[0], tuple):
        return is_normal_range([p[0] for p in v])
    return all(x < NORMAL_RANGE_TSH for x in v)


def _clamp(min_v: float, val: float, max_v: float) -> float:
    if val < min_v:
        return min_v
    if val > max_v:
        return max_v
    return val


def normalize(lut: LookupTable) -> LookupTable:
    if is_normal_range(lut):
        return lut
    return [_clamp(0, v / CURVE_LEN, 1) for v in lut]


def denormalize(lut: LookupTable) -> LookupTable:
    if is_normal_range(lut):
        return [_clamp(0, floor((v * CURVE_LEN) + 0.5), CURVE_LEN - 1) for v in lut]
    return lut


def _interpol(c: CurveXY, samples: List[float]) -> LookupTable:

    xp = [p[0] for p in c]
    fp = [p[1] for p in c]
    return list(np.interp(x=samples,
                          xp=xp,
                          fp=fp,
                          left=fp[0],
                          right=fp[-1]))


def _sample_range_of(c: CurveXY) -> List[float]:
    if is_normal_range(c):
        return [v / CURVE_LEN for v in range(CURVE_LEN)]
    return [float(v) for v in range(CURVE_LEN)]


def _populate_from_xy(c: CurveXY) -> LookupTable:

    assert 2 <= len(c) <= CURVE_LEN
    x_set = set(p[0] for p in c)
    assert len(x_set) == len(c)

    if len(c) == CURVE_LEN:
        return [v[1] for v in c]

    c = sorted(c)

    return _interpol(c, samples=_sample_range_of(c))


def _populate_from_func(c: CurveFunc) -> LookupTable:
    samples = [v / CURVE_LEN for v in range(CURVE_LEN)]
    return [c(x) for x in samples]


def populate_curve_xy(c: CurveXY) -> CurveXY:
    assert isinstance(c, list)
    return list(zip(_sample_range_of(c), _populate_from_xy(c)))


def populate(c: Curve) -> LookupTable:
    if callable(c):
        return denormalize(_populate_from_func(c))
    return denormalize(_populate_from_xy(c))


def _levels_of(image: ImageT) -> np.ndarray:
    """The channel levels of an image as a float array."""
    return np.asarray(image, dtype=np.float32)


def _image_of(levels: np.ndarray) -> ImageT:
    """Quantize an array of levels to an image, rounding to the nearest."""
    return Image.fromarray(np.clip(levels + 0.5, 0, MAX_LEVEL).astype(np.uint8))


def _apply_to_luminance(rgb: np.ndarray, lut: LookupTable) -> np.ndarray:
    """
    Apply the lookup table to the luminance of each pixel and scale
    its channels by the resulting gain. This keeps the R:G:B ratios,
    thus the color balance, which an independent per-channel mapping
    would distort wherever the curve is steep, flat, or clipping.
    """
    lum = rgb @ np.asarray(LUMA_WEIGHTS, dtype=np.float32)
    target = np.interp(lum,
                       np.arange(CURVE_LEN, dtype=np.float32),
                       np.asarray(lut, dtype=np.float32)).astype(np.float32)

    # Scaling by target/lum blows up in the deepest shadows - a lifted
    # near-black pixel would turn into a saturated one - so below
    # GAIN_FADE_LEVEL the gain is faded over to adding the difference.
    # Both reach the target luminance exactly, as the weights sum to 1.
    gain = np.divide(target, lum, out=np.zeros_like(lum), where=lum > EPSILON)
    scaled = rgb * gain[..., None]
    offset = rgb + (target - lum)[..., None]
    fade = np.clip(lum / GAIN_FADE_LEVEL, 0, 1)[..., None]
    res = (fade * scaled) + ((1 - fade) * offset)

    # A clipping channel would shift the balance again, so desaturate
    # towards the target luminance instead of letting the clamp do it.
    peak = res.max(axis=-1)
    excess = np.maximum(peak - MAX_LEVEL, 0)
    ratio = np.clip(excess / np.maximum(peak - target, EPSILON), 0, 1)
    res += (target[..., None] - res) * ratio[..., None]

    return res


def _apply_per_channel(image: ImageT, lut: LookupTable) -> np.ndarray:
    """Map each channel of an image through the lookup table independently."""
    return np.asarray(lut, dtype=np.float32)[np.asarray(image)]


def _mask_weights(mask: Mask, size: Tuple[int, int]) -> np.ndarray:
    """The [0, 1] weights of a mask as a float array matching the image size."""

    if isinstance(mask, ImageT):
        if mask.size != size:
            raise ValueError(f'Mask of {mask.size} for an image of {size}')
        weights = np.asarray(mask.convert(mode='L'), dtype=np.float32) / MAX_LEVEL
    else:
        arr = np.asarray(mask)
        if arr.shape != (size[1], size[0]):
            raise ValueError(f'Mask of {arr.shape} for an image of {size}')
        weights = arr.astype(np.float32)
        if np.issubdtype(arr.dtype, np.integer):
            weights = weights / MAX_LEVEL

    return np.clip(weights, 0, 1)


def _blend_levels(base: np.ndarray, overlay: np.ndarray, weights: np.ndarray) -> np.ndarray:
    if base.ndim == 3:
        # The same weight applies to each channel of a multichannel image
        weights = weights[..., None]
    return base + ((overlay - base) * weights)


def blend(base: ImageT, overlay: ImageT, mask: Mask) -> ImageT:
    """
    Mix the overlay over the base image by the mask: where the mask
    is black the base is kept, where it's white the overlay is taken,
    the values in between fade between the two.
    """
    if base.mode != overlay.mode:
        raise ValueError(f'Blending images of {base.mode} and {overlay.mode}')
    if base.size != overlay.size:
        raise ValueError(f'Blending images of {base.size} and {overlay.size}')

    res = _blend_levels(base=_levels_of(base),
                        overlay=_levels_of(overlay),
                        weights=_mask_weights(mask, base.size))
    return _image_of(res)


def apply(image: ImageT,
          curve: Curve,
          per_channel: bool = False,
          mask: Optional[Mask] = None) -> ImageT:
    """
    Apply a curve to an image, keeping the color balance of the pixels.
    Pass per_channel=True to map R, G, and B independently, e.g. for
    curves which are not tonal adjustments like an invert.
    Pass a mask to adjust the image selectively: the curve is applied
    and the result is blended back over the original by the mask,
    see blend(). The blending is done on the unquantized result of the
    curve, so a partially masked pixel keeps the precision of the mix.
    """
    if not per_channel and image.mode != 'RGB':
        raise ValueError(f'RGB image is needed, got {image.mode}')

    lut = populate(curve)

    if per_channel:
        if mask is None:
            # The lookup is exact on integer levels, Pillow does it in place
            return image.point(lut * 3)  # Apply the same curve to R, G, and B
        res = _apply_per_channel(image, lut)
    else:
        res = _apply_to_luminance(_levels_of(image), lut)

    if mask is not None:
        res = _blend_levels(base=_levels_of(image),
                            overlay=res,
                            weights=_mask_weights(mask, image.size))

    return _image_of(res)


def invert_image(image: ImageT) -> ImageT:
    return apply(image=image, curve=INVERT_CURVE, per_channel=True)


def adjust(*, sh: float = 0, amb: float = 0, hl: float = 0) -> Curve:
    return Curves.combine(Curves.shadows(sh), Curves.ambient(amb), Curves.highlights(hl))


def enhance_inv(strength: float) -> Curve:
    assert 0.0 <= strength <= 1.0
    return Curves.combine(Curves.brightness(strength*1.8),
                          Curves.shadows(strength*0.5),
                          Curves.ambient(strength))


def enhance_pos(strength: float) -> Curve:
    assert 0.0 <= strength <= 1.0
    return Curves.combine(Curves.darkness(strength*2),
                          Curves.ambient(strength))


def _annotate_image(image: ImageT, curve: Optional[Curve] = None) -> ImageT:

    lw = min(image.size)
    hist = image.convert(mode='L').histogram()

    img = image.copy().convert(mode='RGB')
    xs = [x * lw / CURVE_LEN for x in range(CURVE_LEN)]

    def line(ys: List[float], color: str):
        draw = ImageDraw.Draw(img)
        xy = list(zip(xs, [lw - y for y in ys]))
        draw.line(xy, width=2, fill=color)

    line([x / 30 for x in hist], color='blue')

    if curve:
        lut = populate(curve)
        lut = [x * img.height / CURVE_LEN for x in lut]
        line(lut, color='red')

    return img


def gradient_image() -> ImageT:

    # Standard deviation of the dithering noise of the generated gradient, in levels
    DITHER_SIGMA = 2.0

    size = (2*CURVE_LEN, 2*CURVE_LEN)
    image = Image.linear_gradient(mode='L').resize(size)
    image = image.transpose(Image.Transpose.ROTATE_90)

    # Gaussian noise is centered at 128, the offset keeps the mean level intact
    noise = Image.effect_noise(size, DITHER_SIGMA)
    image = ImageChops.add(image, noise, offset=-128)

    return image.convert(mode='RGB')


def gen_curve_test_set(inp: Optional[Union[ImageT, str]] = None, out_dir: Optional[str] = None):

    if not inp:
        image = gradient_image()
    elif isinstance(inp, ImageT):
        image = inp
    else:
        image = Image.open(inp)

    if out_dir:
        out_path = Path(out_dir)
        out_path.mkdir(parents=True, exist_ok=True)
    else:
        tmp_dir = TemporaryDirectory(delete=False)
        out_path = Path(tmp_dir.name)

    print(f'Out directory: {out_path.resolve()}')

    def _annot_and_save(img, curve, name):
        img = _annotate_image(image=img, curve=curve)
        out_file = out_path / f'{name}.jpg'
        print(f'  {out_file}')
        img.save(out_file, quality=95)

    _annot_and_save(image, Curves.linear(), 'base')

    img_inv = apply(image, INVERT_CURVE, per_channel=True)
    _annot_and_save(img_inv, INVERT_CURVE, 'inv')

    def series(curve_type, name: str, rng: Tuple[float, float, float]):

        start, step, end = rng
        for i, s in enumerate(np.arange(start, end+step, step, dtype=float)):
            s = round(s, 2)
            c = curve_type(s)
            img_amb = apply(image, c)
            name_postfix = f'{i}{s:+1.2f}'
            _annot_and_save(img_amb, c, f'{name}.{name_postfix}')

    series(Curves.brightness, 'brightness', (-1, 0.2, 1))
    series(Curves.darkness, 'darkness', (-1, 0.2, 1))
    series(Curves.ambient, 'ambient', (-1, 0.2, 1))
    series(Curves.highlights, 'highlights', (-1, 0.2, 1))
    series(Curves.shadows, 'shadows', (-1, 0.2, 1))
    series(Curves.gate, 'gate', (0, 4, 24))

    series(enhance_inv, 'enh', (0, 0.1, 0.7))
    series(enhance_pos, 'enh_p', (0, 0.1, 0.7))

    def eg(x): return Curves.combine(Curves.gate(12), enhance_inv(x))
    series(eg, 'gate-enh', (0, 0.1, 0.7))

    # def enhance_matrix(a_rng: Tuple[float, float, float], h_rng: Tuple[float, float, float]):
    #
    #    a_start, a_step, a_end = a_rng
    #    a_series = np.arange(a_start, a_end+a_step, a_step, dtype=float)
    #    a_series = [round(a, 2) for a in a_series]
    #
    #    for i, a in enumerate(a_series):
    #        def ec(h, amb = a):
    #            return Curves.combine(Curves.ambient(amb), Curves.highlights(h))
    #        series(ec, f'enh_m.{i}{a:+1.2f}', h_rng)
    #
    # enhance_matrix((0, 0.1, 0.5), (0, 0.1, 0.5))


if __name__ == "__main__":

    parser = ArgumentParser()
    parser.add_argument('-i', '--input', help='Input image, default is a generated gradient')
    parser.add_argument('-o', '--out-dir', help='Output directory, default is a temp dir')
    args = parser.parse_args()

    gen_curve_test_set(inp=args.input, out_dir=args.out_dir)
