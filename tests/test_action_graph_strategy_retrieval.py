from __future__ import annotations

import hashlib
import json
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory

from reasoning_agent.action_graph.config import ActionGraphConfig
from reasoning_agent.action_graph.runtime import ActionGraphRuntime
from reasoning_agent.action_graph.strategy_cards import bound_card_text, build_strategy_cards
from reasoning_agent.strategy_retrieval import (
    EMBEDDING_DIM, EMBEDDING_MODEL_NAME, StrategyRetriever, build_structure_messages,
    ensure_model_weights, get_shared_strategy_retriever, normalize_retrieval_text,
    preferred_device,
)


RESULT = {
    "id": 17,
    "name": "Telescoping Series",
    "tags": ["series"],
    "description": "Turn a sum into endpoint terms.",
    "applicability": ["Adjacent terms cancel."],
    "steps": [{"step": "Expand", "detail": "Check cancellation."}],
    "example": {"problem": "Example problem", "solution": "Example solution"},
    "score": 0.91,
    "raw_score": 0.80,
    "structure_score": 0.94,
}


class StrategyClient:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    def chat(self, messages, **kwargs):
        self.calls.append(messages)
        content = messages[0]["content"]
        if content.startswith("You are a mathematical problem analyzer."):
            return (
                "Domain: algebra\nGoal: compute a sum\nObjects: a finite series\n"
                "Constraints: positive integers\nStructure:\n- adjacent cancellation"
            )
        if "预处理器" in content:
            return json.dumps({"problem_restatement": "求和", "subquestions": []})
        if "题目分类器" in content:
            return json.dumps({"domain": "advanced_olympiad_mathematics", "answer_mode": "computation", "risk_level": "low"})
        if "策略和技能" in content:
            return json.dumps({
                "main_method": "化简", "backup_method": "检验", "proof_obligations": [], "checks": [],
                "skill_domains": [], "skill_sections": [],
                "initial_decision": {"action": "derive", "target_id": "q1", "goal": "求和", "required_fact_ids": [], "success_condition": "得到数值"},
            })
        if content == "你是数学专家。" or "领域的数学专家" in content:
            return "求和为 2。\n<ACTION_RESULT>{\"answer\":\"2\",\"covers\":[\"q1\"]}</ACTION_RESULT>"
        if "局部审核器" in content:
            return json.dumps({"verdict": "accept", "accepted_claims": ["和为2"], "covered_subquestion_ids": ["q1"], "first_fatal_error": "", "repair_instruction": "", "invalidated_claim_ids": []})
        if "答案整理器" in content:
            return "答案为 2"
        raise AssertionError(content)


class FakeRetriever:
    def __init__(self, expected_top_k: int = 2) -> None:
        self.expected_top_k = expected_top_k

    def retrieve_for_structure(self, raw_problem, retrieval_text, *, top_k):
        assert raw_problem == "求一个有限和。"
        assert top_k == self.expected_top_k
        return {"retrieval_text": retrieval_text, "results": [RESULT]}


