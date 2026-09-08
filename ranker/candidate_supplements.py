"""Small deterministic candidate supplements for common IME blind spots."""

from __future__ import annotations

from typing import Iterable


ABBREVIATION_SURFACES = {
    "えーぴーあい": "API",
    "えーあい": "AI",
    "しーぴーゆー": "CPU",
    "じーぴーゆー": "GPU",
    "ゆーあーるえる": "URL",
    "えいちてぃーてぃーぴー": "HTTP",
    "えいちてぃーてぃーぴーえす": "HTTPS",
    "えいちてぃーえむえる": "HTML",
    "しーえすえす": "CSS",
    "えすきゅーえる": "SQL",
    "じぇいそん": "JSON",
    "しーえすぶい": "CSV",
    "ぴーでぃーえふ": "PDF",
    "ゆーえすびー": "USB",
    "えすえすでぃー": "SSD",
    "えいちでぃーでぃー": "HDD",
}

WORD_SURFACES = {
    "けんしん": ("健診",),
}

PHRASE_SURFACES = {
    "えーぴーあいれんけい": ("API連携",),
}

_DIGITS = {
    "れい": 0,
    "ぜろ": 0,
    "いち": 1,
    "に": 2,
    "さん": 3,
    "よん": 4,
    "し": 4,
    "ご": 5,
    "ろく": 6,
    "なな": 7,
    "しち": 7,
    "はち": 8,
    "きゅう": 9,
    "く": 9,
}
_UNITS = {
    "じゅう": 10,
    "じゅっ": 10,
    "ひゃく": 100,
    "びゃく": 100,
    "ぴゃく": 100,
    "せん": 1000,
    "ぜん": 1000,
    "まん": 10000,
    "おく": 100000000,
}
_NUMERIC_SUFFIXES = {
    "ぱーせんと": "パーセント",
    "ねんど": "年度",
    "にん": "人",
    "にち": "日",
    "じ": "時",
    "こ": "個",
    "だい": "台",
    "まい": "枚",
    "ほん": "本",
    "ひき": "匹",
    "えん": "円",
    "い": "位",
}


def _parse_number_prefix(reading: str) -> tuple[int, int] | None:
    tokens = sorted((*_DIGITS, *_UNITS), key=len, reverse=True)
    position = 0
    total = 0
    section = 0
    current: int | None = None
    matched = False
    while position < len(reading):
        token = next((item for item in tokens if reading.startswith(item, position)), None)
        if token is None:
            break
        matched = True
        position += len(token)
        if token in _DIGITS:
            current = _DIGITS[token]
            continue
        unit = _UNITS[token]
        if unit >= 10000:
            section += current if current is not None else 1
            total += section * unit
            section = 0
            current = None
        else:
            section += (current if current is not None else 1) * unit
            current = None
    if not matched:
        return None
    return total + section + (current or 0), position


def _kanji_number(value: int) -> str:
    if value == 0:
        return "零"
    digits = "〇一二三四五六七八九"
    if value < 10:
        return digits[value]
    if value < 100:
        tens, ones = divmod(value, 10)
        return ("" if tens == 1 else digits[tens]) + "十" + (digits[ones] if ones else "")
    if value < 1000:
        hundreds, rest = divmod(value, 100)
        return ("" if hundreds == 1 else digits[hundreds]) + "百" + (_kanji_number(rest) if rest else "")
    if value < 10000:
        thousands, rest = divmod(value, 1000)
        return ("" if thousands == 1 else digits[thousands]) + "千" + (_kanji_number(rest) if rest else "")
    return str(value)


