
# Essay AI Detector

A working web app that flags likely AI-generated passages in college
admissions essays, with visible reasoning — not a single confidence
percentage.

## How it works

Three measurable signals, computed directly from the text (no language
model asked "is this AI?" — see `detector.py` for the full explanation):

1. **Sentence-length uniformity** — AI prose tends toward suspiciously
   consistent sentence lengths; human writing varies more.
2. **Stock transition-phrase density** — "Moreover," "Furthermore," "In
   conclusion," etc., used at a rate far higher than typical human prose.
3. **Local vocabulary variety** — windowed type-token ratio.

These combine into a per-essay likelihood score, and separately into
per-sentence flags (shown highlighted in the UI, with the specific reason
on hover) when a sentence trips 2+ signals at once.

## Running it

```bash
pip install flask
python app.py
```

Then open `http://localhost:5000`, paste an essay, click Analyze.

## Accuracy

**83.3% (10/12)** on a small hand-built test set — see
`documents/accuracy-report.md` for the full breakdown, including the two
essays it got wrong and an honest discussion of the detector's known
false-positive risk for non-native English writers.

## What this is not

Not a wrapper around a chat model asked to judge AI-ness — that approach
is explicitly unreliable and unexplainable, and the brief calls it out
directly. Every signal here is a direct statistical measurement of the
text, and every flag comes with the specific measurement that triggered it.

## Limitations, stated honestly

- Small test set (12 essays), and I authored both the human and AI
  examples myself due to time constraints — see the accuracy report for
  what that means for how much to trust the number above.
- Two signals (transition density, sentence-length uniformity) are the
  same features associated with formally-taught, non-native English
  writing — a real and known false-positive risk, not addressed by this
  version.
- Sentence splitting is a simple regex, not a proper NLP tokenizer — edge
  cases with abbreviations, quotes, etc. may split incorrectly.