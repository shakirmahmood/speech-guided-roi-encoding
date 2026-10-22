# What the "Which thing?" clues tell us

An explanation of table A in `docs/design/importance_clues/linguistic_clues.md`, written 2026-10-20 for
Shakir. The nine points below together cover all 16 rows of the table.

## The question the table answers

Before we can decide how important an object is, we first have to know **which object the speaker is
talking about**. That is all table A does. It doesn't rank anything; the later tables do that. It only links
words in the speech to an object in the frame, the referent.

This sounds easy, but people rarely name things plainly. They say "it", "this one", "the one on the left",
or nothing at all. Each row of the table is a different way speech can point at an object, and each needs a
different kind of work to find the right object on screen. Going from easy to hard:

## 1. The object is named

*"The dog", "a red car", "Sarah", "the Eiffel Tower".*

The speech names the object directly, so we can search the frame for it. This is the easiest case. A proper
name like "Sarah" is harder than it looks, though: the word tells us who, but not what she looks like. To
find her, the system needs some link between the name and an appearance, for example knowing she is the
person who introduced herself earlier, or the only woman on screen.

## 2. The object is named only vaguely

*"The animal", "that thing", "the stuff".*

The word gives a category or a placeholder, not a specific object. "The animal" could be any animal in the
frame. The system has to match the general word to one object on screen, using what else is said and what
is visible.

## 3. The object is pointed at instead of named

*"It jumped", "she's laughing", "this one", "over here", "here it comes, the train!"*

Words like "it", "she" and "this" mean nothing on their own. To find out what they stand for, we look:

- **back in the speech**, for the last object that fits ("grab the zucchini, now slice it": "it" is the
  zucchini);
- **ahead in the speech**, when the name comes later ("here it comes, the train!");
- **at the picture**, for what the speaker is holding, pointing at or looking at ("this one").

"This" and "that" are often never named at all, so the picture is the only way to resolve them.

## 4. The object is described among several similar ones

*"The one in red", "the tall guy", "the cup next to the laptop", "the second jar".*

Here the frame holds several objects of the same kind, and the words pick out one by its colour, size,
position or order. Sometimes the words mean a group or a number instead of one object: "all the birds",
"both of them". When a second object is used to find the first ("the cup next to the laptop"), that second
object is only a landmark. It helps the search but matters less than the cup itself.

## 5. Only part of an object is meant

*"Its tail", "the wheel", "her hands".*

The speech refers to a piece of something larger. The important region is that part, not the whole object.
So the system must first find the whole (the dog, the car, the person) and then the part within it.

## 6. The object is never named at all

*"She's slicing" → the knife, the food and her hands. "He scored!" → the ball, the net, the player.
"The kitchen smells amazing" → the food.*

The object is implied, not said. An action brings its tools and participants with it: slicing needs
something to cut and something to cut with. And sometimes the word used is not the thing meant: "the
kitchen smells amazing" is about the food, not the room. Finding these needs general knowledge of how
actions and situations work.

## 7. The speaker or the person spoken to

*"I", "look at my shoes", "John, look at this", "you".*

These words point at people in the conversation. "I" and "my shoes" mean the speaker and their belongings,
so we need to know who is talking and where they are on screen. "John, look at this" means the person being
addressed. "You" is tricky: in a video it often means the viewer, who isn't on screen at all, so there is
nothing to find.

## 8. Text or a graphic on screen

*"As the chart shows", "read the sign".*

The referent is writing or a drawing: a chart, a caption, a sign, a label. It is a region of the picture
rather than a physical object, and it needs to be sharp enough to read.

## 9. Something matters, but nothing is named

*"Look!", "Wow, gorgeous!", "Wait for it…"*

The speech tells us **when** something important is happening, but not **what** it is. There is no word to
link to any object. The picture has to answer the "what": whatever is moving, being shown or held, or
suddenly appearing at that moment.

## Examples from the Ratatouille clip

- "We'll slice **them**": a pronoun (point 3) that means the four vegetables named earlier.
- "**This device** here": pointed at (point 3); the mandolin he is touching.
- "Be very careful with **your fingers**": a part (point 5) of the speaker (point 7).
- "And we're going for eighth of an inch slices": the zucchini and the mandolin are implied by the slicing
  (point 6).