def numeric_supplement_surfaces(reading: str) -> tuple[str, ...]:
    ordinal = reading.startswith("だい")
    number_reading = reading[2:] if ordinal else reading
    suffix = None
    value = None
    for key, surface in sorted(
        _NUMERIC_SUFFIXES.items(), key=lambda item: len(item[0]), reverse=True
    ):
        if not number_reading.endswith(key):
            continue
        parsed = _parse_number_prefix(number_reading[: -len(key)])
        if parsed is not None and parsed[1] == len(number_reading) - len(key):
            value = parsed[0]
            suffix = surface
            break
    if suffix is None or value is None:
        return ()
    if ordinal and suffix != "位":
        return ()
    if ordinal:
        return (f"第{value}{suffix}", f"第{_kanji_number(value)}{suffix}")
    return (f"{value}{suffix}", f"{_kanji_number(value)}{suffix}")


def supplemental_surfaces(reading: str) -> tuple[str, ...]:
    surfaces = list(WORD_SURFACES.get(reading, ()))
    surfaces.extend(PHRASE_SURFACES.get(reading, ()))
    abbreviation = ABBREVIATION_SURFACES.get(reading)
    if abbreviation:
        surfaces.append(abbreviation)
    surfaces.extend(numeric_supplement_surfaces(reading))
    # Conversion often attaches a particle or inflection to the same Mozc
    # segment.  Preserve that suffix while replacing only the blind-spot
    # reading span (けんしんを -> 健診を, 15日までに出す, ...).
    prefix_sources = {
        **{key: value[0] for key, value in WORD_SURFACES.items()},
        **{key: value[0] for key, value in PHRASE_SURFACES.items()},
    }
    for key, surface in sorted(prefix_sources.items(), key=lambda item: len(item[0]), reverse=True):
        if reading.startswith(key) and len(reading) > len(key):
            surfaces.append(surface + reading[len(key):])
    numeric_prefixes = (
        "じゅうごにち", "にせんにじゅうろくねんど", "じゅっこ", "だいごい", "いちい",
    )
    for key in numeric_prefixes:
        if reading.startswith(key) and len(reading) > len(key):
            base = numeric_supplement_surfaces(key)
            surfaces.extend(surface + reading[len(key):] for surface in base[:1])
    return tuple(dict.fromkeys(surfaces))


def supplemental_prefix(reading: str) -> tuple[str, tuple[str, ...]] | None:
    """Return the longest repairable reading prefix and its surfaces."""
    sources: dict[str, tuple[str, ...]] = {
        **WORD_SURFACES,
        **PHRASE_SURFACES,
    }
    for key in ("じゅうごにち", "にせんにじゅうろくねんど", "じゅっこ", "だいごい", "いちい"):
        values = numeric_supplement_surfaces(key)
        if values:
            sources[key] = values
    matches = [
        (key, values) for key, values in sources.items() if reading.startswith(key)
    ]
    if not matches:
        return None
    return max(matches, key=lambda item: len(item[0]))


def prepare_supplemented_segments(reading: str, segments: list[dict]) -> list[dict]:
    """Collapse only the repairable reading span, retaining following grammar."""
    prefix = supplemental_prefix(reading)
    if prefix is None or len(segments) == 0:
        return segments
    base_reading, surfaces = prefix
    base_length = len(base_reading)
    consumed_length = 0
    for index, segment in enumerate(segments):
        key = str(segment["key"])
        next_length = consumed_length + len(key)
        if next_length < base_length:
            consumed_length = next_length
            continue
        trailing = key[base_length - consumed_length:]
        raw_surface = "".join(str(item["candidates"][0]) for item in segments[: index + 1])
        synthetic = {
            "index": 0,
            "segment_count": len(segments) - index,
            "key": base_reading + trailing,
            "candidates": [raw_surface] + [surface + trailing for surface in surfaces],
        }
        return [synthetic] + segments[index + 1:]
    return segments


def merge_supplemental_surfaces(reading: str, candidates: Iterable[str]) -> list[str]:
    """Append supplements without changing Mozc's existing candidate order."""
    result = list(candidates)
    for surface in supplemental_surfaces(reading):
        if surface not in result:
            result.append(surface)
    return result
