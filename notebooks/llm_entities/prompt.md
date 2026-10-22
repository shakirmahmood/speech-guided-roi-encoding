# Prompt to identify objects and their importance

A prompt that tells the model how to find the object(s) each moment of speech points to, built from docs/design/importance_clues/speech_clues_explained.md (Parts 1-8)

**Not decided, needs Shakir:**

- Field names are v1's (`objects`, `look_at`, `left_out`, `search_for`, `frame_time`, `main_clue`, ...), still proposals, not in the glossary. `search_for` stands in for the plain-description field whose name is open.
- The `left_out` reasons and `main_clue` values are v1's. Reported speech is told to use "past" or "elsewhere" rather than adding a new value.
- Timing (Part 5) is only partly covered: the model picks a moment inside the sentence. A start and end time for each object would need new fields; not added.

---

## The prompt

You help a video encoder decide where to spend detail. Viewers look where the speech sends them: at the object being named, pointed at, praised or warned about. The encoder will make those objects sharper and the rest of the picture softer. Your job is to find, which objects in the video the speech points to, how strongly and the time duration of the importance.

Watch and listen to the whole attached video before answering. Use both the words and the sound of the voice. The words give strong hints, but the video has the last word. For the complete context, you will need to use both the audio and what is visibile to the viewers to identify the objects and their importance accurately which are visually grounded.

### What to do

2. **List the objects** the speech refers to: anything you could point at in a video frame. Decide which objects a viewer would look at because of what is said (sections A to H below), and how strongly. List each object once, however many times and in however many ways it is referred to. Pronouns and names are not objects: they belong to the object they refer to. If a part of something is talked about on its own, list the part separately.
4. **Time**: Give the start and end time of the object when you deem it to be important.

### A. Which object does the speech point to?

People rarely name things plainly. Work out what each phrase points to, in these ways:

- **Named**: "the dog", "a red car", "the Eiffel Tower". Search the picture for it.
- **Named by a proper name**: "Sarah", "Max". The name says who, not what they look like. Link the name to an object on screen using the rest of the video: who introduced themselves, who answers to it, who the camera shows when it is said.
- **Named vaguely**: "the animal", "that thing", "the stuff". Match the general word to the one object on screen that fits what else is said and shown.
- **Pointed at**: "it", "she", "them", "this one", "over here". Find what it stands for: look back in the speech for the last object that fits ("grab the hammer, now swing it": "it" is the hammer), ahead when the name comes later ("here it comes, the train!"), or at the picture for what the speaker is holding, touching, pointing at or looking at ("this one"). "This" and "that" often never get a name; then only the picture can answer.
- **One among several**: "the one in red", "the tall guy", "the second jar", "the cup next to the laptop". Pick the one object the words single out, not all objects of that kind.
- **A group**: "all the birds", "both of them", "the vegetables". Make one entry for the group and list the objects it stands for under `members`.
- **A part**: "its tail", "the wheel", "her hands". The part is what matters, not the whole object. Find the whole first, then the part within it.
- **Implied, never named**: an action brings its participants with it. "She's sawing" means a saw and the board being cut; "he's typing" means the keyboard and his hands. And sometimes the word is not the thing meant: "the room smells amazing" is about the food or flowers in it, not the room.
- **The speaker or the person spoken to**: "I", "my shoes", "John, look at this". "I" and "my" mean the person talking and their belongings, so work out who is talking and where they are on screen. "You" often means the viewer, who is not on screen; but in an instruction the speaker is demonstrating ("hold your pen like this", "watch your fingers"), it means the hands or objects the speaker is using, which are on screen.
- **Text or a graphic**: "as the chart shows", "read the sign", "the price is on the label". The chart, sign, caption or label is the object.
- **Nothing named**: "Look!", "Wow!", "Wait for it…", "Oh no!", a gasp, a laugh. The speech says something notable is happening but not what. Find it in the picture: whatever is moving, being shown or held up, or suddenly appearing at that moment. Use `key` "new" if it is not in your objects list.

### B. Is the object on screen now?

Hearing an object's name does not mean it is in the picture. For every mention, ask whether this object is actually here now. These signs say it is **not**, so put it under `left_out` with the reason:

- **Another time** ("past", "future"): "the dog caught one yesterday", "tomorrow we'll paint the fence". The tense   is about the event, not the object: if the brush for tomorrow is in view and the speaker is showing it, it is here. If the footage itself shows the past (a flashback, a replay), what it shows is here.
- **A kind of thing, not this one** ("general"): "dogs are loyal", "a guitar has six strings". A statement about a whole category says nothing about the one in the frame.
- **Imagined** ("hypothetical"): "if you had a dog…", "imagine a huge wave", "you could use a drill", "I'd rather lose a minute than a thumb". Objects in an imagined, wished-for, feared or possible event are not here, **even when an object of the same kind is visible**: a thumb may be on screen, but "lose a thumb" is about a thumb that might get hurt, not one to look at. A warning about the real object now is different: "keep your thumb clear of the blade" is about the thumb on screen, and it matters.
- **Said to be missing** ("absent"): "there's no lid", "without the guard".
- **Somewhere else** ("elsewhere"): "my dog back home", "in the other room", "at the shop".
- **Not meant literally** ("figure_of_speech"): "raining cats and dogs", "a piece of cake", "a couch potato".
- **From someone else's words**: "she told me the box was heavy". Use "past" or "elsewhere", whichever fits; if the object is in view and being shown, it is here.
- **Can't be seen at all**: "the idea", "freedom", "the economy", "the plan". These are not objects; don't list them anywhere.

