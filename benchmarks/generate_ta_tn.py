"""
Seeded generator for the Tamil TN benchmark dataset (``benchmarks/ta_tn_benchmark.csv``).

Each row is ``input,expected,type``. Inputs are bare spans or spans embedded in Tamil
carrier sentences; ``expected`` comes from the independent reference in
``ta_reference.py``. ``--verify`` runs the WFST grammar over the rows and prints
disagreements per type so the dataset can be reviewed while it is built.
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks import ta_reference as ref

DEFAULT_OUTPUT = Path(__file__).resolve().parent / "ta_tn_benchmark.csv"
DEFAULT_SEED = 20260905
BARE_SHARE = 0.4
TAMIL_DIGIT_SHARE = 0.1

QUOTAS: dict[str, int] = {
    "cardinal": 2200,
    "decimal": 1000,
    "fraction": 500,
    "date": 1200,
    "time": 900,
    "money": 1200,
    "measure": 800,
    "ordinal": 500,
    "telephone": 600,
    "range": 300,
    "whitelist": 300,
    "mixed": 400,
    "word": 60,
}

# Shapes that once broke the grammar; a few fixed rows keep them as regressions.
REGRESSION_ROWS = 5

CURRENCIES_PREFIX = ["₹", "₹", "₹", "₹", "Rs", "Rs.", "Rs ", "ரூ.", "ரூ", "$", "€", "£", "¥"]
CURRENCIES_SUFFIX = ["ரூ.", "ரூ", "₹"]
LATIN_UNITS = [
    "kg", "g", "mg", "km", "m", "cm", "mm", "l", "L", "ml", "mL", "°C", "°F", "ft", "mi",
    "GB", "MB", "KB", "TB", "kW", "MW", "Hz", "km/h", "ha", "ac", "lb", "oz", "doz", "min",
    "hr", "sec", "yr",
]  # fmt: skip
TAMIL_UNITS = [
    "கி.மீ.",
    "கி.மீ",
    "செ.மீ.",
    "செ.மீ",
    "மி.மீ.",
    "மீ.",
    "கி.கி.",
    "கி.கி",
    "மி.லி.",
    "மி.லி",
    "லி.",
]
DENOMINATORS = [*range(2, 20), 20, 30, 40, 50, 60, 70, 80, 90, 100]
ABBREVIATIONS = ["டாக்.", "புரோ.", "இஞ்.", "லெ.", "கு.", "மா."]
NAMES = ["குமார்", "ராமன்", "சுரேஷ்", "மீனா", "கண்ணன்", "லதா", "அருண்", "பிரியா", "வேலு", "ரவி"]

GENERIC_TEMPLATES = [
    "{X} என்று எழுதப்பட்டுள்ளது.",
    "இதில் {X} குறிப்பிடப்பட்டுள்ளது.",
    "அவர் {X} என்றார்.",
    "{X} பற்றி பேசினோம்.",
    "செய்தியில் {X} என்று வந்தது.",
    "{X} என்பதை நினைவில் கொள்ளுங்கள்.",
    "கடிதத்தில் {X} இருந்தது.",
    "{X} சரியானது.",
]

TEMPLATES: dict[str, list[str]] = {
    "cardinal": [
        "அவள் {X} புத்தகங்கள் வாங்கினாள்.",
        "கூட்டத்தில் {X} பேர் வந்தனர்.",
        "மொத்தம் {X} மாணவர்கள் உள்ளனர்.",
        "அந்த ஊரில் {X} வீடுகள் உள்ளன.",
        "எனக்கு {X} வயது.",
        "{X} நாட்கள் ஆயிற்று.",
        "இந்த நூலில் {X} பக்கங்கள் உள்ளன.",
        "அவர் {X} ஓட்டங்கள் எடுத்தார்.",
        "இன்று {X} பேர் வருகை தந்தனர்.",
        "{X} கிலோ அரிசி வாங்கினேன்.",
        "பள்ளியில் {X} ஆசிரியர்கள் உள்ளனர்.",
        "அந்த நிறுவனத்தில் {X} ஊழியர்கள் பணிபுரிகின்றனர்.",
        "எண் {X} சரியானது.",
        "வண்டி எண் {X} ஆகும்.",
        "மொத்த மதிப்பெண் {X}.",
        "அவன் {X} முறை முயன்றான்.",
    ],
    "decimal": [
        "சராசரி {X} ஆகும்.",
        "அவன் {X} மதிப்பெண் பெற்றான்.",
        "வளர்ச்சி விகிதம் {X} ஆக இருந்தது.",
        "இதன் மதிப்பு {X} தான்.",
        "பை மதிப்பு {X} ஆகும்.",
        "அளவு {X} ஆக உள்ளது.",
        "மழை அளவு {X} என பதிவானது.",
        "நீளம் {X} ஆக இருந்தது.",
        "இன்றைய விலை {X} ஆக உயர்ந்தது.",
        "மதிப்பீடு {X}.",
    ],
    "fraction": [
        "{X} பங்கு வேலை முடிந்தது.",
        "பாத்திரத்தில் {X} பங்கு நீர் உள்ளது.",
        "அவன் {X} பங்கு சாப்பிட்டான்.",
        "{X} பங்கு மாணவர்கள் தேர்ச்சி பெற்றனர்.",
        "நிலத்தில் {X} பங்கு விற்றார்.",
        "இதில் {X} பங்கு எனக்கு.",
        "விடை {X} ஆகும்.",
        "மொத்தத்தில் {X} பங்கு.",
    ],
    "date": [
        "கூட்டம் {X} அன்று நடந்தது.",
        "{X} அன்று விடுமுறை.",
        "தேர்வு {X} தேதியில் தொடங்கும்.",
        "கடைசி தேதி {X}.",
        "பிறந்த நாள் {X}.",
        "{X} முதல் விற்பனை தொடங்கும்.",
        "அவர் {X} அன்று பிறந்தார்.",
        "விண்ணப்பம் {X} அன்று அனுப்பப்பட்டது.",
        "திருமணம் {X} அன்று நடைபெறும்.",
        "பதிவு தேதி {X} ஆகும்.",
        "நாள் {X} என்று குறிக்கப்பட்டுள்ளது.",
        "{X} அன்று மழை பெய்தது.",
    ],
    "time": [
        "கூட்டம் {X} தொடங்கும்.",
        "ரயில் {X} புறப்படும்.",
        "நான் {X} எழுந்தேன்.",
        "அலுவலகம் {X} திறக்கும்.",
        "இப்போது மணி {X}.",
        "விமானம் {X} வந்தடையும்.",
        "நேரம் {X} ஆகிவிட்டது.",
        "வகுப்பு {X} முடியும்.",
        "{X} சாப்பிட வா.",
        "பேருந்து {X} கிளம்பும்.",
        "நிகழ்ச்சி {X} ஒளிபரப்பாகும்.",
    ],
    "money": [
        "விலை {X} மட்டும்.",
        "அவர் {X} செலுத்தினார்.",
        "இந்த சட்டை {X} ஆகும்.",
        "மாத சம்பளம் {X} தான்.",
        "கட்டணம் {X} என அறிவித்தனர்.",
        "{X} கடன் வாங்கினேன்.",
        "மொத்த செலவு {X}.",
        "பரிசுத் தொகை {X}.",
        "வாடகை {X} ஆக உயர்ந்தது.",
        "அந்த நிலம் {X} விலை போனது.",
        "பேருந்து கட்டணம் {X} ஆகும்.",
        "{X} அபராதம் விதிக்கப்பட்டது.",
    ],
    "measure": [
        "அவன் {X} நடந்தான்.",
        "இந்த மூட்டை {X} எடை உள்ளது.",
        "வெப்பநிலை {X} ஆக இருந்தது.",
        "{X} பால் வாங்கினேன்.",
        "தூரம் {X} ஆகும்.",
        "அவள் உயரம் {X} ஆகும்.",
        "தினமும் {X} ஓடுகிறேன்.",
        "பெட்டியின் எடை {X} இருக்கும்.",
        "{X} தண்ணீர் குடிக்க வேண்டும்.",
        "நிலப்பரப்பு {X} ஆகும்.",
        "வேகம் {X} ஆக இருந்தது.",
    ],
    "ordinal": [
        "அவர் {X} இடம் பிடித்தார்.",
        "அவள் {X} வகுப்பு படிக்கிறாள்.",
        "{X} மாடியில் அலுவலகம் உள்ளது.",
        "இது {X} முறை.",
        "{X} நூற்றாண்டு இலக்கியம்.",
        "நான் {X} நபராக வந்தேன்.",
        "{X} அத்தியாயம் படிக்கவும்.",
        "அவன் {X} ஆண்டு படிக்கிறான்.",
        "{X} பக்கத்தில் பதில் உள்ளது.",
        "இது அவரது {X} புத்தகம்.",
    ],
    "telephone": [
        "என் எண் {X}.",
        "{X} என்ற எண்ணை அழைக்கவும்.",
        "தொடர்புக்கு {X}.",
        "அவரின் தொலைபேசி எண் {X} ஆகும்.",
        "உதவி எண் {X} என அறிவித்தனர்.",
        "{X} இந்த எண்ணில் அழையுங்கள்.",
        "புகார் எண் {X} ஆகும்.",
        "அலுவலக எண் {X}.",
    ],
    "range": [
        "{X} வயது குழந்தைகள் வரலாம்.",
        "{X} பேர் வரலாம்.",
        "{X} நாட்கள் ஆகும்.",
        "விலை {X} வரை இருக்கும்.",
        "{X} மணி நேரம் தேவை.",
        "வெப்பநிலை {X} டிகிரி இருக்கும்.",
        "{X} பக்கங்கள் படிக்கவும்.",
        "{X} கிலோ எடை வேண்டும்.",
    ],
    "whitelist": [
        "{X} தள்ளுபடி உள்ளது.",
        "வட்டி {X} ஆக உள்ளது.",
        "{X} என்பது சரி.",
        "விலை {X} உயர்ந்தது.",
        "{X} மாணவர்கள் தேர்ச்சி பெற்றனர்.",
        "கணக்கு {X} என்று வரும்.",
        "{X} வந்தார்.",
        "{X} பேசினார்.",
    ],
}

MIXED_TEMPLATES: list[tuple[str, str, str]] = [
    ("date", "money", "{A} அன்று {B} செலுத்தினேன்."),
    ("date", "time", "கூட்டம் {A} அன்று {B} தொடங்கும்."),
    ("cardinal", "money", "{A} பேருக்கு {B} கொடுத்தேன்."),
    ("time", "cardinal", "{A} வரை {B} பேர் காத்திருந்தனர்."),
    ("measure", "money", "{A} அரிசி {B} ஆகும்."),
    ("ordinal", "date", "{A} கூட்டம் {B} அன்று நடந்தது."),
    ("telephone", "time", "{A} என்ற எண்ணை {B} அழைக்கவும்."),
    ("money", "decimal", "விலை {A} ஆனது {B} சதவீதம் உயர்வு."),
    ("date", "cardinal", "{A} அன்று {B} பேர் வந்தனர்."),
    ("fraction", "measure", "{A} பங்கு அதாவது {B} மட்டும் மீதம்."),
    ("cardinal", "time", "{A} மாணவர்கள் {B} வந்தனர்."),
    ("range", "money", "{A} பேருக்கு {B} செலவு ஆகும்."),
    ("time", "measure", "{A} கிளம்பி {B} நடந்தோம்."),
    ("date", "measure", "{A} அன்று {B} மழை பெய்தது."),
    ("decimal", "cardinal", "சராசரி {A} என்பது {B} மாணவர்களின் கணக்கு."),
    ("ordinal", "money", "{A} பரிசு {B} ஆகும்."),
]

WORD_SENTENCES = [
    "வணக்கம் நண்பர்களே.",
    "இன்று வானிலை நன்றாக உள்ளது.",
    "அவன் வீட்டுக்கு சென்றான்.",
    "நீங்கள் எப்படி இருக்கிறீர்கள்?",
    "நல்ல செய்தி வந்தது!",
    "தமிழ் மொழி மிகவும் இனிமையானது.",
    "நாளை பள்ளிக்கு விடுமுறை.",
    "அவள் பாடம் படிக்கிறாள்.",
    "மழை பெய்யத் தொடங்கியது.",
    "hello world",
    "நான் சென்னையில் வசிக்கிறேன்.",
    "இந்த புத்தகம் மிகவும் சுவாரஸ்யமானது.",
    "காலை உணவு தயாராக உள்ளது.",
    "அவர் ஒரு நல்ல ஆசிரியர்.",
    "எங்கள் ஊர் அழகானது.",
    "நேற்று நண்பரை சந்தித்தேன்.",
    "கடைக்கு போய் வருகிறேன்.",
    "இது என் புதிய வீடு.",
    "எல்லோரும் அமைதியாக இருங்கள்!",
    "நீ எங்கே போகிறாய்?",
    "சாப்பிட்டு விட்டாயா?",
    "பூக்கள் மலர்ந்துள்ளன.",
    "மாணவர்கள் விளையாடினர்.",
    "நான் தமிழ் படிக்கிறேன்.",
    "அம்மா சமைக்கிறார்.",
    "அப்பா அலுவலகம் சென்றார்.",
    "குழந்தைகள் பூங்காவில் விளையாடுகின்றனர்.",
    "இன்று திங்கட்கிழமை.",
    "நாளை மழை பெய்யும் என்று சொன்னார்கள்.",
    "எனக்கு தேநீர் பிடிக்கும்.",
    "அவர் புத்தகம் எழுதுகிறார்.",
    "நண்பர்கள் அனைவரும் வந்தனர்.",
    "இந்த பாடல் மிகவும் பிடித்திருக்கிறது.",
    "வீட்டில் யாரும் இல்லை.",
    "கதவை மூடு.",
    "தயவுசெய்து அமைதியாக இருங்கள்.",
    "இன்றைய செய்திகள் இதோ.",
    "சூரியன் கிழக்கில் உதிக்கிறது.",
    "பறவைகள் வானில் பறக்கின்றன.",
    "கடல் அலைகள் ஓசை எழுப்புகின்றன.",
    "நான் நேற்று திரைப்படம் பார்த்தேன்.",
    "அவள் நன்றாக பாடுகிறாள்.",
    "இந்த கடையில் நல்ல பழங்கள் கிடைக்கும்.",
    "வண்டி வேகமாக சென்றது.",
    "மாலை நேரம் அழகாக இருந்தது.",
    "நான் உங்களுக்கு உதவுவேன்.",
    "எங்கள் பள்ளி மிகவும் பெரியது.",
    "இது யாருடைய பை?",
    "எப்போது வருவீர்கள்?",
    "நல்லது நடக்கும்!",
    "வாழ்த்துக்கள்!",
    "good morning everyone",
    "இந்த திட்டம் நன்றாக உள்ளது.",
    "அவர்கள் விவசாயம் செய்கிறார்கள்.",
    "தோட்டத்தில் மரங்கள் உள்ளன.",
    "நான் தினமும் நடைப்பயிற்சி செய்கிறேன்.",
    "இன்று கூட்டம் ரத்து செய்யப்பட்டது.",
    "பேருந்து தாமதமாக வந்தது.",
    "அவன் நல்ல மாணவன்.",
    "எல்லாம் நலம்.",
]

Span = tuple[str, str, bool]  # (input span, expected span, may end sentence)


@dataclass(frozen=True)
class Row:
    """
    One benchmark row.
    """

    text: str
    expected: str
    kind: str


class Generator:
    """
    Seeded producer of benchmark spans and rows.
    """

    def __init__(self, seed: int) -> None:
        self.rng = random.Random(seed)
        self.spans: dict[str, Callable[[], Span]] = {
            "cardinal": self.cardinal,
            "decimal": self.decimal,
            "fraction": self.fraction,
            "date": self.date,
            "time": self.time,
            "money": self.money,
            "measure": self.measure,
            "ordinal": self.ordinal,
            "telephone": self.telephone,
            "range": self.number_range,
            "whitelist": self.whitelist,
        }

    # ------------------------------------------------------------------ helpers

    def _digits(self, low: int, high: int) -> str:
        return str(self.rng.randint(low, high))

    def _weighted(self, options: list[tuple[str, int]]) -> str:
        names = [name for name, _ in options]
        weights = [w for _, w in options]
        return self.rng.choices(names, weights=weights, k=1)[0]

    def _number(self) -> str:
        bucket = self._weighted(
            [
                ("units", 5),
                ("tens", 15),
                ("hundreds", 22),
                ("thousands", 22),
                ("ten_thousands", 10),
                ("lakhs", 12),
                ("crores", 6),
                ("indian_commas", 8),
            ]
        )
        if bucket == "units":
            return self._digits(0, 9)
        if bucket == "tens":
            return self._digits(10, 99)
        if bucket == "hundreds":
            return self._digits(100, 999)
        if bucket == "thousands":
            return self._digits(1000, 9999)
        if bucket == "ten_thousands":
            return self._digits(10000, 99999)
        if bucket == "lakhs":
            return self._digits(100000, 9999999)
        if bucket == "crores":
            return self._digits(10000000, 999999999)
        return indian_commas(self._digits(1000, 999999999))

    def _intl_number(self) -> str:
        n = self.rng.randint(1000, 999999)
        return f"{n:,}"

    # ------------------------------------------------------------------ spans

    def cardinal(self) -> Span:
        shape = self._weighted(
            [
                ("plain", 70),
                ("intl", 5),
                ("negative", 5),
                ("leading_zero", 2),
                ("locative", 10),
                ("digit_string", 3),
            ]
        )
        if shape == "plain":
            text = self._number()
            return text, ref.cardinal(text), True
        if shape == "intl":
            text = self._intl_number()
            return text, ref.cardinal(text), True
        if shape == "negative":
            text = "-" + self._number().replace(",", "")
            return text, ref.cardinal(text), True
        if shape == "leading_zero":
            text = "0" + self._digits(1, 9)
            return text, ref.cardinal(text), True
        if shape == "locative":
            number = self.rng.choice([self._digits(1, 99), self._digits(100, 9999), "1000", "2000"])
            text = number + self.rng.choice(["ல்", "இல்"])
            return text, ref.locative(number), True
        text = "".join(self.rng.choice("0123456789") for _ in range(self.rng.randint(10, 13)))
        return text, ref.digit_by_digit(text), True

    def decimal(self) -> Span:
        integer = self.rng.choice(
            [self._digits(0, 9), self._digits(10, 999), self._digits(1000, 99999)]
        )
        frac = "".join(self.rng.choice("0123456789") for _ in range(self.rng.randint(1, 3)))
        if frac.endswith("0") and len(frac) > 1:
            frac = frac[:-1] + self.rng.choice("123456789")
        text = f"{integer}.{frac}"
        if self.rng.random() < 0.08:
            text = "-" + text
        if self.rng.random() < 0.05 and not text.startswith("-") and integer != "1":
            quantity = self.rng.choice(["இலட்சம்", "கோடி"])
            return f"{text} {quantity}", ref.decimal(text, quantity), True
        return text, ref.decimal(text), True

    def fraction(self) -> Span:
        shape = self._weighted([("simple", 70), ("mixed", 15), ("vulgar", 10), ("mixed_vulgar", 5)])
        if shape in ("vulgar", "mixed_vulgar"):
            sign = self.rng.choice(list(ref.VULGAR_FRACTIONS))
            text = sign if shape == "vulgar" else f"{self._digits(1, 20)}{sign}"
            return text, ref.fraction(text), True
        den = self.rng.choice(DENOMINATORS)
        num = (
            self.rng.randint(1, max(1, den - 1))
            if self.rng.random() < 0.85
            else self.rng.randint(1, 99)
        )
        text = f"{num}/{den}"
        if shape == "mixed":
            text = f"{self._digits(1, 20)} {text}"
        return text, ref.fraction(text), True

    def date(self) -> Span:
        year = (
            self.rng.randint(1900, 2099)
            if self.rng.random() < 0.85
            else self.rng.randint(1000, 2999)
        )
        month = self.rng.randint(1, 12)
        day = (
            self.rng.randint(1, 28)
            if month == 2
            else self.rng.randint(1, 30 if month in (4, 6, 9, 11) else 31)
        )
        shape = self._weighted(
            [("dmy", 60), ("dmy_slash", 15), ("dmy_dot", 5), ("iso", 12), ("mdy", 8)]
        )
        if shape == "iso":
            text = f"{year}-{month:02d}-{day:02d}"
        elif shape == "mdy":
            day = max(day, 13)
            text = f"{month:02d}-{day:02d}-{year}"
        else:
            sep = {"dmy": "-", "dmy_slash": "/", "dmy_dot": "."}[shape]
            text = f"{day:02d}{sep}{month:02d}{sep}{year}"
        return text, ref.date(text), True

    def time(self) -> Span:
        hour = self.rng.randint(1, 24)
        minute = self.rng.randint(0, 59)
        hour_text = f"{hour:02d}" if self.rng.random() < 0.5 else str(hour)
        shape = self._weighted([("hm", 66), ("hms", 20), ("h00", 8), ("hms00", 3), ("h00s", 3)])
        if shape == "h00":
            text = f"{hour_text}:00"
        elif shape == "hms00":
            text = f"{hour_text}:{max(minute, 1):02d}:00"
        elif shape == "h00s":
            text = f"{hour_text}:00:{self.rng.randint(1, 59):02d}"
        elif shape == "hms":
            minute = max(minute, 1)
            text = f"{hour_text}:{minute:02d}:{self.rng.randint(1, 59):02d}"
        else:
            text = f"{hour_text}:{minute:02d}"
        if self.rng.random() < 0.3:
            text += " மணிக்கு"
        return text, ref.time(text), True

    def money(self) -> Span:
        amount = self.rng.choice(
            [
                self._digits(1, 99),
                self._digits(100, 9999),
                self._number().replace(",", ""),
                indian_commas(self._digits(1000, 99999999)),
            ]
        )
        if self.rng.random() < 0.3:
            frac = self._digits(1, 9) if self.rng.random() < 0.3 else f"{self.rng.randint(10, 99)}"
            amount = f"{amount}.{frac}"
        if self.rng.random() < 0.05:
            amount = f"0.{self.rng.randint(10, 99)}"
        if self.rng.random() < 0.85:
            symbol = self.rng.choice(CURRENCIES_PREFIX)
            space = "" if symbol.endswith(" ") else self.rng.choice(["", "", " "])
            text = f"{symbol}{space}{amount}"
            end_ok = True
        else:
            symbol = self.rng.choice(CURRENCIES_SUFFIX)
            text = f"{amount}{self.rng.choice(['', ' '])}{symbol}"
            end_ok = symbol == "₹"
        if symbol.startswith(("₹", "Rs", "ரூ")) and self.rng.random() < 0.1 and "." not in amount:
            text += self.rng.choice(["/-", " /-"])
        return text, ref.money(text), end_ok

    def measure(self) -> Span:
        tamil_unit = self.rng.random() < 0.3
        unit = self.rng.choice(TAMIL_UNITS if tamil_unit else LATIN_UNITS)
        amount = self.rng.choice([self._digits(1, 99), self._digits(100, 9999), self._digits(1, 9)])
        if self.rng.random() < 0.3:
            amount = f"{amount}.{self._digits(1, 99)}".replace(".0", ".5")
        if unit in ("°C", "°F") and self.rng.random() < 0.3:
            amount = "-" + amount
        space = self.rng.choice(["", " ", " "]) if not tamil_unit else " "
        text = f"{amount}{space}{unit}"
        return text, ref.measure(text), not unit.endswith(".") and not tamil_unit

    def ordinal(self) -> Span:
        number = self.rng.choice(
            [
                self._digits(1, 12),
                self._digits(1, 99),
                self._digits(100, 999),
                self._digits(1000, 9999),
            ]
        )
        suffix = self._weighted([("வது", 55), ("ஆவது", 15), ("ஆம்", 30)])
        text = number + suffix
        return text, ref.ordinal(text), True

    def telephone(self) -> Span:
        shape = self._weighted([("mobile", 55), ("cc_mobile", 25), ("landline", 20)])
        if shape == "landline":
            std = "0" + "".join(
                self.rng.choice("0123456789") for _ in range(self.rng.randint(1, 3))
            )
            subscriber = "".join(
                self.rng.choice("0123456789") for _ in range(self.rng.randint(6, 8))
            )
            text = f"{std}-{subscriber}"
        else:
            mobile = self.rng.choice("6789") + "".join(
                self.rng.choice("0123456789") for _ in range(9)
            )
            text = mobile
            if shape == "cc_mobile":
                code = self.rng.choice(["91", "91", "91", "1", "44", "65", "971"])
                text = f"+{code}{self.rng.choice([' ', ' ', ''])}{mobile}"
        return text, ref.telephone(text), True

    def number_range(self) -> Span:
        lower = self.rng.choice(
            [self.rng.randint(1, 99), self.rng.randint(100, 999), self.rng.randint(1000, 2100)]
        )
        upper = lower + self.rng.randint(1, max(1, lower))
        text = f"{lower}-{upper}"
        return text, ref.number_range(text), True

    def whitelist(self) -> Span:
        shape = self._weighted([("percent", 50), ("equation", 25), ("abbr", 25)])
        if shape == "percent":
            number = (
                self._digits(0, 100)
                if self.rng.random() < 0.8
                else f"{self._digits(0, 99)}.{self._digits(1, 9)}"
            )
            text = f"{number}{self.rng.choice(['%', '%', ' %'])}"
            return text, ref.percent(text), True
        if shape == "equation":
            a, b = self.rng.randint(1, 12), self.rng.randint(1, 12)
            if self.rng.random() < 0.6:
                text = f"{a}×{b}={a * b}"
            else:
                text = f"{a * b}÷{b}={a}" if self.rng.random() < 0.5 else f"{a * b}÷{b}"
            return text, ref.equation(text), True
        text = f"{self.rng.choice(ABBREVIATIONS)} {self.rng.choice(NAMES)}"
        return text, ref.abbreviation(text), False

    # ------------------------------------------------------------------ rows

    def _maybe_tamil_digits(self, kind: str, span: Span) -> Span:
        if kind in ("telephone", "whitelist") or self.rng.random() >= TAMIL_DIGIT_SHARE:
            return span
        text, expected, end_ok = span
        return ref.to_tamil_digits(text), expected, end_ok

    def row(self, kind: str) -> Row:
        if kind == "word":
            text = self.rng.choice(WORD_SENTENCES)
            return Row(text, ref.space_punctuation(text), kind)
        if kind == "mixed":
            kind_a, kind_b, template = self.rng.choice(MIXED_TEMPLATES)
            a = self._maybe_tamil_digits(kind_a, self.spans[kind_a]())
            b = self._maybe_tamil_digits(kind_b, self.spans[kind_b]())
            text = template.format(A=a[0], B=b[0])
            expected = ref.space_punctuation(template).format(A=a[1], B=b[1])
            return Row(text, expected, kind)
        span = self._maybe_tamil_digits(kind, self.spans[kind]())
        text, expected, end_ok = span
        if self.rng.random() < BARE_SHARE:
            return Row(text, expected, kind)
        templates = TEMPLATES[kind] + GENERIC_TEMPLATES
        if kind == "whitelist" and not end_ok:
            templates = [t for t in templates if t.startswith("{X} ")]
        candidates = [t for t in templates if end_ok or not t.rstrip(".?!").endswith("{X}")]
        template = self.rng.choice(candidates)
        return Row(
            template.format(X=text), ref.space_punctuation(template).format(X=expected), kind
        )


def indian_commas(digits: str) -> str:
    """
    Format a digit string with Indian grouping: ``1500000`` -> ``15,00,000``.
    """
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    groups: list[str] = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join([*groups, tail])


def regression_rows() -> list[Row]:
    """
    Fixed rows for shapes that used to fail (documented in the README).
    """
    rows: list[Row] = []
    for n in range(1, REGRESSION_ROWS + 1):
        rows.append(Row(f"{n},000,000", ref.cardinal(f"{n},000,000"), "cardinal"))
        rows.append(Row(f"-₹{n * 50}", ref.money(f"-₹{n * 50}"), "money"))
        rows.append(Row(f"{n + 10}-வது", ref.ordinal(f"{n + 10}-வது"), "ordinal"))
        rows.append(Row(f"{n + 8}:30:00", ref.time(f"{n + 8}:30:00"), "time"))
        rows.append(Row(f"{n}/4/2024", ref.date(f"{n}/4/2024"), "date"))
        rows.append(Row(f"{n + 8}:00:{n * 7:02d}", ref.time(f"{n + 8}:00:{n * 7:02d}"), "time"))
    return rows


def generate(rows: int, seed: int) -> list[Row]:
    """
    Produce at least ``rows`` unique rows following the class quotas.
    """
    gen = Generator(seed)
    scale = rows / sum(QUOTAS.values())
    seen: set[str] = set()
    out: list[Row] = []
    for row in regression_rows():
        seen.add(row.text)
        out.append(row)

    def add(kind: str) -> bool:
        row = gen.row(kind)
        text = ref.nfc(row.text)
        if text in seen or text != text.strip():
            return False
        seen.add(text)
        out.append(Row(text, ref.with_alternatives(ref.nfc(row.expected)), kind))
        return True

    for kind, quota in QUOTAS.items():
        target = max(1, round(quota * scale))
        produced = 0
        for _ in range(target * 50):
            if produced >= target:
                break
            produced += add(kind)
        if produced < target:
            print(f"warning: only {produced}/{target} unique rows for {kind}", file=sys.stderr)
    top_up = [k for k in QUOTAS if k not in ("word", "mixed")]
    # `add` returns False for a duplicate, so the unique-span space can run out; cap the
    # attempts as the quota loop does rather than spinning forever.
    for _ in range((rows - len(out)) * 50 + 1):
        if len(out) >= rows:
            break
        add(gen.rng.choice(top_up))
    if len(out) < rows:
        print(f"warning: only {len(out)}/{rows} unique rows after top-up", file=sys.stderr)
    gen.rng.shuffle(out)
    return out


def write_csv(rows: list[Row], path: Path) -> None:
    """
    Write rows as ``input,expected,type`` UTF-8 CSV.
    """
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["input", "expected", "type"])
        for row in rows:
            writer.writerow([row.text, row.expected, row.kind])


def verify(rows: list[Row], cache_dir: Path, examples: int) -> int:
    """
    Run the grammar over ``rows`` and print disagreements per type; return their count.
    """
    from benchmarks.run_benchmark import build_normalizer

    normalize = build_normalizer("ta", "tn", cache_dir)
    totals: Counter[str] = Counter()
    bad: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for row in rows:
        totals[row.kind] += 1
        actual = normalize(row.text)
        if actual not in row.expected.split(ref.ALTERNATIVE_SEPARATOR):
            bad[row.kind].append((row.text, row.expected, actual))
    mismatches = sum(len(v) for v in bad.values())
    for kind in QUOTAS:
        print(f"{kind:10s} rows={totals[kind]:5d} mismatches={len(bad[kind]):4d}")
        for text, expected, actual in bad[kind][:examples]:
            print(f"    input:    {text}\n    expected: {expected}\n    actual:   {actual}")
    print(f"total rows={len(rows)} mismatches={mismatches}")
    return mismatches


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=10000, help="minimum number of rows")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--verify", action="store_true", help="run the grammar and report disagreements"
    )
    parser.add_argument(
        "--examples", type=int, default=5, help="examples per type to print with --verify"
    )
    parser.add_argument(
        "--cache-dir", type=Path, default=Path(__file__).resolve().parent / ".far_cache"
    )
    args = parser.parse_args(argv)

    rows = generate(args.rows, args.seed)
    write_csv(rows, args.output)
    print(f"wrote {len(rows)} rows to {args.output}")
    if args.verify:
        verify(rows, args.cache_dir, args.examples)
    return 0


if __name__ == "__main__":
    sys.exit(main())
