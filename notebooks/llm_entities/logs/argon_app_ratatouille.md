# Gemini 4 Argon on the whole Ratatouille minute, by hand in the Gemini app (2026-10-20, three runs)

**Who / how:** Shakir, in gemini.google.com (Gemini 4 Argon), with the prompt at the end of this file and
`clips/ratatouille_1min.mp4` (the first minute of `data/raw/ratatouille/ratatouille.mp4`), the whole video with
its sound, no transcript. No API call, so no cost. Three runs: run 1 (reasoning level not recorded), run 2
(reasoning level medium) and run 3 (thinking level high). The app adds its own instructions, so these are a first look, not the same as an API
call.

**Answers**, as Argon gave them: [run 1](argon_app_ratatouille_run1.json),
[run 2, medium](argon_app_ratatouille_run2_medium.json), [run 3, high](argon_app_ratatouille_run3_high.json).

**In short:** run 3 (high) was the best of the three, still one sentence short of Qwen on the main object:

| Run | Main object right (16 sentences scored for Qwen) | Any object found (of 41) | Boxes good / rough / wrong spot |
|---|---|---|---|
| Run 1 (level not recorded) | 15 | 37 | 20 / 21 / 7 of 48 |
| Run 2, medium | 13 | 34 | 12 / 21 / 6 of 39 |
| Run 3, high | 15 | 40 | 22 / 21 / 6 of 49 |
| Qwen goal-v4 with thinking (2026-10-16) | 16 | 37 | - |

With one run each, a 1-2 sentence gap is within the run-to-run noise seen with Qwen.

## Run 1: which objects (scored with `score.py` and `answer_keys/gold_ratatouille.yaml`)

Argon splits the speech its own way (19 sentences; faster-whisper gives 17). Each answer-key sentence was matched
to the Argon sentence containing its opening words (any case), then scored with `score.py` unchanged. One
Argon sentence ("And finally, the tomatoes: these are soft ...") covers two key sentences.

| Run | Primary hit | P recall | Any recall | Wrong | Unmatched |
|---|---|---|---|---|---|
| Argon, all 17 key sentences with a primary | 16/17 | 23/25 | 38/42 | 2 | 4 |
| Argon, the same 16 sentences as Qwen | 15/16 | 22/24 | 37/41 | 2 | 4 |
| Qwen goal-v4 with thinking (2026-10-16) | 16/16 | 23/24 | 37/41 | 1 | 1 |

