# Outputs of Variants

## Current

> python3 try_variants.py $V --variant current --out runs/current.json

```
transcribing 59.8 s of audio with faster-whisper small.en ...

PROMPT (things, goal-v4 / look_at-4)

--- 1. system: instructions ---
You are given the transcript of a video. Make a list of the concrete things the speech
refers to: anything you could point at in a picture, such as an object, a person, an
animal, food or a plant. Later steps will look for these things in the video.

Read the whole transcript first. Then list each thing once, however many times and in
however many ways it is referred to. Pronouns and names are not things themselves: they
belong to the thing they refer to. Leave pointing words ("this", "that") out: later steps
can see what is pointed at.
If a part of something is talked about on its own, list it separately.

List a thing whether or not it is likely to be in the video; later steps decide that.
Do not list things meant in general, places or directions, or figures of speech.

For each thing give:
id: a short, unique, lowercase name for it
what: a short description of it
first_mention: where it is first mentioned: "<sentence number>: <words>"
also_called: every other word or phrase in the transcript that refers to it, except
bare pointing words ("this", "that")

Answer only with the JSON.

--- 2. user: example transcript ---
Full transcript of the video (for context):
1 [0.00-1.10 s] This is Luna.
2 [1.30-4.60 s] Cats usually hate water, but look at her paws in the bowl, isn't that funny?
3 [4.80-6.00 s] My other cat is at the vet today.

--- 3. assistant: example answer ---
{python3 try_variants.py $V $T --variant labels  --think --out runs/labels_think.json
transcribing 59.8 s of audio with faster-whisper small.en ...

1 There are four distinct vegetables in a ratatouille.   (79.0 s)
  primary   [ratatouille] words='ratatouille' search='the dish being prepared'

2 We've got roma tomatoes, yellow squash, Japanese eggplant, and zucchini.   (32.6 s)
  primary   [roma_tomatoes] words='roma tomatoes' search='two small red round tomatoes sitting on the right side of the wooden board'
  primary   [yellow_squash] words='yellow squash' search="two yellow vegetables being held in the person's hands in the center"
  primary   [japanese_eggplant] words='Japanese eggplant' search='two purple elongated vegetables standing upright in the middle'
  primary   [zucchini] words='zucchini' search='two green elongated vegetables lying on the left side of the board'

3 We'll slice them using a fairly dangerous tool called a mandolin.   (76.7 s)

4 This device here causes a lot of injuries in the kitchen, so be careful.   (52.1 s)
  primary   [mandolin] words='This device here' search='a white mandolin slicer held in hands'

5 And we're going for eighth of an inch slices.   (192.4 s)
  primary   [fingers] words='slices' search='vegetable slices being cut on the table'
  minor     [mandolin] words='' search='white mandolin slicer tool'
  minor     [zucchini] words='' search='green vegetable being sliced'

6 This is just right.   (78.8 s)
  primary   [zucchini] words='This' search="the zucchini slice held between the person's fingers"

7 Be very careful with your fingers if you slice using one of these without a guard.   (113.6 s)
  primary   [mandolin] words='these' search='the white mandolin slicer tool on the counter'
  secondary [fingers] words='fingers' search="the viewer's or cook's fingers holding the vegetable"
  secondary [guard] words='guard' search='the safety guard attachment for the mandolin'

8 I tend to always end early.   (116.0 s)
  minor     [mandolin] words='' search='white mandolin slicer tool'
  minor     [zucchini] words='' search='green vegetable being sliced'
  minor     [slices] words='' search='thin green vegetable slices on cutting board'

9 I'd rather buy a few extra vegetables than cut my finger.   (104.0 s)

10 And since the slices tend to get thinner towards the end of each vegetable, it's hard to layer those ones into the ratatouille anyways when you go to build it.   (77.9 s)
  primary   [slices] words='the slices' search='the vegetable slices currently being cut on the mandolin'

11 With my zucchini done, I'll move on now to the yellow squash, which is a little bit firmer and therefore a little bit easier to slice.   (108.5 s)
  primary   [yellow_squash] words='yellow squash' search='the yellow squash being held in the hand'
  minor     [slices] words='' search='the vegetable slices falling onto the cutting board'
  minor     [mandolin] words='' search='the mandolin slicer tool'

12 Now for the two more difficult vegetables.   (60.5 s)
  primary   [japanese_eggplant] words='two more difficult vegetables' search="the Japanese eggplant being held in the person's left hand"
  primary   [roma_tomatoes] words='two more difficult vegetables' search='the red tomatoes sitting on the wooden cutting board'

13 The eggplant is soft, which means it's sometimes a little bit tricky to work with here, but if you use nice, firm pressure, it should be totally fine.   (97.4 s)
  primary   [japanese_eggplant] words='The eggplant' search='a whole purple Japanese eggplant being held in a mandolin slicer'

14 And finally, the tomatoes.   (45.0 s)
  primary   [roma_tomatoes] words='the tomatoes' search='the red tomatoes sitting on the wooden cutting board next to the sliced eggplant'

15 These are soft and watery enough that we'll have to use a knife.   (38.6 s)
  primary   [roma_tomatoes] words='These' search='two red round vegetables held in hands'
  secondary [new] words='knife' search='metal blade tool lying on wooden cutting board'

16 Check the other slices you've done and then take this nice and slow to try to get the most even slices possible.   (105.4 s)
  primary   [guard] words='other slices' search='pile of sliced tomato pieces on the cutting board'

17 To me, tomato's the most frustrating part here, but just remember that the secret to that movie perfect ratatouille is nice even slices.   (78.0 s)
  primary   [roma_tomatoes] words="tomato's" search='red tomato being sliced on a wooden board'
  secondary [ratatouille] words='ratatouille' search='the dish being prepared on a counter'
  secondary [slices] words='slices' search='thin vegetable slices on a wooden cutting board'

saved runs/labels_think.jsonpython3 try_variants.py $V $T --variant labels  --think --out runs/labels_think.json
transcribing 59.8 s of audio with faster-whisper small.en ...

1 There are four distinct vegetables in a ratatouille.   (79.0 s)
  primary   [ratatouille] words='ratatouille' search='the dish being prepared'

2 We've got roma tomatoes, yellow squash, Japanese eggplant, and zucchini.   (32.6 s)
  primary   [roma_tomatoes] words='roma tomatoes' search='two small red round tomatoes sitting on the right side of the wooden board'
  primary   [yellow_squash] words='yellow squash' search="two yellow vegetables being held in the person's hands in the center"
  primary   [japanese_eggplant] words='Japanese eggplant' search='two purple elongated vegetables standing upright in the middle'
  primary   [zucchini] words='zucchini' search='two green elongated vegetables lying on the left side of the board'

3 We'll slice them using a fairly dangerous tool called a mandolin.   (76.7 s)

4 This device here causes a lot of injuries in the kitchen, so be careful.   (52.1 s)
  primary   [mandolin] words='This device here' search='a white mandolin slicer held in hands'

5 And we're going for eighth of an inch slices.   (192.4 s)
  primary   [fingers] words='slices' search='vegetable slices being cut on the table'
  minor     [mandolin] words='' search='white mandolin slicer tool'
  minor     [zucchini] words='' search='green vegetable being sliced'

6 This is just right.   (78.8 s)
  primary   [zucchini] words='This' search="the zucchini slice held between the person's fingers"

7 Be very careful with your fingers if you slice using one of these without a guard.   (113.6 s)
  primary   [mandolin] words='these' search='the white mandolin slicer tool on the counter'
  secondary [fingers] words='fingers' search="the viewer's or cook's fingers holding the vegetable"
  secondary [guard] words='guard' search='the safety guard attachment for the mandolin'

8 I tend to always end early.   (116.0 s)
  minor     [mandolin] words='' search='white mandolin slicer tool'
  minor     [zucchini] words='' search='green vegetable being sliced'
  minor     [slices] words='' search='thin green vegetable slices on cutting board'

9 I'd rather buy a few extra vegetables than cut my finger.   (104.0 s)

10 And since the slices tend to get thinner towards the end of each vegetable, it's hard to layer those ones into the ratatouille anyways when you go to build it.   (77.9 s)
  primary   [slices] words='the slices' search='the vegetable slices currently being cut on the mandolin'

11 With my zucchini done, I'll move on now to the yellow squash, which is a little bit firmer and therefore a little bit easier to slice.   (108.5 s)
  primary   [yellow_squash] words='yellow squash' search='the yellow squash being held in the hand'
  minor     [slices] words='' search='the vegetable slices falling onto the cutting board'
  minor     [mandolin] words='' search='the mandolin slicer tool'

12 Now for the two more difficult vegetables.   (60.5 s)
  primary   [japanese_eggplant] words='two more difficult vegetables' search="the Japanese eggplant being held in the person's left hand"
  primary   [roma_tomatoes] words='two more difficult vegetables' search='the red tomatoes sitting on the wooden cutting board'

13 The eggplant is soft, which means it's sometimes a little bit tricky to work with here, but if you use nice, firm pressure, it should be totally fine.   (97.4 s)
  primary   [japanese_eggplant] words='The eggplant' search='a whole purple Japanese eggplant being held in a mandolin slicer'

14 And finally, the tomatoes.   (45.0 s)
  primary   [roma_tomatoes] words='the tomatoes' search='the red tomatoes sitting on the wooden cutting board next to the sliced eggplant'

15 These are soft and watery enough that we'll have to use a knife.   (38.6 s)
  primary   [roma_tomatoes] words='These' search='two red round vegetables held in hands'
  secondary [new] words='knife' search='metal blade tool lying on wooden cutting board'

16 Check the other slices you've done and then take this nice and slow to try to get the most even slices possible.   (105.4 s)
  primary   [guard] words='other slices' search='pile of sliced tomato pieces on the cutting board'

17 To me, tomato's the most frustrating part here, but just remember that the secret to that movie perfect ratatouille is nice even slices.   (78.0 s)
  primary   [roma_tomatoes] words="tomato's" search='red tomato being sliced on a wooden board'
  secondary [ratatouille] words='ratatouille' search='the dish being prepared on a counter'
  secondary [slices] words='slices' search='thin vegetable slices on a wooden cutting board'

saved runs/labels_think.json
"things": [
{
"id": "luna",
"what": "the speaker's cat, Luna",
"first_mention": "1: Luna",
"also_called": [
"her"
]
},
{
"id": "luna_paws",
"what": "Luna's paws",
"first_mention": "2: her paws",
"also_called": []
},
{
"id": "bowl",
"what": "the bowl the paws are in",
"first_mention": "2: the bowl",
"also_called": []
},
{
"id": "other_cat",
"what": "the speaker's other cat, at the vet",
"first_mention": "3: My other cat",
"also_called": []
}
]
}
(sent as a single line of JSON)

--- 4. user: this video's transcript ---
Full transcript of the video (for context):
1 [0.00-2.20 s] There are four distinct vegetables in a ratatouille.
2 [2.34-6.34 s] We've got roma tomatoes, yellow squash, Japanese eggplant, and zucchini.
3 [6.54-9.36 s] We'll slice them using a fairly dangerous tool called a mandolin.
4 [9.60-12.76 s] This device here causes a lot of injuries in the kitchen, so be careful.
5 [12.96-14.68 s] And we're going for eighth of an inch slices.
6 [15.04-16.00 s] This is just right.
7 [16.26-19.50 s] Be very careful with your fingers if you slice using one of these without a guard.
8 [19.70-20.94 s] I tend to always end early.
9 [21.10-23.24 s] I'd rather buy a few extra vegetables than cut my finger.
10 [23.46-30.10 s] And since the slices tend to get thinner towards the end of each vegetable, it's hard to layer those ones into the ratatouille anyways when you go to build it.
11 [30.18-35.68 s] With my zucchini done, I'll move on now to the yellow squash, which is a little bit firmer and therefore a little bit easier to slice.
12 [36.02-37.72 s] Now for the two more difficult vegetables.
13 [37.96-44.22 s] The eggplant is soft, which means it's sometimes a little bit tricky to work with here, but if you use nice, firm pressure, it should be totally fine.
14 [44.42-45.60 s] And finally, the tomatoes.
15 [45.94-48.12 s] These are soft and watery enough that we'll have to use a knife.
16 [48.38-53.04 s] Check the other slices you've done and then take this nice and slow to try to get the most even slices possible.
17 [53.24-59.54 s] To me, tomato's the most frustrating part here, but just remember that the secret to that movie perfect ratatouille is nice even slices.
==============================================================================

THINGS IN THIS VIDEO (14.1 s)
Things in this video (use these ids as key):
ratatouille the dish being prepared (first: 1: ratatouille)
roma_tomatoes roma tomatoes (first: 2: roma tomatoes; also: tomatoes)
yellow_squash yellow squash (first: 2: yellow squash; also: yellow squash)
japanese_eggplant Japanese eggplant (first: 2: Japanese eggplant; also: eggplant)
zucchini zucchini (first: 2: zucchini)
mandolin a mandolin slicer tool (first: 3: mandolin; also: device, these)
slices the vegetable slices being cut (first: 5: slices; also: slices)
fingers the person's fingers (first: 7: fingers)
guard a safety guard for the mandolin (first: 7: guard)

1 There are four distinct vegetables in a ratatouille. (6.1 s)
primary [ratatouille] words='' search='the final dish (not yet visible)'
secondary [roma_tomatoes] words='' search='red tomatoes on the left'
secondary [yellow_squash] words='' search='yellow squash in the middle-left'
secondary [japanese_eggplant] words='' search='purple eggplants in the middle-right'
secondary [zucchini] words='' search='green zucchinis on the right'

2 We've got roma tomatoes, yellow squash, Japanese eggplant, and zucchini. (4.9 s)
primary [roma_tomatoes] words='' search='the red tomatoes in the hands'
primary [yellow_squash] words='' search='the yellow vegetables in the hands'
secondary [japanese_eggplant] words='' search='the purple vegetables on the board'
secondary [zucchini] words='' search='the green vegetables on the board'

3 We'll slice them using a fairly dangerous tool called a mandolin. (7.3 s)
primary [mandolin] words='' search='the white slicer tool in his hand'
secondary [slices] words='' search='the vegetable slices being cut'
minor [japanese_eggplant] words='' search='the purple eggplants on the cutting board'
minor [yellow_squash] words='' search='the yellow squash on the cutting board'
minor [zucchini] words='' search='the green zucchini on the cutting board'
minor [roma_tomatoes] words='' search='the red tomatoes on the cutting board'

4 This device here causes a lot of injuries in the kitchen, so be careful. (4.7 s)
primary [mandolin] words='' search='the white mandolin slicer being held by hands'
secondary [fingers] words='' search="the person's fingers holding the mandolin"

5 And we're going for eighth of an inch slices. (2.9 s)
primary [slices] words='' search='the small round pieces of zucchini on the table'

6 This is just right. (3.9 s)
primary [slices] words='' search='the vegetable slice being held between the fingers'
secondary [zucchini] words='' search='the whole vegetable on the table or the one being sliced'

7 Be very careful with your fingers if you slice using one of these without a guard. (5.8 s)
primary [fingers] words='' search="the person's fingers holding the vegetable"
secondary [mandolin] words='' search='the white mandolin slicer'
minor [guard] words='' search='a safety guard for the mandolin (not present)'

8 I tend to always end early. (3.0 s)
secondary [slices] words='' search='the vegetable slices on the cutting board'

9 I'd rather buy a few extra vegetables than cut my finger. (5.8 s)
primary [fingers] words='' search="the person's fingers"
minor [roma_tomatoes] words='' search='red tomatoes'
minor [yellow_squash] words='' search='yellow squash'
minor [japanese_eggplant] words='' search='purple eggplants'
minor [zucchini] words='' search='green zucchini'

10 And since the slices tend to get thinner towards the end of each vegetable, it's hard to layer those ones into the ratatouille anyways when you go to build it. (3.8 s)
primary [slices] words='' search='the sliced zucchini on the mandolin'
secondary [ratatouille] words='' search='the dish being prepared (not visible in frame)'

11 With my zucchini done, I'll move on now to the yellow squash, which is a little bit firmer and therefore a little bit easier to slice. (3.9 s)
primary [yellow_squash] words='' search='the yellow vegetable being held'
minor [zucchini] words='' search='the green vegetable on the table'

12 Now for the two more difficult vegetables. (4.1 s)
secondary [japanese_eggplant] words='' search='the purple vegetable on the cutting board'
secondary [yellow_squash] words='' search='the pile of sliced yellow vegetables on the cutting board'

13 The eggplant is soft, which means it's sometimes a little bit tricky to work with here, but if you use nice, firm pressure, it should be totally fine. (3.8 s)
primary [japanese_eggplant] words='' search='the purple vegetable being sliced'
secondary [slices] words='' search='the thin, round pieces of eggplant on the board'

14 And finally, the tomatoes. (3.0 s)
primary [roma_tomatoes] words='' search='the red tomatoes on the right side of the board'

15 These are soft and watery enough that we'll have to use a knife. (5.3 s)
primary [roma_tomatoes] words='' search='the red tomatoes in hand or on the board'
minor [slices] words='' search='the vegetable slices on the right side of the board'

16 Check the other slices you've done and then take this nice and slow to try to get the most even slices possible. (6.6 s)
primary [slices] words='' search='the pile of sliced vegetables on the right side of the cutting board'
secondary [roma_tomatoes] words='' search='the red vegetable being cut in the center of the frame'
minor [japanese_eggplant] words='' search='the pile of purple and white vegetable slices on the right'
minor [yellow_squash] words='' search='the pile of yellow vegetable slices on the far right'

17 To me, tomato's the most frustrating part here, but just remember that the secret to that movie perfect ratatouille is nice even slices. (4.6 s)
primary [roma_tomatoes] words='' search='the red vegetable being sliced'
secondary [ratatouille] words='' search='the dish being prepared (implied by context)'
secondary [slices] words='' search='the vegetable slices on the cutting board'

saved runs/current.json
```

