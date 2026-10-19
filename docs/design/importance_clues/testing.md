# Testing the clues

How to test the step that picks the important objects from the speech (currently an LLM reading the
transcript and a few frames per sentence; `notebooks/llm_entities/` on exp/llm-entities). Testing the whole
system, such as quality at equal bitrate, is in [_design.md](../_design.md) §6.

The tests are built around the clue files in this folder, so the results say which clues the model
handles, not just one total score.

## What can be tested on the model

The model only sees the transcript and frames, so only clues it can read are tested here.

| Clue file and group | Testable? | Why |
|---|---|---|
| [linguistic_clues.md](linguistic_clues.md) A, B, C, F, G | Yes | The prompt asks the model to read these. |
| linguistic_clues.md D (where on screen) | Partly | The output has no location field. The only place a location can show up is the short description used to find the object (`search_for`). The test is whether "the knife on the left" keeps "on the left" there. |
| linguistic_clues.md E (when) | Not yet | The output has no time span; every answer applies to its whole sentence. |
| linguistic_clues.md H (how it's said) | No | A transcript has no stress, loudness or tone. Needs audio features first. |
| [visual_clues.md](visual_clues.md), [sound_clues.md](sound_clues.md) | No | These come from separate tools (face, motion, sound event detection) and are tested with those tools. |
| [context_clues.md](context_clues.md) | Partly | Genre and the ongoing topic can be tested by using clips of different genres (level 2). |

## Level 1: one clue at a time

**Idea.** Keep the video the same and change only the text the model reads. Take the real transcript of a
clip and rewrite one sentence so that one clue is added or removed. Everything else stays word for word, so
any change in the model's answer comes from that clue. In linguistics, two sentences that differ in only one
feature are called **minimal pairs**.

**Rules.**

1. **One sentence changes per variant.** The rest of the transcript is the original.
2. **The changed sentence keeps the original timing**, so the model sees the same frames for it.
3. **The changed sentence must fit what is on screen at that moment.** "Slice the tomato with the knife"
   goes where a tomato and a knife are visible. Otherwise the test is about a mismatch between speech and
   picture, not about the clue.
4. **Text only.** No audio is recorded; the model gets the written transcript with times.
5. **Only the changed sentence is scored.**

**Examples** (Ratatouille clip):

| Group | Sentence 1 | Sentence 2 | Right answer |
|---|---|---|---|
| A, which object | "Grab the zucchini. Now slice *it*." | "Grab the zucchini. Now slice *the tomato*." | "it" is the zucchini; the second is the tomato |
| B, on screen now? | "Slice the tomato with the knife." | "*If you're not careful* you'll cut your finger with the knife." | The finger is looked at in 1; in 2 it is left out as hypothetical |
| B | "Here's the eggplant." | "My grandmother *used to grow* eggplant." | On screen in 1; left out as past in 2 |
| C, how much | "*Look at* the mandolin." | "I put the mandolin down." | Higher attention for the mandolin in 1 than in 2 |
| C | "Not the squash, *the zucchini*." | "The squash and the zucchini." | Zucchini higher than squash in 1; both equal in 2 |
| F, actions | "Now she's slicing." (no tool named) | "Now she's slicing with the mandolin." | The mandolin is found as an implied object in 1 |
| G, implied | "Careful!" (knife near fingers) | "Okay." | Fingers or knife raised in 1; nothing in 2 |

**Size.** About 5 to 10 pairs per group (A, B, C, F, G), so 30 to 50 pairs in all. Each pair has its right
answer written down with it, before the model is run.

**Score.** For each group, the number of pairs the model got right, for example "B: 9 of 10, C: 6 of 10".
This shows which clues the model handles and which it misses.

## Level 2: real clips

Made-up sentences are cleaner than real speech. They show whether the model reacts to a clue, not how well
it does on real videos, so real clips are still needed.

- **4 to 6 clips of different genres**, chosen with [docs/test_videos/](../../test_videos/README.md),
  plus one control with little to look at (for example a podcast).
- **Answer keys written by a person**, in `notebooks/llm_entities/answer_keys/`. If possible two people
  write each key separately and compare; where people disagree, the model is not counted wrong.
- **Each sentence in the key is marked with the clue groups it contains** (for example "B, hypothetical"),
  so real clips can also be scored per clue group.
- **Scored with `score.py`**: whether the right main object was picked in each sentence, and how many
  objects were listed that should not have been.

## Level 3: where people actually look

The real test of the idea is whether viewers look at the objects the model marks as most important.

- **Data:** eye-tracking recordings of videos with speech. Coutrot2 and DIEM have both.
- **Check:** after each sentence, does viewers' gaze land on the objects the model marked as most important
  more often than on other objects?
- **Comparison:** a visual saliency model that ignores the speech. If the model does no better than that,
  the speech adds nothing.

## Rules for every test run

- **Run each test 3 times.** Runs are not deterministic, so a difference of 1 or 2 sentences can be noise.
- **Compare prompt or model versions only on the same test set**, with the answer keys fixed.
- **Record the time per minute of video** next to the score.

## Needed before starting

- An answer key for the clip checked by a person (for the Ratatouille clip, `gold_ratatouille.yaml`).
- Level 1 needs `run.py` to accept a written transcript with times instead of transcribing the clip.
