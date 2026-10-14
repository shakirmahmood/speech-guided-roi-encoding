# Outputs Analysis

This file contains the results of different prompts for different videos. It helps to compare how the model performed accross different prompts and eventually help us decide which prompt is the best for our use.

## Prompts:

### Prompt 1

```text
--- 1. system: instructions ---
You read the full transcript of a video (words only, no pictures).

List every specific physical thing, person or animal the transcript refers to, once each,
however many times and in whatever way it is mentioned (names, pronouns, "that").
A part that is talked about on its own gets its own entry (the truck's wheel).
Do not list things in general ("cats usually hate water") or figures of speech
("raining cats and dogs").

For each thing - one entry per specific thing, person or animal the transcript refers to.
  id:             a short lowercase name, unique in this video, using letters, digits and _
                  only (e.g. truck, truck_wheel).
  what:           a short description of the thing (e.g. "the speaker's old truck, called
                  Rusty").
  first_mention:  its first mention in the transcript, "<sentence number>: <words>".
  also_called:    every other word or phrase in the transcript that refers to it (names,
                  pronouns, "that").

Answer only with the JSON.

--- 2. user: example transcript ---
Full transcript of the video (for context):
  1 [0.00-1.10 s] This is Luna.
  2 [1.30-4.60 s] Cats usually hate water, but look at her paws in the bowl, isn't that funny?
  3 [4.80-6.00 s] My other cat is at the vet today.

--- 3. assistant: example answer ---
{
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
```

#### [Car Mug Keys](../../data/raw/car_mug_keys/video_car.mp4)

```text
1 [0.00-1.60 s] Look at the red mug on the left. (2.6 s)
high [red_mug] search='the red mug on the table' on_screen=yes (named)
The speaker explicitly directs the viewer's attention to the red mug.

2 [2.64-3.82 s] Now watch this little car. (2.5 s)
high [little_car] search='the blue toy car on the table' on_screen=yes (pointing)
The speaker explicitly directs the viewer's attention to the little car.

3 [4.74-5.38 s] There it goes! (3.3 s)
high [little_car] search='the blue toy car on the table' on_screen=yes (pronoun)
The speaker says 'it' referring to the car that was just watched.
high [it] search='the blue toy car on the table' on_screen=yes (pronoun)
'it' refers to the same object as before, which is the little car.

4 [6.50-7.32 s] And those are my keys. (2.5 s)
high [keys] search='a set of keys on the table' on_screen=yes (named)
The speaker explicitly points out the keys as 'my keys'.

5 [8.28-9.52 s] My phone is in the other room. (1.9 s)
left out: 'phone' (elsewhere)
```

#### [Doll School](../../data/raw/doll_school/doll_school.mp4)

<pre>
1 [0.34-1.72 s] My new doll, her name is Sparkle.   (2.8 s)
  high   [sparkle] search='the doll with pink hair being held by the girl in yellow' on_screen=yes (named)
         The speaker introduces the doll and names it.

2 [2.12-4.08 s] She has a magical star that glows in the dark.   (3.3 s)
  <span style="color:red;">high</span>   [magical_star] search="the star on the doll's chest" <span style="color:red;">on_screen=yes</span> (named)
         The speaker introduces the doll's magical star feature.
  <span style="color:red;">medium</span> [sparkle] search='the doll with pink hair' on_screen=yes (pronoun)
         'She' refers to the doll being held and shown.

3 [4.24-5.32 s] No way, let me see that.   (2.6 s)
  high   [sparkle] search='the doll with pink hair' on_screen=yes (pointing)
         The speaker points to the doll and says 'let me see that', directing attention to it.

4 [5.40-6.06 s] Does she fly too?   (2.5 s)
  high   [sparkle] search='the doll with pink hair' on_screen=yes (pronoun)
         The speaker asks if the doll can fly, drawing attention to the doll itself.

5 [6.26-7.98 s] No, but you can style her hair like this.   (3.4 s)
  high   [doll_hair] search="the doll's pink hair" on_screen=yes (pointing)
         The speaker explicitly directs the viewer to look at the doll's hair being styled.
  medium [sparkle] search='the doll with pink hair' on_screen=yes (pronoun)
         'her' refers to the doll, Sparkle, who is the subject of the sentence.

6 [8.32-9.76 s] Whoa, can I try to comb it?   (3.4 s)
  high   [doll_hair] search="the doll's pink hair" on_screen=yes (pronoun)
         The speaker wants to comb the doll's hair.
  medium [sparkle] search='the doll in the center' on_screen=yes (pronoun)
         The action of combing is directed at the doll itself.
  left out: 'magical_star' (general)
</pre>