class ActionGraphStrategyRetrievalTest(unittest.TestCase):
    def test_embedding_protocol_constants_match_local_index_contract(self) -> None:
        self.assertEqual(EMBEDDING_MODEL_NAME, "Qwen/Qwen3-Embedding-0.6B")
        self.assertEqual(EMBEDDING_DIM, 1024)
        self.assertTrue(ActionGraphConfig().action_strategy_retrieval_enabled)
        self.assertEqual(ActionGraphConfig().action_strategy_retrieval_top_k, 2)

    def test_embedding_defaults_to_cpu(self) -> None:
        self.assertEqual(preferred_device(), "cpu")

    def test_structured_query_requires_and_preserves_transition_directionality(self) -> None:
        prompt = build_structure_messages("Count paths with x_i-x_{i+1} in {-1, 19}.")[0]["content"]
        self.assertIn("Directionality:", prompt)
        self.assertIn("Do not infer reverse reachability", prompt)

        normalized = normalize_retrieval_text(
            "Domain: combinatorics\nGoal: count paths\nObjects: coordinate vertices\n"
            "Constraints: x_i-x_{i+1} is -1 or 19\n"
            "Directionality: directed; x_{i+1}=x_i+1 (mod 20)\n"
            "Structure:\n- directed periodic strip"
        )
        self.assertIn("Directionality: directed", normalized)
        self.assertIn("x_{i+1}=x_i+1", normalized)

    def test_cards_are_layered_and_drop_whole_low_rank_cards(self) -> None:
        cards = build_strategy_cards([RESULT], max_chars=10_000)
        self.assertIn("Telescoping Series", cards.planner)
        self.assertNotIn("Example problem", cards.planner)
        self.assertIn("Example problem", cards.executor)
        self.assertIn("Example solution", cards.executor)
        too_small = build_strategy_cards([RESULT], max_chars=1)
        self.assertEqual(too_small.executor, "")
        self.assertTrue(too_small.executor_truncated)
        bounded, truncated = bound_card_text(cards.executor, 20)
        self.assertEqual(bounded, "")
        self.assertTrue(truncated)

    def test_missing_index_is_a_controlled_retriever_error(self) -> None:
        with TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                StrategyRetriever(data_dir=Path(directory), model_dir=Path(directory))

    def test_split_model_is_reconstructed_and_validated_on_first_use(self) -> None:
        payload = b"split embedding model payload"
        with TemporaryDirectory() as directory:
            model_dir = Path(directory)
            part_names = ["model.safetensors.part-000", "model.safetensors.part-001"]
            (model_dir / part_names[0]).write_bytes(payload[:11])
            (model_dir / part_names[1]).write_bytes(payload[11:])
            (model_dir / "model.safetensors.parts.json").write_text(
                json.dumps({
                    "target": "model.safetensors",
                    "size": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "parts": part_names,
                }),
                encoding="utf-8",
            )

            rebuilt = ensure_model_weights(model_dir)

            self.assertEqual(rebuilt.read_bytes(), payload)
            self.assertEqual(ensure_model_weights(model_dir), rebuilt)

    def test_split_model_rejects_corrupt_payload(self) -> None:
        with TemporaryDirectory() as directory:
            model_dir = Path(directory)
            (model_dir / "model.safetensors.part-000").write_bytes(b"wrong")
            (model_dir / "model.safetensors.parts.json").write_text(
                json.dumps({
                    "target": "model.safetensors",
                    "size": 5,
                    "sha256": "0" * 64,
                    "parts": ["model.safetensors.part-000"],
                }),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "integrity"):
                ensure_model_weights(model_dir)
            self.assertFalse((model_dir / "model.safetensors").exists())

    @patch("reasoning_agent.strategy_retrieval.StrategyRetriever")
    def test_shared_retriever_is_created_once_per_resource_and_device(self, retriever_class) -> None:
        with TemporaryDirectory() as directory:
            data_dir = Path(directory) / "data"
            model_dir = Path(directory) / "model"
            first = get_shared_strategy_retriever(
                data_dir=data_dir, model_dir=model_dir, device="test-device",
            )
            second = get_shared_strategy_retriever(
                data_dir=data_dir, model_dir=model_dir, device="test-device",
            )
        self.assertIs(first, second)
        retriever_class.assert_called_once()

    @patch("reasoning_agent.action_graph.runtime.get_shared_strategy_retriever", return_value=FakeRetriever())
    def test_runtime_records_scores_and_actual_cards(self, _retriever) -> None:
        client = StrategyClient()
        config = ActionGraphConfig(action_strategy_retrieval_enabled=True)
        result = ActionGraphRuntime(client, config).run("求一个有限和。")
        event = next(item for item in result["trace"] if item["type"] == "strategy_retrieval_completed")
        data = event["data"]
        self.assertIn("Domain: algebra", data["retrieval_text"])
        self.assertEqual(data["results"][0]["score"], 0.91)
        self.assertEqual(data["results"][0]["raw_score"], 0.8)
        self.assertEqual(data["results"][0]["structure_score"], 0.94)
        self.assertNotIn("Example problem", data["planner_cards"])
        self.assertIn("Example problem", data["executor_cards"])
        selector = next(call for call in client.calls if "策略和技能" in call[0]["content"])
        self.assertIn("Telescoping Series", selector[1]["content"])
        self.assertNotIn("Example solution", selector[1]["content"])
        executor = next(call for call in client.calls if "数学专家" in call[0]["content"])
        self.assertIn("Example solution", executor[1]["content"])
        reflector = next(call for call in client.calls if "局部审核器" in call[0]["content"])
        self.assertNotIn("Example solution", reflector[1]["content"])

    @patch("reasoning_agent.action_graph.runtime.get_shared_strategy_retriever", side_effect=FileNotFoundError("missing"))
    def test_missing_resource_degrades_without_blocking_solution(self, _retriever) -> None:
        result = ActionGraphRuntime(
            StrategyClient(), ActionGraphConfig(action_strategy_retrieval_enabled=True),
        ).run("求一个有限和。")
        self.assertTrue(result["final_response"])
        self.assertTrue(any(item["type"] == "strategy_retrieval_degraded" for item in result["trace"]))

    @patch("reasoning_agent.action_graph.runtime.get_shared_strategy_retriever", return_value=FakeRetriever(1))
    def test_top_k_override_and_trace_card_limit(self, _retriever) -> None:
        result = ActionGraphRuntime(
            StrategyClient(),
            ActionGraphConfig(
                action_strategy_retrieval_enabled=True,
                action_strategy_retrieval_top_k=1,
                action_trace_max_chars=20,
            ),
        ).run("求一个有限和。")
        event = next(item for item in result["trace"] if item["type"] == "strategy_retrieval_completed")
        self.assertTrue(event["data"]["planner_cards_truncated"])
        self.assertTrue(event["data"]["executor_cards_truncated"])
        self.assertEqual(event["data"]["executor_cards"], "")

    def test_strategy_stage_budget_degrades_before_model_call(self) -> None:
        client = StrategyClient()
        result = ActionGraphRuntime(
            client,
            ActionGraphConfig(
                action_strategy_retrieval_enabled=True,
                action_strategy_retrieval_pool_seconds=0,
            ),
        ).run("求一个有限和。")
        self.assertTrue(any(item["type"] == "strategy_retrieval_degraded" for item in result["trace"]))
        self.assertFalse(any(
            call[0]["content"].startswith("You are a mathematical problem analyzer.")
            for call in client.calls
        ))


if __name__ == "__main__":
    unittest.main()