Signs that it **is** here: "here's…", "this is…", "as you can see", "meet…", "look at…". "This one" leans towards something close and visible, "that one" towards something farther away, but people mix them up.

In the end, check the picture: if the object is clearly visible and it is talked about at that time instance, it is on screen whatever the tense; if it is nowhere in the frame, it is not, whatever the speaker says.

### C. How much does it matter? (attention)

A speech often mentions several objects, and they don't deserve the same attention at a time instance. Give each one "high", "medium" or "low".

**high**: the speech sends the viewer's eyes to it:

- The speaker tells us to look or warns about it: "look at", "watch", "check out", "see that?", "notice", "the key part is", "here's the trick", "careful with…".
- It is what is talked about: usually the grammatical subject ("**The eagle** dives for the fish"). In a longer phrase the main word counts, not the words describing it: in "the bowl of cherries" the bowl is meant.
- **Speaker rule.** Narrators keep saying "I", "we" and "you" while describing what they do to something else. In "**I**'ll tighten the last bolt now" the eye goes to the bolt, not the speaker. In "**we** usually stop just short of the line" the eye goes to where the cut stops. So when the subject is the speaker, "we", or "you" meaning the viewer, the object the action is done to is the main one. The speaker is "high" only when the speech is about the speaker: how they look, what they wear, what happens to them ("I just cut my hair", "I'm soaked!", "look at my new jacket").
- The speech puts it in the spotlight: "it's **the striker** who scored", "that painting, I love", or the answer after a question ("What's in the box? **A kitten!**").
- It is chosen in a contrast: "not the cat, **the dog**". The rejected one is "low" or left out.
- It is singled out by a comparison: "the **biggest** one", "the **only** one with a lid".
- It is newly introduced and shown: "here's **my new drone**".
- The speaker reacts strongly to it: "beautiful", "gross", "perfect", "**so** cool", "absolutely stunning".
- It is the item of a list being named or shown right now ("you'll need a ruler, a pencil and tape": each in turn).
- It is what "Look!", "Wow!", a gasp or a laugh reacts to.
- The voice stresses it: "take the **red** one".

**medium**: talked about in the speech but not the focus: the object of the action when something else is the subject; a part, belonging or feature of the main object that is mentioned but not pointed at ("she has a bright scarf"); the tool in the hands while the speech is about what it works on; an object mentioned again that is still being talked about.

**low**: only implied (the saw in "she's sawing", unless it is the point); a landmark used only to find another object ("the cup **next to the laptop**": the laptop); a place or background ("in the bushes"); the speaker when they are only narrating and are on screen.

These signs add up: "look at **this** beautiful bird" has a command to look, a pointing word and praise, so the bird is clearly "high"; "the bird is on the fence" has only the subject.

### D. Where on screen is it?

Use words about place to pick the right object, especially when there are several similar objects or the object is small:

- **A place in the frame**: "on the left", "top right", "in the background".
- **Next to another object**: "under the table", "behind the door". Find the landmark first, then look around it. The landmark is only a guide ("low").
- **Relative to the speaker**: "behind me", "in my hand", "to my right". When the speaker faces the camera, their right is the left side of the picture.
- **Size and distance**: "tiny", "way off in the distance" (small, often near the horizon), "up close" (large).
- **Direction of motion**: "coming toward us", "flying off to the left".

### E. When does it matter?

- Viewers look at a named object about a fifth of a second after the word starts. Choose `frame_time` at or just after the moment the object is named, pointed at or shown, as long as it is clearly visible then. If it is not visible at that moment, choose the nearest moment in the speech when it is.
- Check that the frame you describe is really the one at `frame_time`: after a camera cut, the same object is in a different place and size.
- "Right now", "here it is": the moment of speaking.
- "Watch what happens next", "wait for it", "in a second": the object matters before the event and until it
  happens.
- "Did you see that?!", "that was close": the speaker reacts after the event. If it is no longer visible, mark it not on screen.
- "First…, then…, finally…": attention moves from one object to the next in that order.
- The verb form says where the action is: "is catching" (now), "caught" (done), "is about to catch" (soon).

### F. What is happening?

- An action brings its participants: who does it, what it is done to, what it is done with. Include participants that are on screen even if they are not named ("she's pouring" → the jug and the glass), usually as "medium" or "low", and higher when the action is the point of the speech.
- When the action happens before the object is named ("now let's cut…"), the thing about to be cut already
  matters.
- Hands working on an object ("grab", "press", "hold it like this", "cut along the line"): the hands and what they
  hold are the centre of attention. Treat the hands as a part of the person.
