
# Accuracy report

## Test set

12 essays, hand-built, roughly 100-150 words each:
- 6 written by hand (personal, human) — `dataset/human_*.txt`
- 6 written to imitate typical AI-generated admissions-essay style
  (heavy on stock transitions, uniform sentence rhythm, generically
  positive) — `dataset/ai_*.txt`

**Limitation of this dataset, stated plainly**: it's small (12 essays)
and I wrote both the human and AI examples myself rather than sourcing
real submitted essays or generating the AI ones from an actual language
model. This was a time-constrained choice, not an ideal one. It means the
"AI" essays may be somewhat exaggerated/stereotyped versions of real AI
output — genuinely careful AI writing (or AI writing edited by a human
afterward) would likely be harder to catch than what's in this test set.
It also means the detector hasn't been tested against essays from
non-English-first speakers, which is exactly where these kinds of
detectors are known to misfire (see below).

## Method

Each essay is scored on three whole-essay signals — sentence-length
uniformity, stock-transition-phrase density, and local vocabulary
variety — combined into a single 0–1 likelihood score (see
`essay_level_score()` in `detector.py`). Essays scoring ≥0.5 are
classified "AI"; below that, "human." Per-sentence flags (shown in the
UI) use a stricter rule requiring 2+ independent signals on the same
sentence, so they under-flag compared to the essay-level score — that's
intentional, since the per-sentence view is meant to point at specific
suspicious spots, not serve as the primary classifier.

## Result

**10/12 correct (83.3%)** on this test set.

| File | True label | Predicted | Score |
|---|---|---|---|
| ai_1.txt | AI | AI | 0.88 |
| ai_2.txt | AI | **human (wrong)** | 0.47 |
| ai_3.txt | AI | AI | 0.64 |
| ai_4.txt | AI | AI | 0.65 |
| ai_5.txt | AI | AI | 0.66 |
| ai_6.txt | AI | **human (wrong)** | 0.50 |
| human_1–5.txt | human | human | 0.00 |
| human_6.txt | human | human | 0.14 |

## The two misses, and why

**`ai_2.txt`** (score 0.47) and **`ai_6.txt`** (score 0.50) were both
written to be a slightly "better" imitation of AI writing — still using
stock transitions ("Moreover," "Furthermore") but with more sentence-length
variety than the other AI examples (lengths ranged more, so the
length-uniformity signal, which is weighted 40% of the score, didn't fire
as strongly). Both essays sit right at the classification boundary
(0.47 and 0.50 against a 0.5 threshold) rather than being wildly missed —
which suggests the detector is picking up a real but soft signal, not
randomly guessing. A slightly more sophisticated AI writer (or a human
lightly editing AI output to vary sentence length) would likely evade
this detector at its current threshold.

## Known false-positive risk: non-native English writers

Per the brief's explicit warning, I did not have real ESL-written essays
to test against in the time available, but the mechanism is worth naming
honestly: a non-native English speaker who writes with more formal,
textbook-learned transitions ("Moreover," "In conclusion") and more
uniform sentence construction (a common feature of writing learned via
formal grammar instruction rather than native immersion) would likely
trigger both the transition-phrase and sentence-uniformity signals for
reasons that have nothing to do with AI use. This is a real limitation of
this detector's design, not a hypothetical one — the two signals doing
most of the classification work here are exactly the signals most likely
to conflate "formally taught English" with "AI-generated." If this were
taken further, the fix would be to weight these signals against a
baseline built from a diverse, labeled human corpus rather than fixed
thresholds, so the detector adapts to what "normal" looks like for a given
writer rather than assuming one global norm.