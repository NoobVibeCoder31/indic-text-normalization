"""
ITN tagger converting spoken clock times to digits, shared by every language.
"""

from dataclasses import dataclass

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import GraphFst, delete_space
from indic_text_normalization.core.itn_taggers.cardinal import ItnCardinalFst, half_form_rows
from indic_text_normalization.core.utils import data_path, load_labels


@dataclass(frozen=True)
class ItnTimeWords:
    """
    The spoken clock vocabulary of one language, as ITN hears it.

    Attributes
    ----------
    hour_nouns : ``tuple[str, ...]``
        Plain hour nouns (గంటల, గంట, గంటలు).
    minute_nouns : ``tuple[str, ...]``
        Plain minute nouns.
    second_nouns : ``tuple[str, ...]``
        Plain second nouns.
    hour_suffixed : ``tuple[tuple[str, str], ...]``
        Inflected hour nouns and the written suffix they become (గంటలకు -> కు).
    minute_suffixed : ``tuple[tuple[str, str], ...]``
        Inflected minute nouns and their written suffix.
    second_suffixed : ``tuple[tuple[str, str], ...]``
        Inflected second nouns and their written suffix.
    hour_one : ``tuple[str, str] | None``
        The clock-one word and the noun it takes when the pair alone is a clock time
        (ఒంటి గంట -> 1:00), or None when a bare hour is never a clock time.
    minute_one : ``str | None``
        The counting word for one minute or second (ఒక నిమిషం -> :01).
    half_glued_suffixes : ``tuple[tuple[str, str], ...]``
        Suffixes glued to a fused half-hour word and the written suffix each becomes
        (పదిన്నరకు -> 10:30కు, പത്തരയ്ക്ക് -> 10:30ന്).
    clock_hour_nouns : ``tuple[str, ...]``
        Hour nouns that alone make a clock time, never a duration (Hindi बजे: दस बजे -> 10:00).
    """

    hour_nouns: tuple[str, ...]
    minute_nouns: tuple[str, ...]
    second_nouns: tuple[str, ...]
    hour_suffixed: tuple[tuple[str, str], ...] = ()
    minute_suffixed: tuple[tuple[str, str], ...] = ()
    second_suffixed: tuple[tuple[str, str], ...] = ()
    hour_one: tuple[str, str] | None = None
    minute_one: str | None = None
    half_glued_suffixes: tuple[tuple[str, str], ...] = ()
    clock_hour_nouns: tuple[str, ...] = ()