- Something changing ("it's melting", "turning brown", "watch it pop"): the changing part is what to look at.
- Something moving from place to place ("throws the ball to her", "put it in the box"): the moving object, and
  where it lands.
- The result ("see how smooth it is now", "look how even these are"): the finished object or the changed part is
  "high".

### G. What is meant but not said?

Use what you know about the world and the situation:

- Everyday situations come with familiar objects: "Goal!" means the ball and the net; "the kettle's whistling"
  means the kettle.
- Hints: "Careful!" means a visible danger (a blade, an edge, a hot surface); "well, that didn't go as planned"
  means something visibly failed (a spill, a collapse). Find it.
- Sarcasm: "oh great, just perfect" after a mishap is about the thing that went wrong. The tone of voice usually
  gives it away.
- Why the speaker is talking: in an advert, the product; in a lesson, the thing being explained or demonstrated;
  in a review, the item being judged and its features; in a story, the characters and what happens to them.
- In a conversation, the person talking, and the listener's face when something surprising is said.
- Don't add an object only because the video as a whole is about it; add it when this speech refers to it, even indirectly.

### H. How is it said?

You can hear the voice, so use it:

- **Stress**: the stressed word is the one that matters ("it's the **dog**, not the cat").
- **Sounds without words**: laughter, gasps, screams, "ooh". Something notable is happening now; find what.
- **Whispering or shouting**: a delicate or urgent moment; attention rises.
- **Pauses**: a pause before a reveal ("and the winner is…") means something important is about to be shown.
- **Speed**: slowing down for emphasis marks the part that matters.
- **Feeling in the voice**: amazed or disgusted means something on screen is worth reacting to.
- **Hesitation**: "pass me the, uh, the clamp": something new or hard to name is coming.

### How to describe an object for the search (`search_for`)

A separate tool will find and outline the object in every frame from a short description, and it only
understands how things look. So `search_for` describes what the object looks like on screen, not what the speaker
calls it:

- 1 to 4 words, ending in a common noun: "brown dog", "silver laptop", "red jacket".
- Not names, brands, roles or jargon: "Max" → "golden retriever", the Twitter logo → "blue bird icon", "the
  referee" → "man in striped shirt", "the carburettor" → "metal engine part".
- Not purpose or feelings: "the gift" → "wrapped box", "the winner" → "tallest trophy".
- For a part, say what it belongs to: "dog's tail", not "tail".
- For one among several of the same kind, add what tells it apart: "red mug", "mug on the left".
- For text or a graphic: "bar chart", "street sign", "price label".

### Output

Answer only with one JSON object, in a single code block, with these fields.

objects: a list, one item per object:
- id: a short, unique, lowercase name for it
- description: a short description of it
- first_mention: where it is first mentioned: "\<time\>:\<words\>"
- also_called: every other word or phrase in the speech that refers to it, except bare pointing words ("this", "that")
- members: only for a group: the ids of the objects it stands for; otherwise leave this field out
- importance: a list, one item per a one importance segment:
  - start, end: when it is important, in seconds from the start of the video, with one decimal
  - exact_spoken_word: the exact word/s spoken
  - reason: one short sentence: why the viewer looks at it now
  - key: the id of the object in your objects list; use "new" only for an object that is not in the list
  - description: 2 or 3 words description of how the object looks
  - on_screen: "yes", "no" or "unsure", from the video
  - attention: "high", "medium" or "low", as in section C
  - main_clue: how the speech points to it: "named", "pronoun", "name", "pointing", "implied" or "other"

### Example of the format

```json
{
  "objects": [
    {"id": "", "description": "", "first_mention": "", "also_called": [], "members":[], "importance": [{start_time:"", end_time: "", exact_spoken_word: "", reason: "", key:"", description: "", on_screen:"", attention:"", main_clue: "" }]},
    {"id": "", "description": "", "first_mention": "", "also_called": [], "members":[], "importance": [{start_time:"", end_time: "", exact_spoken_word: "", reason: "", key:"", description: "", on_screen:"", attention:"", main_clue: "" }]},
    {"id": "", "description": "", "first_mention": "", "also_called": [], "members":[], "importance": [{start_time:"", end_time: "", exact_spoken_word: "", reason: "", key:"", description: "", on_screen:"", attention:"", main_clue: "" }]}
  ],
}
```

---

## Adapting for Qwen

The rule sections A to H, the `search_for` rules and the decision examples carry over unchanged. For Qwen's two
steps (text-only object list, then one call per sentence with a few frames): step 1 takes "What to do" item 2 and
section A; step 2 takes sections A to G with "the frames" in place of "the video", drops section H (no sound) and
asks for boxes only (no mask).

## Testing

No paid call has been made. Free option: paste the prompt into gemini.google.com with the Ratatouille minute, as
for v1, and score with reviews/argon_ratatouille/score_argon.py. Through the API, one Ratatouille run is about
$0.25-0.40 (from plans/argon_whole_video_plan.md). Ratatouille is near the ceiling (15/16 already), so the 2-3 new
clips with answer keys would show more.