- Before "mandoline" (Argon's spelling) was added to the answer key (commit 789e4eb), Argon scored 14/17: two
  sentences failed on spelling alone.
- **Miss:** "Check the other slices ... take this nice and slow": the tomato slices and the other slices high,
  the tomato being cut only medium. The key wants the tomato. Debatable.
- **Wrong:** "I'd rather buy a few extra vegetables than cut my finger": the fingers high (Qwen does this too)
  and the zucchini stub medium. It did leave out "a few extra vegetables" as hypothetical.
- **Hit that Qwen's run couldn't get:** "but just remember ... nice, even slices", which faster-whisper joins to
  the sentence before.
- **Speech:** Argon's words match the clip's Parakeet transcript (`clips/ratatouille_1min_transcript.json`,
  NVIDIA Parakeet TDT 0.6B v2 with word times), and its sentence starts are 0.0-0.45 s before Parakeet's time for
  the first word (0.22 s early on average).

## Run 1: where (boxes and outlines)

Each box and outline was drawn on the frame at the time Argon gave and checked by eye (one viewer, Claude).
Boxes are [ymin, xmin, ymax, xmax] and outlines are [x, y] points, all on 0-1000 (every outline point lies inside
its box read that way). The pictures are kept out of git (stills from the video).

48 objects located: **20 good** (outline on the object), **21 rough** (near it or partly on it), **7 in the wrong
spot**; one more correctly marked off screen. Outlines are coarse: 4 to 43 points, and the mandoline is always 4.

**Likely cause of the wrong spots:** the position comes from a frame 1-2 s away from the time given. Drawing
six of them at -2 to +2 s, five fit the object 1-2 s earlier or later. Not checked beyond these six; the app may
also read video differently from the API. It matters because SAM 3.1 would start tracking from that box.

| Sentence | Time (s) | Object (Argon's id) | Attention | Check | Note |
|---|---|---|---|---|---|
| 1 | 1.0 | vegetables | high | rough | misses the tomatoes |
| 2 | 2.5 | tomatoes | high | good |  |
| 2 | 3.5 | yellow_squash | high | good |  |
| 2 | 5.0 | eggplant | high | good |  |
| 2 | 6.1 | zucchini | high | wrong spot | fits the zucchini on the counter at 7-8 s |
| 2 | 2.5 | speaker | low | good |  |
| 3 | 8.0 | mandoline | high | rough |  |
| 3 | 8.0 | vegetables | medium | rough |  |
| 3 | 8.0 | speaker | medium | good |  |
| 4 | 10.5 | mandoline | high | good |  |
| 5 | 14.0 | zucchini_slices | high | rough |  |
| 5 | 14.0 | zucchini | low | wrong spot | beside the mandoline, not on the zucchini |
| 5 | 14.0 | mandoline | low | good |  |
| 5 | 14.0 | speaker | low | rough |  |
| 6 | 15.2 | single_zucchini_slice | high | good |  |
| 7 | 17.0 | speaker_fingers | high | wrong spot | fits the fingers holding the slice at 15-16 s |
| 7 | 17.0 | mandoline | medium | good |  |
| 7 | 17.0 | zucchini | low | rough |  |
| 8 | 20.7 | zucchini_end | high | wrong spot | fits the stub in his hand at about 21.7 s |
| 8 | 20.7 | speaker | medium | wrong spot | same outline as sentence 9 (wide shot) on a close-up |
| 9 | 21.2 | speaker_fingers | high | rough |  |
| 9 | 21.2 | speaker | medium | good |  |
| 9 | 22.0 | zucchini_end | medium | wrong spot | fits the zucchini on the board at 24 s |
| 10 | 26.0 | thin_slices | high | rough |  |
| 10 | 26.0 | zucchini_end | medium | rough |  |
| 11 | 31.5 | yellow_squash | high | wrong spot | fits the squash being sliced at 32.5-33.5 s |
| 11 | 31.5 | speaker | low | rough |  |
| 11 | - | zucchini_slices | low | off screen (null) | |
| 12 | 34.0 | yellow_squash | high | rough |  |
| 12 | 34.0 | squash_slices | medium | good |  |
| 12 | 34.0 | mandoline | low | good |  |
| 13 | 36.5 | difficult_vegetables | high | rough |  |
| 14 | 39.0 | eggplant | high | rough |  |
| 14 | 39.0 | mandoline | medium | rough |  |
| 14 | 40.5 | eggplant_slices | medium | good |  |
| 15 | 43.0 | eggplant | high | rough |  |
| 15 | 43.0 | eggplant_slices | medium | good |  |
| 15 | 43.0 | mandoline | low | good |  |
| 16 | 45.2 | tomatoes | high | good |  |
| 16 | 47.2 | knife | high | rough |  |
| 16 | 47.2 | speaker | low | rough |  |
| 17 | 50.0 | other_slices | high | good |  |
| 17 | 50.0 | tomato_slices | high | rough |  |
| 17 | 50.0 | tomatoes | medium | rough |  |
| 17 | 50.0 | knife | medium | good |  |
| 18 | 54.5 | tomatoes | high | rough |  |
| 18 | 54.5 | speaker | low | rough |  |
| 19 | 58.5 | tomato_slices | high | good |  |
| 19 | 58.5 | other_slices | medium | good |  |

## Run 2: reasoning level medium

Scored and checked the same way as run 1, with the same prompt and clip.

| Run | Sentences | Primary hit | P recall | Any recall | Wrong | Unmatched |
|---|---|---|---|---|---|---|
| Run 2, all 17 key sentences with a primary | 16 | 14/17 | 21/25 | 35/42 | 1 | 6 |
| Run 2, the same 16 sentences as Qwen | 16 | 13/16 | 20/24 | 34/41 | 1 | 6 |
| Run 1, the same 16 sentences as Qwen | 19 | 15/16 | 22/24 | 37/41 | 2 | 4 |

- Run 2 joins more sentences at commas (16 instead of 19), so a joined sentence gets one list of objects for two
  answer-key sentences.
- **New misses:** "Be very careful with your fingers": "your fingers" put under left_out as general, so the hand
  by the blade is not marked. "I tend to always end early" (joined with "I'd rather buy ..."): the man high, the
  zucchini stub not listed.
- **Same miss as run 1:** "Check the other slices ... take this nice and slow": slices high, the tomato low.
- **"cut my finger":** the finger medium instead of high (still counted wrong).
- **Speech:** all 242 words match the Parakeet transcript; sentence starts 0.25 s early on average (largest 0.49 s).

**Boxes and outlines:** 39 objects located: **12 good**, **21 rough**, **6 in the wrong spot** (run 1: 20, 21
and 7 of 48); one more correctly marked off screen. Frame times are now mostly whole seconds, but the misplacement
is the same kind: the zucchini and the man at 6.0 s both fit the wide shot that starts at 6.46 s, the same wrong
spot as run 1's zucchini.

| Sentence | Time (s) | Object (Argon's id) | Attention | Check | Note |
|---|---|---|---|---|---|
| 1 | 1.0 | vegetables | high | rough | misses the tomatoes |
| 2 | 2.5 | tomatoes | high | good |  |
| 2 | 3.5 | yellow_squash | high | good |  |
| 2 | 5.0 | eggplant | high | good |  |
| 2 | 6.0 | zucchini | high | wrong spot | same wrong spot as run 1: fits the zucchini in the wide shot that starts at 6.46 s |
| 2 | 6.0 | chef | medium | wrong spot | outline of the man from the wide shot (starts 6.46 s) on the overhead shot |
| 3 | 9.0 | mandoline | high | rough | long band much wider than the mandoline |
| 3 | 8.0 | vegetables | medium | rough |  |
| 3 | 8.0 | chef | medium | rough |  |
| 4 | 11.0 | mandoline | high | good |  |
| 4 | 14.0 | slices | high | rough |  |
| 4 | 13.0 | zucchini | low | wrong spot | two patches beside the mandoline |
| 4 | 13.0 | chef | medium | rough |  |
| 5 | 15.3 | single_slice | high | rough |  |
| 6 | 17.5 | mandoline | medium | good |  |
| 6 | 17.0 | zucchini | low | wrong spot | over the mandoline, not the zucchini |
| 7 | 21.0 | chef | high | good |  |
| 7 | 21.0 | chef_finger | medium | wrong spot | on his upper arm, not his fingers |
| 8 | 25.0 | end_slices | high | rough |  |
| 8 | 26.0 | vegetable_end | medium | rough |  |
| 8 | 26.0 | vegetables | medium | rough |  |
| 9 | 33.0 | yellow_squash | high | rough |  |
| 9 | - | zucchini | medium | off screen (null) | |
| 9 | 33.0 | chef | high | rough |  |
| 9 | 33.0 | mandoline | low | good |  |
| 10 | 36.0 | difficult_vegetables | high | rough |  |
| 11 | 40.0 | eggplant | high | rough |  |
| 11 | 40.0 | mandoline | low | good |  |
| 12 | 45.0 | tomatoes | high | wrong spot | below the tomatoes in his hand |
| 13 | 47.0 | tomatoes | high | good |  |
| 13 | 47.0 | knife | medium | rough |  |
| 13 | 47.0 | chef | medium | rough |  |
| 14 | 50.0 | other_slices | high | good |  |
| 14 | 51.0 | tomato_slices | medium | rough |  |
| 14 | 51.0 | tomatoes | low | rough |  |
| 14 | 51.0 | knife | low | good |  |
| 15 | 54.0 | tomatoes | high | rough |  |
| 15 | 54.0 | chef | medium | rough |  |
| 16 | 58.0 | tomato_slices | high | rough |  |
| 16 | 58.0 | other_slices | medium | good |  |

## Run 3: thinking level high

Scored and checked the same way, with the same prompt and clip.

| Run | Sentences | Primary hit | P recall | Any recall | Wrong | Unmatched |
|---|---|---|---|---|---|---|
| Run 3, all 17 key sentences with a primary | 17 | 15/17 | 22/25 | 41/42 | 2 | 3 |
| Run 3, the same 16 sentences as Qwen | 17 | 15/16 | 22/24 | 40/41 | 2 | 2 |

- Splits the speech almost like faster-whisper (17 sentences); joins "To me, tomato's ..." with "but just
  remember ...".
- **Fixed since run 1:** "Check the other slices ... take this nice and slow": the tomato is now high ("'this'
  refers to the tomato he is slowly slicing"). "Now for the two more difficult vegetables": the eggplant and the
  tomatoes listed separately, both high.
- **Miss:** "I tend to always end early": the man high (the subject "I"), the zucchini stub medium. The prompt's
  rule makes the subject high, so this is the prompt more than the model.
- **Miss (joined sentence):** "but just remember ... nice, even slices": the tomato high, the slices medium (the
  key marks its choice of slices here as debatable). Not among the 16 sentences scored for Qwen.
- **"cut my finger":** the finger medium and the zucchini stub low (both counted wrong; the stub entry is about
  him putting it down, not the hypothetical vegetables).
- **Speech:** every word matches the Parakeet transcript (apart from the spelling "mandoline"); sentence starts 0.08 s
  early on average (largest 0.59 s).

**Boxes and outlines:** 49 objects located: **22 good**, **21 rough**, **6 in the wrong spot**; one more
correctly marked off screen. The two 6 s errors of runs 1 and 2 are gone (the zucchini at 5.0 s and the man at
6.5 s are in the right shot). Still wrong: the fingers (twice), the zucchini twice in close-ups, the man at 20.8 s
drawn from the wide shot that starts at 20.98 s, and the tomatoes at 45.0 s.

| Sentence | Time (s) | Object (Argon's id) | Attention | Check | Note |
|---|---|---|---|---|---|
| 1 | 1.0 | vegetables | high | good | includes the tomatoes this time |
| 2 | 2.5 | tomatoes | high | good |  |
| 2 | 4.0 | yellow_squash | high | good |  |
| 2 | 5.0 | eggplant | high | good |  |
| 2 | 5.0 | zucchini | high | good | right this time: the zucchini on the board |
| 2 | 6.5 | speaker | low | good | right shot this time (6.5 s, after the cut at 6.46 s) |
| 3 | 9.5 | mandoline | high | good |  |
| 3 | 8.0 | vegetables | medium | rough |  |
| 3 | 8.0 | speaker | low | good |  |
| 4 | 11.0 | mandoline | high | rough |  |
| 5 | 14.0 | zucchini_slices | high | rough |  |
| 5 | 13.0 | zucchini | low | wrong spot | beside the zucchini |
| 5 | 14.0 | mandoline | low | rough |  |
| 5 | 14.0 | speaker | low | rough |  |
| 6 | 15.3 | held_zucchini_slice | high | rough |  |
| 7 | 17.0 | mandoline | high | good |  |
| 7 | 17.0 | speaker_fingers | medium | wrong spot | on the blurred background, not the fingers |
| 7 | 17.0 | zucchini | low | wrong spot | between the zucchini and the mandoline |
| 7 | 17.0 | zucchini_slices | low | good |  |
| 8 | 20.8 | speaker | high | wrong spot | outline of the man from the wide shot (starts 20.98 s) on the close-up |
| 8 | 20.8 | zucchini_end | medium | rough |  |
| 9 | 21.0 | speaker | high | good |  |
| 9 | 21.0 | speaker_fingers | medium | wrong spot | on his upper arm, as in run 2 |
| 9 | 22.5 | zucchini_end | low | good | right: the stub being put down on the right |
| 10 | 25.0 | zucchini_slices | high | rough |  |
| 10 | 25.0 | zucchini_end | medium | rough |  |
| 10 | 25.0 | mandoline | low | good |  |
| 11 | 33.0 | yellow_squash | high | rough |  |
| 11 | - | zucchini | medium | off screen (null) | |
| 11 | 34.0 | squash_slices | low | rough |  |
| 11 | 33.0 | mandoline | low | good |  |
| 11 | 33.0 | speaker | low | rough |  |
| 12 | 37.0 | eggplant | high | rough |  |
| 12 | 37.0 | tomatoes | high | good |  |
| 13 | 41.0 | eggplant | high | rough |  |
| 13 | 41.0 | mandoline | low | good |  |
| 13 | 43.0 | eggplant_slices | low | rough |  |
| 14 | 45.0 | tomatoes | high | wrong spot | below the tomatoes in his hand, as in run 2 |
| 15 | 47.0 | tomatoes | high | good |  |
| 15 | 47.0 | knife | medium | good | on the knife this time |
| 15 | 47.0 | speaker | low | rough |  |
| 16 | 51.0 | eggplant_slices | high | good |  |
| 16 | 51.0 | squash_slices | high | rough |  |
| 16 | 51.0 | tomatoes | high | rough |  |
| 16 | 51.0 | tomato_slices | medium | rough |  |
| 16 | 51.0 | knife | low | good |  |
| 17 | 56.0 | tomatoes | high | rough |  |
| 17 | 56.0 | tomato_slices | medium | rough |  |
| 17 | 56.0 | speaker | low | good |  |
| 17 | 56.0 | knife | low | good |  |

## The prompt (Argon prompt v1)

Built from goal-v4 (`config/prompt_goal.yaml`) and look_at-4 (`config/output_format.yaml`), rewritten for one whole
video, plus a time, box and outline per object. The new field names in it are not yet agreed for the glossary.

````text
You help a video encoder decide where to spend detail. Viewers look at what the speech draws their attention to, so the encoder will make those regions sharper.

Watch and listen to the whole attached video, then do the following.

1. LIST THE OBJECTS. List the concrete objects the speech refers to: anything you could point at in a picture, such as a tool, a person, an animal, food or a plant. List each object once, however many times and in however many ways it is referred to. Pronouns and names are not objects themselves: they belong to the object they refer to. If a part of something is talked about on its own, list it separately. Also list objects the speech only points at ("this", "that") or implies ("she's slicing" means the knife and the food). Do not list things meant in general, places or directions, or figures of speech.

2. GO THROUGH THE SPEECH SENTENCE BY SENTENCE, in order, covering every sentence. For each sentence, list the objects a viewer would look at because of what is said in THAT sentence: objects named, referred to by a pronoun, a name, a pointing word ("this", "that") or a gesture, and objects only implied. Use the whole speech to work out what the words refer to, and the picture at that moment to see what is being pointed at. One entry per object, even if the sentence mentions it twice.
Leave out objects that are not here now: in the past or future, somewhere else, hypothetical, about things in general, absent ("there's no lid"), or only a figure of speech ("raining cats and dogs"). List those under left_out with the reason.

3. LOCATE EACH OBJECT TO LOOK AT. For each entry in look_at, pick one moment inside the sentence where the object is clearly visible and give its bounding box and its outline (mask) in that frame. If it is not on screen during the sentence, give null for all three.

OUTPUT: answer only with one JSON object, in a single code block, with these fields.

objects: a list, one item per object:
- id: a short, unique, lowercase name for it
- what: a short description of it
- first_mention: where it is first mentioned: "<sentence number>: <words>"
- also_called: every other word or phrase in the speech that refers to it, except bare pointing words ("this", "that")

sentences: a list, one item per spoken sentence, in order:
- n: the sentence number, from 1
- start, end: when it is spoken, in seconds from the start of the video, with one decimal
- text: the exact words spoken
- look_at: one entry per object the viewer looks at because of this sentence:
  - reason: one short sentence - why the viewer looks at it now
  - key: the id of the object in your objects list; use "new" only for an object that is not in the list
  - search_for: a short visual description to find it in the frame. For a part, say what it belongs to ("the doll's hair", not "hair")
  - on_screen: "yes", "no" or "unsure", from the video
  - attention: "high" - the speaker directs the viewer to it ("look", "watch", "see that"), or it is the subject of the sentence (who or what the sentence is about); "medium" - something else talked about in the sentence: a part, a possession or a feature of the subject that is mentioned but not pointed at ("she has a magical star"); "low" - only implied, or background to what is said
  - main_clue: one of "named", "pronoun", "name", "pointing", "implied", "other"
  - frame_time: the moment you chose, in seconds with one decimal, inside the sentence's start and end; null if not on screen
  - box_2d: the object's bounding box in that frame as [ymin, xmin, ymax, xmax], each from 0 to 1000 relative to the frame size; null if not on screen
  - mask: the object's outline in that frame as a polygon, a list of [x, y] points, each from 0 to 1000 relative to the whole frame; null if not on screen
- left_out: only objects (things, people, animals) mentioned in this sentence but not here now:
  - words: the words used
  - why: one of "past", "future", "elsewhere", "hypothetical", "general", "absent", "figure_of_speech"

EXAMPLE of the format, from another video. Its speech was: (1) "This is Luna." (2) "Cats usually hate water, but look at her paws in the bowl, isn't that funny?" (3) "My other cat is at the vet today." Only sentence 2 is shown, and the example has no picture, so on_screen is "unsure" and frame_time, box_2d and mask are null. Your answer must cover every sentence and locate every object that is on screen.

```json
{
  "objects": [
    {"id": "luna", "what": "the speaker's cat, Luna", "first_mention": "1: Luna", "also_called": ["her"]},
    {"id": "luna_paws", "what": "Luna's paws", "first_mention": "2: her paws", "also_called": []},
    {"id": "bowl", "what": "the bowl the paws are in", "first_mention": "2: the bowl", "also_called": []},
    {"id": "other_cat", "what": "the speaker's other cat, at the vet", "first_mention": "3: My other cat", "also_called": []}
  ],
  "sentences": [
    {
      "n": 2, "start": 1.3, "end": 4.6,
      "text": "Cats usually hate water, but look at her paws in the bowl, isn't that funny?",
      "look_at": [
        {"reason": "The speaker tells the viewer to look at Luna's paws in the water.", "key": "luna_paws",
         "search_for": "the cat's paws", "on_screen": "unsure", "attention": "high", "main_clue": "named",
         "frame_time": null, "box_2d": null, "mask": null},
        {"reason": "Her paws are in it, so it is part of what is being shown.", "key": "bowl",
         "search_for": "water bowl", "on_screen": "unsure", "attention": "medium", "main_clue": "named",
         "frame_time": null, "box_2d": null, "mask": null},
        {"reason": "'her' is Luna, whose paws are being shown.", "key": "luna",
         "search_for": "cat", "on_screen": "unsure", "attention": "medium", "main_clue": "pronoun",
         "frame_time": null, "box_2d": null, "mask": null}
      ],
      "left_out": [{"words": "Cats", "why": "general"}, {"words": "water", "why": "general"}]
    }
  ]
}
```
````
