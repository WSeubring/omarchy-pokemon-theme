"""sRGB <-> OKLCh, with gamut mapping by chroma reduction.

Palettes are built in OKLCh because lightness there is perceptually uniform:
pinning L is what makes a generated theme readable regardless of which hue the
day's Pokemon supplies. Values from Bjorn Ottosson's reference implementation.
"""

import math

# --- transfer functions ---

def _to_linear(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _to_srgb(c):
    c = 12.92 * c if c <= 0.0031308 else 1.055 * (max(c, 0.0) ** (1 / 2.4)) - 0.055
    return c


# --- conversions ---

def hex_to_oklch(value):
    h = value.lstrip("#")
    r, g, b = (_to_linear(int(h[i:i + 2], 16)) for i in (0, 2, 4))
    return _linear_to_oklch(r, g, b)


def _linear_to_oklch(r, g, b):
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (max(v, 0.0) ** (1 / 3) for v in (l, m, s))
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return L, math.hypot(a, bb), math.degrees(math.atan2(bb, a)) % 360


def _oklch_to_linear(L, C, H):
    a = C * math.cos(math.radians(H))
    b = C * math.sin(math.radians(H))
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (
        +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


def oklch_to_hex(L, C, H):
    """Convert to sRGB, walking chroma down until the colour fits the gamut.

    Clipping channels instead would shift hue and lightness; dropping chroma
    keeps both and only desaturates, which is the least visible compromise.
    """
    for _ in range(64):
        rgb = _oklch_to_linear(L, C, H)
        if all(-1e-4 <= v <= 1 + 1e-4 for v in rgb):
            break
        C -= 0.005
        if C <= 0:
            C = 0
            rgb = _oklch_to_linear(L, 0, H)
            break
    out = []
    for v in rgb:
        out.append(max(0, min(255, round(_to_srgb(min(max(v, 0.0), 1.0)) * 255))))
    return "#%02x%02x%02x" % tuple(out)


def blend_hue(base, target, amount):
    """Rotate `base` toward `target` by `amount` along the shorter arc."""
    delta = ((target - base + 180) % 360) - 180
    return (base + delta * amount) % 360