## Current (--think enabled)

> python3 try_variants.py $V $T --variant current --think --out runs/current_think.json

```
transcribing 59.8 s of audio with faster-whisper small.en ...
1 There are four distinct vegetables in a ratatouille. (104.4 s)
primary [roma_tomatoes] words='' search='the two red tomatoes on the left'
primary [yellow_squash] words='' search='the yellow squash next to the tomatoes'
primary [japanese_eggplant] words='' search='the purple eggplants in the middle'
primary [zucchini] words='' search='the green zucchinis on the right'

2 We've got roma tomatoes, yellow squash, Japanese eggplant, and zucchini. (50.1 s)
primary [roma_tomatoes] words='' search='red tomatoes in hands or on board'
primary [yellow_squash] words='' search='yellow squash vegetables'
primary [japanese_eggplant] words='' search='purple eggplants on cutting board'
primary [zucchini] words='' search='green zucchinis on cutting board'

3 We'll slice them using a fairly dangerous tool called a mandolin. (111.0 s)
primary [mandolin] words='' search='the mandolin slicer held by the person'
secondary [roma_tomatoes] words='' search='red roma tomatoes'
secondary [yellow_squash] words='' search='yellow squash'
secondary [japanese_eggplant] words='' search='purple Japanese eggplant'
secondary [zucchini] words='' search='green zucchini'

4 This device here causes a lot of injuries in the kitchen, so be careful. (64.2 s)
primary [mandolin] words='' search='the white mandolin slicer held by hands'

5 And we're going for eighth of an inch slices. (70.5 s)
primary [slices] words='' search='small green circular vegetable pieces on the wooden board'
secondary [zucchini] words='' search='green vegetable held in hand on the slicer'
secondary [mandolin] words='' search='white handheld slicing device'

6 This is just right. (71.8 s)
primary [slices] words='' search='the zucchini slice held between fingers'

7 Be very careful with your fingers if you slice using one of these without a guard. (69.0 s)
primary [fingers] words='' search='hands holding the zucchini'
secondary [mandolin] words='' search='white slicer device'

8 I tend to always end early. (78.1 s)
primary [zucchini] words='' search='the green vegetable being held against the slicer'
primary [mandolin] words='' search='the white handheld slicer device'
secondary [slices] words='' search='the pile of round vegetable slices on the board'

9 I'd rather buy a few extra vegetables than cut my finger. (89.6 s)
primary [fingers] words='' search="the person's hands near the mandolin"
secondary [mandolin] words='' search='the slicer on the wooden board'

10 And since the slices tend to get thinner towards the end of each vegetable, it's hard to layer those ones into the ratatouille anyways when you go to build it. (88.2 s)
primary [slices] words='' search='the green vegetable pieces under the mandolin'
secondary [zucchini] words='' search='the green vegetable being pushed through the mandolin'

11 With my zucchini done, I'll move on now to the yellow squash, which is a little bit firmer and therefore a little bit easier to slice. (83.5 s)
primary [yellow_squash] words='' search='yellow vegetable being held and sliced'
secondary [slices] words='' search='pile of thin yellow slices on the wooden board'
secondary [mandolin] words='' search='white slicer tool held against the vegetable'
minor [fingers] words='' search='hands holding the yellow squash and mandolin'

12 Now for the two more difficult vegetables. (114.5 s)
primary [japanese_eggplant] words='' search='purple eggplant held in hand by the speaker'
primary [roma_tomatoes] words='' search='red tomato on the wooden cutting board'

13 The eggplant is soft, which means it's sometimes a little bit tricky to work with here, but if you use nice, firm pressure, it should be totally fine. (100.1 s)
primary [japanese_eggplant] words='' search='purple vegetable being pushed through slicer'
secondary [mandolin] words='' search='white slicer device on cutting board'
minor [fingers] words='' search='hands holding mandolin and eggplant'

14 And finally, the tomatoes. (50.9 s)
primary [roma_tomatoes] words='' search='the red round vegetables on the right side of the wooden board'

15 These are soft and watery enough that we'll have to use a knife. (97.1 s)
primary [roma_tomatoes] words='' search='the red round vegetables in hands or on the board'
secondary [new] words='' search='the small knife on the left side of the cutting board'

16 Check the other slices you've done and then take this nice and slow to try to get the most even slices possible. (100.9 s)
primary [slices] words='' search='vegetable slices on the cutting board and pile'
primary [roma_tomatoes] words='' search='red tomato being cut with a knife'
secondary [fingers] words='' search='hands and fingers holding the tomato'

17 To me, tomato's the most frustrating part here, but just remember that the secret to that movie perfect ratatouille is nice even slices. (103.2 s)
primary [roma_tomatoes] words='' search='the red tomato on the cutting board'
secondary [slices] words='' search='the sliced tomatoes on the cutting board'

saved runs/current_think.json
```

