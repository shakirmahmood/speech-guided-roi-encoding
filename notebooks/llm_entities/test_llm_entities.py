"""Tests for the parts that need no model, GPU or video. Run from the repository root with
`make test`; skipped if ollama or pydantic is not installed (pip install -e ".[llm]"). The Gemini
tests use a fake Google client (no paid calls) and need google-genai (pip install -e ".[gemini]").
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
HAVE_GEMINI = (
    HAVE_LLM
    and importlib.util.find_spec("google") is not None
    and importlib.util.find_spec("google.genai") is not None
)
if HAVE_LLM:
    sys.path.insert(0, HERE)
    import answer_format
    import frames
    import prompts
    import run
    import score
    import steps
    import transcript
    from models import gemini, reply
    from models import ollama as model


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

    def test_group_answer_credits_its_members(self):
        found = {"vegetables": "primary", "tomatoes": "minor", "squash": "primary"}
        score.credit_members(found, {"vegetables": ["tomatoes", "squash", "eggplant"]})
        self.assertEqual(
            found,
            {"vegetables": "primary", "tomatoes": "primary", "squash": "primary", "eggplant": "primary"},
        )
        found = {"tomatoes": "minor"}
        score.credit_members(found, {"vegetables": ["tomatoes"]})
        self.assertEqual(found, {"tomatoes": "minor"})


def interaction(iid, text="", inp=1000, cached=0, thought=0, out=10):
    usage = SimpleNamespace(
        total_input_tokens=inp,
        total_cached_tokens=cached,
        total_thought_tokens=thought,
        total_output_tokens=out,
    )
    return SimpleNamespace(id=iid, output_text=text, usage=usage, status="completed")


class FakeInteractions:
    """Stands in for client().interactions: records each request, answers from a list."""

    def __init__(self, answers):
        self.answers, self.requests = list(answers), []

    def create(self, **request):
        self.requests.append(request)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


@unittest.skipUnless(HAVE_GEMINI, "needs google-genai")
class TestGemini(unittest.TestCase):
    def setUp(self):
        gemini._starts.clear()
        self.answer = answer_format.things_answer(answer_format.load_format())
        self.ok = json.dumps({"things": [thing("knife")]})
        self.messages = [
            {"role": "system", "content": "rules"},
            {"role": "user", "content": "example"},
            {"role": "assistant", "content": "{}"},
            {"role": "user", "content": "transcript"},
        ]

    def run_calls(self, answers, calls=1, think=True):
        fake = FakeInteractions(answers)
        client = SimpleNamespace(interactions=fake)
        with (
            mock.patch.object(gemini, "client", return_value=client),
            mock.patch("sys.stderr", new_callable=lambda: open(os.devnull, "w")),
        ):
            replies = [
                gemini.call_model(
                    self.messages + [{"role": "user", "content": f"sentence {i}"}],
                    self.answer,
                    "gemini-4-argon",
                    0,
                    think,
                )
                for i in range(calls)
            ]
        return replies, fake.requests

    def test_messages_become_turns(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg") as f:
            f.write(b"jpeg")
            f.flush()
            system, turns = gemini.to_turns(
                self.messages + [{"role": "user", "content": "s", "images": [f.name]}]
            )
        self.assertEqual(system, "rules")
        self.assertEqual(
            [t["type"] for t in turns],
            ["user_input", "model_output", "user_input", "user_input"],
        )
        self.assertEqual(
            turns[-1]["content"][1],
            {"type": "image", "data": "anBlZw==", "mime_type": "image/jpeg"},
        )

    def test_calls_continue_from_one_starting_interaction(self):
        replies, requests = self.run_calls(
            [interaction("start"), interaction("a", self.ok), interaction("b", self.ok)],
            calls=2,
        )
        start, first, second = requests
        self.assertEqual(start["input"][-1]["content"][0]["text"], gemini.READY)
        self.assertNotIn("previous_interaction_id", start)
        for r in (first, second):
            self.assertEqual(r["previous_interaction_id"], "start")
            self.assertEqual(len(r["input"]), 1)  # only the call's own message
            self.assertEqual(r["system_instruction"], "rules")
            self.assertEqual(r["generation_config"]["thinking_level"], "high")
            self.assertEqual(r["response_format"]["mime_type"], "application/json")
        self.assertTrue(all(r["store"] for r in requests))
        self.assertEqual(replies[0].usage["interaction_ids"], ["start", "a"])
        self.assertEqual(replies[1].usage["interaction_ids"], ["b"])
        self.assertEqual(replies[1].answer.things[0].id, "knife")

    def test_unusable_answer_is_retried_and_every_try_counted(self):
        replies, requests = self.run_calls(
            [interaction("start"), interaction("a", '{"things": ['), interaction("b", self.ok)],
            think=False,
        )
        self.assertEqual(requests[2]["generation_config"], {"thinking_level": "low", "seed": 101})
        self.assertEqual(replies[0].usage["interaction_ids"], ["start", "a", "b"])
        self.assertEqual(replies[0].usage["input_tokens"], 3000)

    def test_full_messages_sent_if_start_refused(self):
        from google.genai import errors

        refused = errors.APIError(400, {"error": {"message": "no"}})
        _, requests = self.run_calls(
            [interaction("start"), refused, interaction("a", self.ok)]
        )
        self.assertNotIn("previous_interaction_id", requests[2])
        self.assertEqual(len(requests[2]["input"]), 4)

    def test_gemini_names_go_to_gemini(self):
        import models

        with mock.patch.object(gemini, "call_model", return_value="g") as call:
            self.assertEqual(models.call_model([], None, "gemini-4-argon", 0, True), "g")
        call.assert_called_once()

    def test_cost_from_settings_prices(self):
        counts = {"input_tokens": 1000, "cached_tokens": 400, "thinking_tokens": 200, "output_tokens": 100}
        # 600 fresh x $2 + 400 cached x $0.10 + 300 written x $10, per million tokens
        self.assertAlmostEqual(gemini.cost(counts, "gemini-4-argon"), 0.00424)

    def test_total_usage(self):
        a = {"interaction_ids": ["x"], "input_tokens": 5, "cost_usd": 0.5}
        b = {"interaction_ids": ["y"], "input_tokens": 2, "cost_usd": None}
        self.assertEqual(
            reply.total_usage([a, {}, a]),
            {"interaction_ids": ["x", "x"], "input_tokens": 10, "cost_usd": 1.0},
        )
        self.assertIsNone(reply.total_usage([a, b])["cost_usd"])
        self.assertIsNone(reply.total_usage([b, a])["cost_usd"])


if __name__ == "__main__":
    unittest.main()
