"""Tests for the parts that need no model, GPU or video. Run from the repository root with
`make test`; skipped if ollama or pydantic is not installed (pip install -e ".[llm]").
"""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
HAVE_LLM = all(importlib.util.find_spec(m) for m in ("ollama", "pydantic"))
if HAVE_LLM:
    sys.path.insert(0, HERE)
    import answer_format
    import frames
    import model
    import prompts
    import run
    import score
    import steps
    import transcript


def thing(tid):
    return {"id": tid, "what": tid, "first_mention": "1: " + tid, "also_called": []}


def entry(key, attention="medium", on_screen="unsure", reason="r"):
    return {
        "reason": reason,
        "key": key,
        "search_for": key,
        "on_screen": on_screen,
        "attention": attention,
        "main_clue": "named",
    }


@unittest.skipUnless(HAVE_LLM, "needs ollama and pydantic")
class TestTranscript(unittest.TestCase):
    def test_words_split_into_sentences(self):
        words = [
            {"start": 0, "end": 1, "word": " Look"},
            {"start": 1, "end": 2, "word": " here."},
            {"start": 2, "end": 3, "word": " Nice!"},
            {"start": 3, "end": 4, "word": " and"},
        ]
        self.assertEqual(
            transcript.sentences_from_words(words),
            [
                {"start": 0.0, "end": 2.0, "text": "Look here."},
                {"start": 2.0, "end": 3.0, "text": "Nice!"},
                {"start": 3.0, "end": 4.0, "text": "and"},
            ],
        )

    def test_load_transcript_both_layouts(self):
        segs = [
            {"start": 0, "end": 1, "text": " Hi. "},
            {"start": 1, "end": 2, "text": ""},
        ]
        for data in (segs, {"transcript": segs}):
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
                json.dump(data, f)
            try:
                self.assertEqual(
                    transcript.load_transcript(f.name),
                    [{"start": 0.0, "end": 1.0, "text": "Hi."}],
                )
            finally:
                os.unlink(f.name)


@unittest.skipUnless(HAVE_LLM, "needs ollama and pydantic")
class TestFrames(unittest.TestCase):
    def test_times_spread_over_the_sentence(self):
        self.assertEqual(frames.frame_times(10, 13, 3, 60), [10.5, 11.5, 12.5])

    def test_times_stay_inside_the_video(self):
        self.assertEqual(frames.frame_times(59, 61, 2, 60), [59.5, 59.95])


@unittest.skipUnless(HAVE_LLM, "needs ollama and pydantic")
class TestAnswerFormat(unittest.TestCase):
    def setUp(self):
        self.fmt = answer_format.load_format()

    def test_key_must_be_a_thing_id_or_new(self):
        answer = answer_format.sentence_answer(self.fmt, ["knife"])
        answer(look_at=[entry("knife"), entry("new")], left_out=[])
        with self.assertRaises(Exception):
            answer(look_at=[entry("spoon")], left_out=[])

    def test_attention_strongest_first(self):
        self.assertEqual(
            answer_format.attention_order(self.fmt), ["high", "medium", "low"]
        )


@unittest.skipUnless(HAVE_LLM, "needs ollama and pydantic")
class TestPrompts(unittest.TestCase):
    def setUp(self):
        self.fmt, self.text = answer_format.load_format(), prompts.load_prompt()
        self.transcript = prompts.format_transcript(
            [{"start": 0, "end": 1, "text": "Look at the knife."}]
        )

    def test_things_prompt_ends_with_the_transcript(self):
        p = prompts.things_prompt(self.fmt, self.text, self.transcript)
        self.assertEqual(p.messages[-1], {"role": "user", "content": self.transcript})
        self.assertIn("goal-v4", p.version)

    def test_sentence_prompt_ends_with_the_things(self):
        p = prompts.sentence_prompt(
            self.fmt, self.text, self.transcript, [thing("knife")]
        )
        self.assertEqual(len(p.messages), 7)
        self.assertIn("knife", p.messages[-1]["content"])
        self.assertEqual(
            p.messages[4]["role"], "assistant"
        )  # the worked example's answer

    def test_sentence_message(self):
        m = prompts.sentence_message(
            2, {"start": 1.0, "end": 2.5, "text": "This one."}, [1.5], ["a.jpg"]
        )
        self.assertEqual(
            m["content"],
            "Sentence to analyse: 2 [1.00-2.50 s] This one.\n"
            "Frames of sentence 2, in order, at: 1.50 s",
        )
        self.assertEqual(m["images"], ["a.jpg"])


@unittest.skipUnless(HAVE_LLM, "needs ollama and pydantic")
class TestSteps(unittest.TestCase):
    def test_clean_things(self):
        ids = [
            t["id"]
            for t in steps.clean_things(
                [thing("Red Knife"), thing("red knife"), thing("new")]
            )
        ]
        self.assertEqual(ids, ["red_knife", "red_knife_2", "new_thing"])

    def test_merge_keeps_strongest_attention_and_on_screen(self):
        merged = steps.merge_by_key(
            [
                entry("knife", "low", "no", "a"),
                entry("knife", "high", "yes", "b"),
                entry("new"),
                entry("new"),
            ],
            ["high", "medium", "low"],
        )
        self.assertEqual(len(merged), 3)  # new entries stay separate
        self.assertEqual(
            (
                merged[0]["attention"],
                merged[0]["on_screen"],
                merged[0]["reason"],
                merged[0]["merged"],
            ),
            ("high", "yes", "a / b", 2),
        )


@unittest.skipUnless(HAVE_LLM, "needs ollama and pydantic")
class TestModel(unittest.TestCase):
    def test_unusable_answer_is_retried(self):
        answer = answer_format.things_answer(answer_format.load_format())
        replies = [
            SimpleNamespace(
                message=SimpleNamespace(content=c, thinking=""), prompt_eval_count=10
            )
            for c in ('{"things": [', json.dumps({"things": [thing("knife")]}))
        ]
        with (
            mock.patch.object(model, "chat", side_effect=replies) as chat,
            mock.patch("sys.stderr", new_callable=lambda: open(os.devnull, "w")),
        ):
            reply = model.call_model([], answer, "m", 1000, think=False)
        self.assertEqual(reply.answer.things[0].id, "knife")
        self.assertEqual(chat.call_count, 2)
        self.assertEqual(chat.call_args.kwargs["options"]["seed"], 101)

    def test_thinking_uses_qwen_sampling(self):
        self.assertEqual(model.sampling(True, 100)["temperature"], 0.6)
        self.assertEqual(model.sampling(False, 100)["temperature"], 0.0)


@unittest.skipUnless(HAVE_LLM, "needs ollama and pydantic")
class TestRunAndScore(unittest.TestCase):
    def test_defaults_come_from_settings(self):
        a = run.parse_args(["clip.mp4"])
        self.assertTrue(a.think)
        self.assertEqual((a.frames, a.ctx), (3, 16384))
        self.assertFalse(run.parse_args(["clip.mp4", "--no-think"]).think)

    def test_score_reads_run_output(self):
        sent = {"look_at_merged": [{**entry("tomatoes", "high"), "merged": 1}]}
        self.assertEqual(score.targets_of(sent)[0]["strength"], "primary")
        refs = {"tomatoes": ["tomato"], "knife": ["knife"]}
        self.assertEqual(
            score.match({"key": "tomatoes"}, refs, ["tomatoes", "knife"]), "tomatoes"
        )
        self.assertEqual(
            score.match(
                {"key": "new", "search_for": "a sharp knife"}, refs, list(refs)
            ),
            "knife",
        )


if __name__ == "__main__":
    unittest.main()