class ItnTimeFst(GraphFst):
    """
    Finite state transducer for classifying spoken times, e.g.
        పది గంటల ముప్పై నిమిషాలు -> time { hours: "10" minutes: "30" }
        పది గంటలకు -> time { hours: "10" suffix: "కు" }
        ఒంటి గంట -> time { hours: "1" }
        పదిన్నర గంటలకు -> time { hours: "10" minutes: "30" suffix: "కు" }

    A bare "X <hour noun>" is a duration, so the hour-only form converts only with a
    suffixed hour noun (a dative) or the unambiguous clock-one pair.
    """

    def __init__(
        self, cardinal: ItnCardinalFst, words: ItnTimeWords, deterministic: bool = True
    ) -> None:
        super().__init__(name="time", kind="classify", deterministic=deterministic)

        profile = cardinal.profile
        lang = profile.lang

        def table_words(name: str) -> pynini.Fst:
            rows = [r for r in load_labels(data_path(lang, f"time/{name}.tsv")) if len(r) >= 2]
            return (
                pynini.invert(pynini.string_map([(k, v) for k, v, *_ in rows])) @ profile.to_ascii
            ).optimize()

        # Any spoken number may head a time; the verbalizer reads an hour above 23 back as
        # a plain number so ఇరవై ఐదు గంటలకు is 25 గంటలకు rather than 20 5:00కు.
        hour_table = table_words("hours")
        one_word = pynini.project(cardinal.words_to_digits @ pynini.accep("1"), "input")
        hour_words = pynini.union(
            cardinal.words_to_digits, cardinal.read(hour_table | pynini.cross(one_word, "1"))
        ).optimize()
        minute_table = table_words("minutes")
        second_table = table_words("seconds")
        if words.minute_one:
            minute_table |= pynini.cross(words.minute_one, "01")
            second_table |= pynini.cross(words.minute_one, "01")
        minute_words = cardinal.read(minute_table)
        second_words = cardinal.read(second_table)

        def suffixed(pairs: tuple[tuple[str, str], ...]) -> pynini.Fst:
            if not pairs:
                return pynini.Fst()
            return (
                pynutil.insert(' suffix: "') + pynini.string_map(list(pairs)) + pynutil.insert('"')
            )

        hour_plain = pynutil.delete(pynini.union(*words.hour_nouns))
        minute_plain = pynutil.delete(pynini.union(*words.minute_nouns))
        second_plain = pynutil.delete(pynini.union(*words.second_nouns))

        hours = pynutil.insert('hours: "') + hour_words + pynutil.insert('"')
        minutes = pynutil.insert(' minutes: "') + minute_words + pynutil.insert('"')
        seconds = pynutil.insert(' seconds: "') + second_words + pynutil.insert('"')

        graph_h = hours + delete_space + suffixed(words.hour_suffixed)
        clock_noun = pynini.Fst()
        if words.clock_hour_nouns:
            clock_noun = delete_space + pynutil.delete(pynini.union(*words.clock_hour_nouns))
            graph_h |= hours + clock_noun
        if words.hour_one is not None:
            one, noun = words.hour_one
            graph_h |= (
                pynutil.insert('hours: "')
                + pynini.cross(one, "1")
                + pynutil.insert('"')
                + delete_space
                + pynutil.delete(noun)
            )
        graph_hm = (
            hours
            + delete_space
            + hour_plain
            + delete_space
            + minutes
            + delete_space
            + (minute_plain | suffixed(words.minute_suffixed))
        )
        graph_hms = (
            hours
            + delete_space
            + hour_plain
            + delete_space
            + minutes
            + delete_space
            + minute_plain
            + delete_space
            + seconds
            + delete_space
            + (second_plain | suffixed(words.second_suffixed))
        )
        # Hour and minute with no hour noun between them, as ASR often renders a clock
        # time: పది ముప్పై గంటలకు -> 10:30కు. The dative is required, so a bare pair stays a number.
        graph_hm_bare = (
            hours + delete_space + minutes + delete_space + suffixed(words.hour_suffixed)
        )
        graph_hs = (
            hours
            + delete_space
            + hour_plain
            + delete_space
            + seconds
            + delete_space
            + (second_plain | suffixed(words.second_suffixed))
        )

        graph = graph_hms | graph_hm | graph_hs | graph_h | pynutil.add_weight(graph_hm_bare, 0.1)

        # Half- and quarter-hour idioms: పదిన్నర గంటలకు -> 10:30, സവാ ദസ് ബജേ -> 10:15,
        # പത്തേമുക്കാൽ മണിക്ക് -> 10:45. Bare "Xన్నర గంటలు" is a duration (2.5 hours), so the
        # clock reading needs a dative or a clock noun.
        minutes_of = {"5": "30", "25": "15", "75": "45"}
        half_rows = [r for r in half_form_rows(lang) if r[2] in minutes_of and int(r[1]) <= 23]
        if half_rows:
            half_words = pynini.union(
                *[
                    pynini.cross(w, f'hours: "{ip}" minutes: "{minutes_of[fp]}"')
                    for w, ip, fp in half_rows
                ]
            )
            tails = delete_space + suffixed(words.hour_suffixed)
            if words.half_glued_suffixes:
                tails |= (
                    pynutil.insert(' suffix: "')
                    + pynini.string_map(list(words.half_glued_suffixes))
                    + pynutil.insert('"')
                )
            if words.clock_hour_nouns:
                tails |= clock_noun
            graph |= half_words + tails

        graph += pynutil.insert(" preserve_order: true")
        self.fst = self.add_tokens(graph).optimize()
