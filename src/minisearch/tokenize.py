"""Text tokenization with light Russian stemming."""

from __future__ import annotations

import re

_TOKEN = re.compile(r"\w+", re.UNICODE)
_CYRILLIC = re.compile(r"[\u0400-\u04FF]")
_VOWEL = re.compile(r"[аеиоуыэюя]")

# Snowball Russian ending groups (applied inside RV).
_PERFECTIVE_GERUND = re.compile(
    r"((ив|ивши|ившись|ыв|ывши|ывшись)|((?<=[ая])(в|вши|вшись)))$"
)
_REFLEXIVE = re.compile(r"(с[яь])$")
_ADJECTIVE = re.compile(
    r"(ее|ие|ые|ое|ими|ыми|ей|ий|ый|ой|ем|им|ым|ом|его|ого|ему|ому|их|ых|"
    r"ую|юю|ая|яя|ою|ею)$"
)
_PARTICIPLE = re.compile(r"((ивш|ывш|ующ)|((?<=[ая])(ем|нн|вш|ющ|щ)))$")
_VERB = re.compile(
    r"((ила|ыла|ена|ейте|уйте|ите|или|ыли|ей|уй|ил|ыл|им|ым|ен|ило|ыло|ено|"
    r"ят|ует|уют|ит|ыт|ены|ить|ыть|ишь|ую|ю)|"
    r"((?<=[ая])(ла|на|ете|йте|ли|й|л|ем|н|ло|но|ет|ют|ны|ть|ешь|нно)))$"
)
_NOUN = re.compile(
    r"(а|ев|ов|ие|ье|е|иями|ями|ами|еи|ии|и|ией|ей|ой|ий|й|иям|ям|ием|ем|"
    r"ам|ом|о|у|ах|иях|ях|ы|ь|ию|ью|ю|ия|ья|я)$"
)
_SUPERLATIVE = re.compile(r"(ейше|ейш)$")
_DERIVATIONAL = re.compile(r"ость?$")
_I = re.compile(r"и$")
_NN = re.compile(r"нн$")
_SOFT = re.compile(r"ь$")


def _rv(word: str) -> int:
    """Start index of RV region (after first vowel)."""
    m = _VOWEL.search(word)
    return m.end() if m else len(word)


def _r2(word: str) -> int:
    """Start index of R2 (second consonant-after-vowel region)."""
    rv = _rv(word)
    m1 = _VOWEL.search(word, rv)
    if not m1:
        return len(word)
    # after first non-vowel following that vowel
    i = m1.end()
    while i < len(word) and _VOWEL.match(word[i]):
        i += 1
    if i >= len(word):
        return len(word)
    i += 1  # past the consonant
    m2 = _VOWEL.search(word, i)
    if not m2:
        return len(word)
    j = m2.end()
    while j < len(word) and _VOWEL.match(word[j]):
        j += 1
    if j >= len(word):
        return len(word)
    return j + 1


def _stem_ru(word: str) -> str:
    word = word.replace("ё", "е")
    if len(word) <= 1 or not _CYRILLIC.search(word):
        return word

    rv = _rv(word)
    if rv >= len(word):
        return word

    # Step 1
    stem, end = word[:rv], word[rv:]
    m = _PERFECTIVE_GERUND.search(end)
    if m:
        end = end[: m.start()]
    else:
        m = _REFLEXIVE.search(end)
        if m:
            end = end[: m.start()]
        matched = False
        m = _ADJECTIVE.search(end)
        if m:
            end2 = end[: m.start()]
            m2 = _PARTICIPLE.search(end2)
            end = end2[: m2.start()] if m2 else end2
            matched = True
        if not matched:
            m = _VERB.search(end)
            if m:
                end = end[: m.start()]
                matched = True
        if not matched:
            m = _NOUN.search(end)
            if m:
                end = end[: m.start()]

    # Step 2
    m = _I.search(end)
    if m:
        end = end[: m.start()]

    # Step 3 (derivational in R2 of full word)
    full = stem + end
    r2 = _r2(full)
    if r2 < len(full):
        suffix = full[r2:]
        m = _DERIVATIONAL.search(suffix)
        if m:
            full = full[: r2 + m.start()]
            stem, end = full[:rv], full[rv:] if rv < len(full) else ""

    # Step 4
    m = _SUPERLATIVE.search(end)
    if m:
        end = end[: m.start()]
    m = _NN.search(end)
    if m:
        end = end[: m.start()] + "н"
    else:
        m = _SOFT.search(end)
        if m:
            end = end[: m.start()]

    return stem + end


def tokenize(text: str) -> list[str]:
    tokens = _TOKEN.findall(text.lower())
    return [_stem_ru(t) if _CYRILLIC.search(t) else t for t in tokens]