## Generic

> python3 try_variants.py $V $T --variant generic --out runs/generic.json

```
transcribing 59.8 s of audio with faster-whisper small.en ...

1 There are four distinct vegetables in a ratatouille. (16.4 s)
primary [ratatouille] words='ratatouille' search='the wooden cutting board holding all the vegetables'
secondary [roma_tomatoes] words='roma tomatoes' search='two red round tomatoes on the left side of the board'
secondary [yellow_squash] words='yellow squash' search='two yellow squashes in the middle-left of the board'
secondary [japanese_eggplant] words='Japanese eggplant' search='two long purple eggplants in the center of the board'
secondary [zucchini] words='zucchini' search='two green zucchinis on the right side of the board'

2 We've got roma tomatoes, yellow squash, Japanese eggplant, and zucchini. (5.3 s)
primary [fingers] words='roma tomatoes' search="the person's hands holding the red tomatoes"
secondary [yellow_squash] words='yellow squash' search='the two yellow vegetables on the right side of the board'
secondary [japanese_eggplant] words='Japanese eggplant' search='the two purple vegetables in the middle of the board'
secondary [zucchini] words='zucchini' search='the two green vegetables on the left side of the board'

3 We'll slice them using a fairly dangerous tool called a mandolin. (4.6 s)
primary [mandolin] words='mandolin' search="a white handheld mandolin slicer held in the chef's left hand"
secondary [slices] words='slice them' search='the yellow squash, zucchini, and eggplant on the wooden cutting board'

4 This device here causes a lot of injuries in the kitchen, so be careful. (3.7 s)
primary [mandolin] words='This device here' search='a white handheld vegetable slicer being held by two hands'
secondary [fingers] words='injuries' search="the person's fingers holding the mandolin"

5 And we're going for eighth of an inch slices. (3.8 s)
primary [slices] words='slices' search='the small, round green pieces of zucchini falling onto the wooden board'
secondary [zucchini] words='' search='the long green vegetable being held and sliced by the person'

6 This is just right. (3.4 s)
primary [zucchini] words='This' search="the round, green-skinned vegetable slice being held between the person's fingers"

7 Be very careful with your fingers if you slice using one of these without a guard. (4.7 s)
primary [fingers] words='your fingers' search="the person's hand holding the zucchini near the mandolin blade"
secondary [guard] words='without a guard' search='the missing safety attachment on the mandolin slicer'

8 I tend to always end early. (3.9 s)
primary [zucchini] words='end' search='the green vegetable being held and sliced by the person'
secondary [slices] words='' search='the pile of zucchini slices accumulating on the cutting board'

9 I'd rather buy a few extra vegetables than cut my finger. (3.9 s)
primary [zucchini] words='vegetables' search='the green vegetable being held and sliced'
secondary [fingers] words='finger' search="the person's fingers"

10 And since the slices tend to get thinner towards the end of each vegetable, it's hard to layer those ones into the ratatouille anyways when you go to build it. (4.1 s)
primary [slices] words='slices' search='the pile of green circular slices accumulating under the mandolin slicer'
secondary [ratatouille] words='ratatouille' search='the wooden cutting board where the ratatouille will be assembled'

11 With my zucchini done, I'll move on now to the yellow squash, which is a little bit firmer and therefore a little bit easier to slice. (3.9 s)
primary [yellow_squash] words='yellow squash' search='the yellow vegetable being held in the hand and pushed through the slicer'
secondary [zucchini] words='zucchini' search='the pile of already sliced yellow rounds on the cutting board'

12 Now for the two more difficult vegetables. (5.3 s)
primary [japanese_eggplant] words='the two more difficult vegetables' search='a purple eggplant lying on the wooden cutting board next to a red tomato'
secondary [roma_tomatoes] words='the two more difficult vegetables' search='a red tomato lying on the wooden cutting board next to a purple eggplant'

13 The eggplant is soft, which means it's sometimes a little bit tricky to work with here, but if you use nice, firm pressure, it should be totally fine. (4.1 s)
primary [japanese_eggplant] words='eggplant' search='the purple vegetable being held and pushed through the mandolin slicer'

14 And finally, the tomatoes. (4.0 s)
primary [roma_tomatoes] words='tomatoes' search='two red, round vegetables being placed on the wooden cutting board'

15 These are soft and watery enough that we'll have to use a knife. (3.9 s)
primary [roma_tomatoes] words='These' search='two red tomatoes on the wooden cutting board'
secondary [new] words='knife' search='a small paring knife lying on the left side of the wooden cutting board'

16 Check the other slices you've done and then take this nice and slow to try to get the most even slices possible. (4.8 s)
primary [roma_tomatoes] words='this' search="the red tomato being held and sliced by the person's hands in the center of the frame"
secondary [slices] words='other slices' search='the pile of already cut vegetable slices on the right side of the cutting board'

17 To me, tomato's the most frustrating part here, but just remember that the secret to that movie perfect ratatouille is nice even slices. (6.3 s)
primary [roma_tomatoes] words='tomato' search="the red vegetable being held and cut by the chef's hands"
secondary [slices] words='slices' search='the pile of red, circular tomato slices on the wooden cutting board'
minor [ratatouille] words='ratatouille' search='the dish being prepared, implied by the collection of sliced vegetables on the counter'

saved runs/generic.json
```

