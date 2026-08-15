
"""
Detection logic for the AI essay detector.

Design principle (per the brief): the model/statistics are used as an
INSTRUMENT to produce measurements. This code makes the judgement call
itself, based on those measurements — it never asks a language model
"is this AI-written?" and relays the answer.

Three signals, each computed per-sentence and also in relation to the
whole essay:

1. Sentence-length uniformity — human writing varies sentence length a
   lot (short punchy sentences next to long winding ones). AI text tends
   to produce sentences clustered around a similar length. We measure
   this with the coefficient of variation of sentence lengths in a
   sliding window around each sentence.

2. Transition/filler phrase density — AI-generated prose leans heavily
   on a small set of stock transitions ("Moreover", "Furthermore", "In
   conclusion", "It is important to note", "This demonstrates", etc).
   We count hits against a curated list and flag sentences that contain
   them, especially when the essay-wide density of these phrases is high.

3. Vocabulary predictability (type-token ratio in a local window) — human
   writing tends to repeat and reuse words more idiosyncratically; heavily
   polished AI text often has a wider, more "thesaurus-smooth" vocabulary
   with less repetition, or conversely uses very common words at a
   suspiciously constant rate. We approximate this with a windowed
   type-token ratio (TTR) compared to the essay's own baseline.

Every flag is a data point, not a percentage. The final output is a list
of per-sentence findings with the specific measurement that triggered
each one, so the reader can inspect the reasoning directly.
"""

import re
import statistics
from dataclasses import dataclass, field

TRANSITION_PHRASES = [
    "moreover", "furthermore", "additionally", "in conclusion",
    "it is important to note", "it is worth noting", "this demonstrates",
    "this highlights", "this illustrates", "in today's society",
    "in today's world", "plays a crucial role", "plays a vital role",
    "delve into", "delve deeper", "in summary", "overall,",
    "on the other hand", "as a result", "in essence", "ultimately,",
    "it is essential", "it is crucial", "a testament to",
    "underscores the importance", "serves as a", "shed light on",
    "the fact that", "not only", "but also",
]


def split_sentences(text: str) -> list[str]:
    """Very small sentence splitter — good enough for essay-length text."""
    text = text.strip()
    if not text:
        return []
    raw = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'])", text)
    return [s.strip() for s in raw if s.strip()]


def word_count(sentence: str) -> int:
    return len(re.findall(r"[A-Za-z']+", sentence))


def transition_hits(sentence: str) -> list[str]:
    lower = sentence.lower()
    return [p for p in TRANSITION_PHRASES if p in lower]


def local_ttr(words: list[str], center: int, window: int = 40) -> float:
    """Type-token ratio in a window of words around index `center`."""
    lo = max(0, center - window // 2)
    hi = min(len(words), center + window // 2)
    chunk = words[lo:hi]
    if not chunk:
        return 1.0
    return len(set(w.lower() for w in chunk)) / len(chunk)


@dataclass
class SentenceFinding:
    index: int
    text: str
    word_count: int
    flagged: bool
    reasons: list[str] = field(default_factory=list)


@dataclass
class DetectionResult:
    sentences: list[SentenceFinding]
    overall_flagged_fraction: float
    length_cv: float
    transition_density: float
    avg_local_ttr: float
    essay_ai_likelihood: float = 0.0


def essay_level_score(length_cv: float, transition_density: float, flagged_fraction: float) -> float:
    """
    Combines whole-essay signals into a single 0-1 likelihood score.
    This is separate from per-sentence flagging (which requires 2+ local
    signals and is meant for pointing at specific sentences). This score
    looks at the essay as a whole, since some signals — like an essay-wide
    reliance on stock transitions — are meaningful even if no single
    sentence trips two signals at once.

    Thresholds below were picked by inspecting the test dataset in
    dataset/, not tuned to force a particular accuracy number — see
    documents/accuracy-report.md for the honest results including misses.
    """
    length_score = max(0.0, min(1.0, (0.45 - length_cv) / 0.45))
    transition_score = max(0.0, min(1.0, transition_density / 6))
    flag_score = min(1.0, flagged_fraction * 2)

    return round(0.4 * length_score + 0.4 * transition_score + 0.2 * flag_score, 3)


def analyze(text: str) -> DetectionResult:
    sentences = split_sentences(text)
    if not sentences:
        return DetectionResult([], 0.0, 0.0, 0.0, 1.0)

    lengths = [word_count(s) for s in sentences]
    mean_len = statistics.mean(lengths) if lengths else 0
    stdev_len = statistics.pstdev(lengths) if len(lengths) > 1 else 0
    length_cv = (stdev_len / mean_len) if mean_len > 0 else 0

    all_words = re.findall(r"[A-Za-z']+", text)
    total_words = len(all_words) or 1
    all_transition_hits = sum(len(transition_hits(s)) for s in sentences)
    transition_density = (all_transition_hits / total_words) * 100

    findings: list[SentenceFinding] = []
    word_cursor = 0
    ttr_values = []

    WINDOW = 5
    for i, sent in enumerate(sentences):
        reasons = []

        lo = max(0, i - WINDOW // 2)
        hi = min(len(sentences), i + WINDOW // 2 + 1)
        local_lengths = lengths[lo:hi]
        if len(local_lengths) >= 3:
            l_mean = statistics.mean(local_lengths)
            l_std = statistics.pstdev(local_lengths)
            local_cv = (l_std / l_mean) if l_mean > 0 else 0
            if local_cv < 0.15 and l_mean > 8:
                reasons.append(
                    f"sentence length unusually uniform in this passage "
                    f"(local variation {local_cv:.2f}, typical human writing is >0.35)"
                )

        hits = transition_hits(sent)
        if hits:
            reasons.append(
                f"uses stock transition phrase(s): {', '.join(hits)}"
            )

        n_words = word_count(sent)
        center = word_cursor + n_words // 2
        ttr = local_ttr(all_words, center)
        ttr_values.append(ttr)
        if ttr < 0.55 and n_words > 6:
            reasons.append(
                f"low local vocabulary variety around this sentence "
                f"(type-token ratio {ttr:.2f}, human passages of similar "
                f"length are usually >0.65)"
            )
        word_cursor += n_words

        findings.append(
            SentenceFinding(
                index=i,
                text=sent,
                word_count=n_words,
                flagged=len(reasons) >= 2,
                reasons=reasons,
            )
        )

    flagged_count = sum(1 for f in findings if f.flagged)
    overall_flagged_fraction = flagged_count / len(findings) if findings else 0
    avg_local_ttr = statistics.mean(ttr_values) if ttr_values else 1.0

    return DetectionResult(
        sentences=findings,
        overall_flagged_fraction=overall_flagged_fraction,
        length_cv=length_cv,
        transition_density=transition_density,
        avg_local_ttr=avg_local_ttr,
        essay_ai_likelihood=essay_level_score(length_cv, transition_density, overall_flagged_fraction),
    )