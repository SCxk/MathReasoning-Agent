import asyncio
import json
import threading

from agent_platform.tools.isolation import isolated_calculate
from agent_platform.tools.schemas import ARGUMENTS


class LocalTools:
    def __init__(self, retriever=None, *, concurrency=8, documents=None):
        self.retriever = retriever
        self.documents = documents
        self.permits = threading.BoundedSemaphore(concurrency)

    async def invoke(self, name, arguments):
        args = ARGUMENTS[name].model_validate(arguments).model_dump()
        if name == "document_search":
            if self.documents is None:
                return {"status": "failed", "error_code": "unavailable"}
            value = await self.documents.search(args)
            return {"status": "succeeded", "value": value,
                    "citations": [item["chunk_id"] for item in value["passages"]]}
        # Retain capacity until a timed-out thread actually finishes. No local
        # lexical timeout retries, and no accumulating blocked executor threads.
        while not self.permits.acquire(blocking=False):
            await asyncio.sleep(.01)
        if name == "strategy_search":
            def search():
                try:
                    return self.strategy_search(args)
                finally:
                    self.permits.release()
            return await asyncio.to_thread(search)
        try:
            if name == "sympy_calculate":
                return await isolated_calculate(args)
            return await self.math_verify(args)
        finally:
            self.permits.release()

    def strategy_search(self, args):
        from reasoning_agent.lexical_strategy_retrieval import get_shared_lexical_strategy_retriever
        retriever = self.retriever or get_shared_lexical_strategy_retriever()
        retrieved = retriever.retrieve_for_structure(args["query"], None, top_k=args["top_k"],
                                                    metadata={key: args[key] for key in ("domain", "problem_type")})
        version = str(retrieved.get("index_version", "unknown"))[:200]
        matches = [{"strategy_id": str(card["id"])[:200], "title": str(card.get("name", ""))[:300],
                    "summary": (str(card.get("description", "")) + "\n" + json.dumps(card.get("steps", []), ensure_ascii=False))[:2000],
                    "score": float(card["score"]), "source_version": version}
                   for card in retrieved["results"][:args["top_k"]]]
        return {"status": "succeeded", "value": {"matches": matches},
                "citations": [item["strategy_id"] for item in matches]}

    async def math_verify(self, args):
        from reasoning_agent.custom2.program_checks import numeric_equalities
        claims = numeric_equalities(args["candidate"]) if "numeric_equivalence" in args["checks"] else []
        findings, checked, failed = [], [], None
        for claim in claims:
            result = await isolated_calculate({"expression": claim, "operation": "simplify",
                                               "variables": [], "assumptions": []})
            if result["status"] != "succeeded":
                findings.append("Unsupported or resource-limited numeric claim; not verified.")
                continue
            value = result["value"]["value"]
            if value not in {"True", "False"}:
                continue
            checked.append(claim)
            if value == "False":
                failed = claim
                findings.append("Contradictory numeric equality: " + claim)
                break
        # Checking individual equalities does not establish the problem-to-proof
        # correspondence, quantified constraints, or general boundary coverage.
        if not failed:
            findings.append("Only listed numeric claims were checked; complete solution correctness remains uncertain.")
        return {"status": "succeeded", "value": {
            "verdict": "fail" if failed else "uncertain", "findings": findings[:20],
            "counterexample": failed, "checked_claims": checked[:12],
        }}