## Generic (--think enabled)

> python3 try_variants.py $V $T --variant generic --think --out runs/generic_think.json

```
transcribing 59.8 s of audio with faster-whisper small.en ...

1 There are four distinct vegetables in a ratatouille.   (67.4 s)
  primary   [roma_tomatoes] words='vegetables' search='red round tomatoes located on the left side of the cutting board'
  primary   [yellow_squash] words='vegetables' search='yellow squash located next to the tomatoes'
  primary   [japanese_eggplant] words='vegetables' search='purple eggplants located in the middle of the board'
  primary   [zucchini] words='vegetables' search='green zucchinis located on the right side of the cutting board'



2 We've got roma tomatoes, yellow squash, Japanese eggplant, and zucchini.   (43.0 s)
  primary   [roma_tomatoes] words='roma tomatoes' search='two red tomatoes held in hands'
  primary   [yellow_squash] words='yellow squash' search='two yellow squashes held in hands'
  primary   [zucchini] words='zucchini' search='two green zucchinis held in hands'
  secondary [japanese_eggplant] words='Japanese eggplant' search='two purple eggplants standing on the board behind the hands'

3 We'll slice them using a fairly dangerous tool called a mandolin.   (101.5 s)
  primary   [mandolin] words='mandolin' search='white mandolin slicer held in left hand'
  secondary [roma_tomatoes] words='them' search='red tomato on the cutting board'
  secondary [yellow_squash] words='them' search='yellow squash on the cutting board'
  secondary [japanese_eggplant] words='them' search='purple eggplants on the cutting board'
  secondary [zucchini] words='them' search='green zucchini on the cutting board'

4 This device here causes a lot of injuries in the kitchen, so be careful.   (43.9 s)
  primary   [mandolin] words='This device' search='white mandolin slicer held by hands'

5 And we're going for eighth of an inch slices.   (18.4 s)
  primary   [slices] words='slices' search='green circular vegetable pieces lying on the wooden cutting board'

6 This is just right.   (125.9 s)
  primary   [slices] words='This' search='thin green slice of zucchini held between fingers'

7 Be very careful with your fingers if you slice using one of these without a guard.   (96.0 s)
  primary   [mandolin] words='these' search='the white handheld mandolin slicer tool being used to cut the vegetable'
  secondary [fingers] words='fingers' search="the person's fingers holding the green vegetable against the slicer"

8 I tend to always end early.   (142.2 s)
  primary   [slices] words='' search='pile of green circular vegetable slices on the wooden board'
  secondary [zucchini] words='' search='green cylindrical vegetable being held in hand and sliced by mandolin'

9 I'd rather buy a few extra vegetables than cut my finger.   (119.0 s)
  primary   [zucchini] words='vegetables' search='a green zucchini held in hand and on the cutting board'
  secondary [roma_tomatoes] words='' search='red tomatoes on the cutting board'
  secondary [yellow_squash] words='' search='yellow squash on the cutting board'
  secondary [japanese_eggplant] words='' search='purple eggplant on the cutting board'
  minor     [fingers] words='finger' search="the chef's hands and fingers gesturing or holding the vegetable"

10 And since the slices tend to get thinner towards the end of each vegetable, it's hard to layer those ones into the ratatouille anyways when you go to build it.   (75.9 s)
  primary   [slices] words='slices' search='pile of green round slices accumulating under the mandolin blade'
  secondary [zucchini] words='vegetable' search='green zucchini being pushed through the slicer and a whole one lying on the board'

11 With my zucchini done, I'll move on now to the yellow squash, which is a little bit firmer and therefore a little bit easier to slice.   (91.6 s)
  primary   [guard] words='yellow squash' search='yellow vegetable held in hand being sliced by mandolin'
  secondary [mandolin] words='' search='white mandolin slicer tool angled on board'
  secondary [slices] words='' search='yellow circular slices falling onto wooden board'

12 Now for the two more difficult vegetables.   (17.2 s)
  primary   [japanese_eggplant] words='two more difficult vegetables' search='a purple eggplant being held by the chef'
  secondary [roma_tomatoes] words='two more difficult vegetables' search='red tomatoes sitting on the wooden cutting board'

13 The eggplant is soft, which means it's sometimes a little bit tricky to work with here, but if you use nice, firm pressure, it should be totally fine.   (79.4 s)
  primary   [japanese_eggplant] words='The eggplant' search='purple vegetable being held in hand and pushed against the slicer'
  secondary [mandolin] words='' search='white mandolin slicer device on the wooden board'

14 And finally, the tomatoes.   (40.9 s)
  primary   [roma_tomatoes] words='tomatoes' search='two red round vegetables sitting on the right side of the wooden cutting board'

15 These are soft and watery enough that we'll have to use a knife.   (24.0 s)
  primary   [roma_tomatoes] words='These' search='two red tomatoes being held in hands and placed on the wooden cutting board'
  secondary [new] words='knife' search='a small knife lying on the left side of the wooden cutting board'

16 Check the other slices you've done and then take this nice and slow to try to get the most even slices possible.   (93.8 s)
  primary   [roma_tomatoes] words='take this nice and slow' search='red tomato being held in hands and cut with a knife on the wooden board'
  secondary [slices] words="Check the other slices you've done" search='pile of sliced eggplant and yellow squash on the bottom right side of the board'

17 To me, tomato's the most frustrating part here, but just remember that the secret to that movie perfect ratatouille is nice even slices.   (78.3 s)
  primary   [roma_tomatoes] words='tomato' search='red tomato being sliced on a wooden board with a whole tomato nearby'
  secondary [slices] words='slices' search='piles of sliced vegetables including eggplant and squash next to the cutting action'
  minor     [ratatouille] words='ratatouille' search='the dish being prepared represented by the collection of sliced vegetables on the board'

saved runs/generic_think.json

```

## Labels

> python3 try_variants.py $V $T --variant labels --out runs/labels.json

```
transcribing 59.8 s of audio with faster-whisper small.en ...

1 There are four distinct vegetables in a ratatouille.   (11.9 s)

2 We've got roma tomatoes, yellow squash, Japanese eggplant, and zucchini.   (7.5 s)
  primary   [roma_tomatoes] words='roma tomatoes' search="two red roma tomatoes held in the person's hands"
  primary   [yellow_squash] words='yellow squash' search="two yellow squashes held in the person's hands"
  primary   [japanese_eggplant] words='Japanese eggplant' search="two purple Japanese eggplants held in the person's hands"
  primary   [zucchini] words='zucchini' search="two green zucchinis held in the person's hands"

3 We'll slice them using a fairly dangerous tool called a mandolin.   (5.6 s)

4 This device here causes a lot of injuries in the kitchen, so be careful.   (6.4 s)
  primary   [mandolin] words='This device here' search='a white mandolin slicer held in hands'

5 And we're going for eighth of an inch slices.   (4.0 s)
  primary   [slices] words='slices' search='the small, round pieces of zucchini on the wooden cutting board'

6 This is just right.   (4.5 s)
  primary   [zucchini] words='This' search='a single round slice of green-skinned vegetable held between fingers'

7 Be very careful with your fingers if you slice using one of these without a guard.   (6.0 s)
  primary   [mandolin] words='one of these' search='a mandolin slicer tool'
  secondary [fingers] words='your fingers' search="the person's fingers"
  secondary [guard] words='a guard' search='a safety guard for the mandolin'

8 I tend to always end early.   (4.9 s)

9 I'd rather buy a few extra vegetables than cut my finger.   (4.7 s)
  minor     [new] words='finger' search="the speaker's finger"

10 And since the slices tend to get thinner towards the end of each vegetable, it's hard to layer those ones into the ratatouille anyways when you go to build it.   (6.6 s)
  primary   [slices] words='slices' search='the vegetable slices being cut on the mandolin'

11 With my zucchini done, I'll move on now to the yellow squash, which is a little bit firmer and therefore a little bit easier to slice.   (8.2 s)
  primary   [yellow_squash] words='yellow squash' search='a yellow squash being held by the person'

12 Now for the two more difficult vegetables.   (4.4 s)

13 The eggplant is soft, which means it's sometimes a little bit tricky to work with here, but if you use nice, firm pressure, it should be totally fine.   (6.2 s)
  primary   [japanese_eggplant] words='The eggplant' search='the purple vegetable being held and sliced on the mandolin'

14 And finally, the tomatoes.   (3.9 s)
  primary   [roma_tomatoes] words='the tomatoes' search='two red tomatoes on a wooden cutting board'

15 These are soft and watery enough that we'll have to use a knife.   (4.7 s)
  primary   [roma_tomatoes] words='These' search='the two red tomatoes being held and placed on the cutting board'
  secondary [new] words='a knife' search='a small knife lying on the wooden cutting board'

16 Check the other slices you've done and then take this nice and slow to try to get the most even slices possible.   (6.8 s)

17 To me, tomato's the most frustrating part here, but just remember that the secret to that movie perfect ratatouille is nice even slices.   (6.2 s)
  primary   [roma_tomatoes] words="tomato's" search='the red vegetable being sliced on the cutting board'
  primary   [ratatouille] words='ratatouille' search='the dish being prepared, implied by the context of slicing vegetables for it'
  primary   [slices] words='slices' search='the tomato slices being cut on the cutting board'

saved runs/labels.json
```

## Labels (--think enabled)

```
python3 try_variants.py $V $T --variant labels  --think --out runs/labels_think.json
transcribing 59.8 s of audio with faster-whisper small.en ...

1 There are four distinct vegetables in a ratatouille.   (79.0 s)
  primary   [ratatouille] words='ratatouille' search='the dish being prepared'

2 We've got roma tomatoes, yellow squash, Japanese eggplant, and zucchini.   (32.6 s)
  primary   [roma_tomatoes] words='roma tomatoes' search='two small red round tomatoes sitting on the right side of the wooden board'
  primary   [yellow_squash] words='yellow squash' search="two yellow vegetables being held in the person's hands in the center"
  primary   [japanese_eggplant] words='Japanese eggplant' search='two purple elongated vegetables standing upright in the middle'
  primary   [zucchini] words='zucchini' search='two green elongated vegetables lying on the left side of the board'

3 We'll slice them using a fairly dangerous tool called a mandolin.   (76.7 s)

4 This device here causes a lot of injuries in the kitchen, so be careful.   (52.1 s)
  primary   [mandolin] words='This device here' search='a white mandolin slicer held in hands'

5 And we're going for eighth of an inch slices.   (192.4 s)
  primary   [fingers] words='slices' search='vegetable slices being cut on the table'
  minor     [mandolin] words='' search='white mandolin slicer tool'
  minor     [zucchini] words='' search='green vegetable being sliced'

6 This is just right.   (78.8 s)
  primary   [zucchini] words='This' search="the zucchini slice held between the person's fingers"

7 Be very careful with your fingers if you slice using one of these without a guard.   (113.6 s)
  primary   [mandolin] words='these' search='the white mandolin slicer tool on the counter'
  secondary [fingers] words='fingers' search="the viewer's or cook's fingers holding the vegetable"
  secondary [guard] words='guard' search='the safety guard attachment for the mandolin'

8 I tend to always end early.   (116.0 s)
  minor     [mandolin] words='' search='white mandolin slicer tool'
  minor     [zucchini] words='' search='green vegetable being sliced'
  minor     [slices] words='' search='thin green vegetable slices on cutting board'

9 I'd rather buy a few extra vegetables than cut my finger.   (104.0 s)

10 And since the slices tend to get thinner towards the end of each vegetable, it's hard to layer those ones into the ratatouille anyways when you go to build it.   (77.9 s)
  primary   [slices] words='the slices' search='the vegetable slices currently being cut on the mandolin'

11 With my zucchini done, I'll move on now to the yellow squash, which is a little bit firmer and therefore a little bit easier to slice.   (108.5 s)
  primary   [yellow_squash] words='yellow squash' search='the yellow squash being held in the hand'
  minor     [slices] words='' search='the vegetable slices falling onto the cutting board'
  minor     [mandolin] words='' search='the mandolin slicer tool'

12 Now for the two more difficult vegetables.   (60.5 s)
  primary   [japanese_eggplant] words='two more difficult vegetables' search="the Japanese eggplant being held in the person's left hand"
  primary   [roma_tomatoes] words='two more difficult vegetables' search='the red tomatoes sitting on the wooden cutting board'

13 The eggplant is soft, which means it's sometimes a little bit tricky to work with here, but if you use nice, firm pressure, it should be totally fine.   (97.4 s)
  primary   [japanese_eggplant] words='The eggplant' search='a whole purple Japanese eggplant being held in a mandolin slicer'

14 And finally, the tomatoes.   (45.0 s)
  primary   [roma_tomatoes] words='the tomatoes' search='the red tomatoes sitting on the wooden cutting board next to the sliced eggplant'

15 These are soft and watery enough that we'll have to use a knife.   (38.6 s)
  primary   [roma_tomatoes] words='These' search='two red round vegetables held in hands'
  secondary [new] words='knife' search='metal blade tool lying on wooden cutting board'

16 Check the other slices you've done and then take this nice and slow to try to get the most even slices possible.   (105.4 s)
  primary   [guard] words='other slices' search='pile of sliced tomato pieces on the cutting board'

17 To me, tomato's the most frustrating part here, but just remember that the secret to that movie perfect ratatouille is nice even slices.   (78.0 s)
  primary   [roma_tomatoes] words="tomato's" search='red tomato being sliced on a wooden board'
  secondary [ratatouille] words='ratatouille' search='the dish being prepared on a counter'
  secondary [slices] words='slices' search='thin vegetable slices on a wooden cutting board'

saved runs/labels_think.json
```
