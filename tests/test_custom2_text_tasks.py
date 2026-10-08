import unittest

from reasoning_agent.custom2.text_tasks import TextTaskLedger, TextTaskPlan, TextTaskReplan


def plan_for(dependencies):
    return TextTaskPlan.model_validate({
        "tasks": [{"objective": f"目标 {index}", "acceptance_criteria": [f"验收 {index}"], "depends_on": values}
                  for index, values in enumerate(dependencies, 1)],
    })


class TextTaskLedgerTests(unittest.TestCase):
    def ledger(self, dependencies=None):
        ledger = TextTaskLedger()
        ledger.initialize(plan_for(dependencies or [[], [1]]))
        return ledger

    def accept_all(self, ledger):
        while task := ledger.ready_task():
            ledger.accept(task.id, "S" + task.id[1:], ledger.dependency_versions(task.id))

    def test_only_verified_dependencies_unlock_next_task(self):
        ledger = self.ledger()
        self.assertEqual(ledger.ready_task().id, "T1")
        with self.assertRaises(ValueError):
            ledger.accept("T2", "S2", ())
        ledger.accept("T1", "S1", ())
        self.assertEqual(ledger.ready_task().id, "T2")
        self.assertFalse(ledger.complete())
        ledger.accept("T2", "S2", (("T1", "S1"),))
        self.assertTrue(ledger.complete())

    def test_initial_dependency_order_is_validated(self):
        for dependencies in [[[], [2]], [[2], []], [[], [0]], [[], [1, 1]]]:
            with self.subTest(dependencies=dependencies), self.assertRaises(ValueError):
                self.ledger(dependencies)

    def test_invalidation_cascades_but_preserves_independent_work(self):
        ledger = self.ledger([[], [1], [2], []])
        self.accept_all(ledger)
        self.assertEqual(ledger.invalidate(["T1"]), ["T1", "T2", "T3"])
        self.assertTrue(ledger.is_current("T4"))
        self.assertIsNone(ledger.tasks["T2"].accepted_solution_id)
        self.assertEqual(ledger.ready_task().id, "T1")

    def test_version_mismatch_revokes_descendants(self):
        ledger = self.ledger([[], [1], [2]])
        self.accept_all(ledger)
        ledger.tasks["T1"].accepted_solution_id = "S99"
        self.assertFalse(ledger.is_current("T2"))
        self.assertEqual(ledger.invalidate_stale(), ["T2", "T3"])
        with self.assertRaises(ValueError):
            ledger.accept("T2", "S4", (("T1", "S1"),))

    def test_replacement_keeps_original_goal_and_rewires_downstream(self):
        ledger = self.ledger([[], [1], [2]])
        self.accept_all(ledger)
        updated, invalidated, replacement = ledger.revised("T2", TextTaskReplan(route="使用替代论证"))
        self.assertEqual(invalidated, ["T2", "T3"])
        self.assertEqual(updated.tasks["T2"].status, "superseded")
        self.assertEqual(updated.tasks[replacement].objective, ledger.tasks["T2"].objective)
        self.assertEqual(updated.tasks[replacement].acceptance_criteria, ledger.tasks["T2"].acceptance_criteria)
        self.assertEqual(updated.tasks["T3"].dependencies, (replacement,))
        self.assertTrue(updated.is_current("T1"))
        self.assertTrue(ledger.complete())

    def test_new_prerequisite_must_pass_before_replacement(self):
        ledger = self.ledger()
        ledger.accept("T1", "S1", ())
        plan = TextTaskReplan.model_validate({
            "route": "补充边界分析", "prerequisites": [
                {"objective": "核对临界情况", "acceptance_criteria": ["列出全部临界情况"]},
            ],
        })
        updated, _, replacement = ledger.revised("T2", plan)
        self.assertEqual(updated.ready_task().id, "T3")
        updated.accept("T3", "S3", updated.dependency_versions("T3"))
        self.assertEqual(updated.ready_task().id, replacement)

    def test_replan_can_revoke_ancestor_and_all_dependent_results(self):
        ledger = self.ledger([[], [1], [2], []])
        self.accept_all(ledger)
        updated, invalidated, _ = ledger.revised("T3", TextTaskReplan(route="重查范围", invalidate_task_ids=["T1"]))
        self.assertEqual(invalidated, ["T1", "T2", "T3"])
        self.assertTrue(updated.is_current("T4"))
        self.assertEqual(updated.ready_task().id, "T1")

    def test_replan_rejects_unknown_or_invalidated_dependencies_atomically(self):
        ledger = self.ledger()
        self.accept_all(ledger)
        plans = [
            {"route": "重查", "invalidate_task_ids": ["T99"]},
            {"route": "重查", "invalidate_task_ids": ["T1"], "prerequisites": [
                {"objective": "新任务", "acceptance_criteria": ["可验证"], "uses": ["T1"]},
            ]},
            {"route": "重查", "prerequisites": [
                {"objective": "新任务", "acceptance_criteria": ["可验证"], "uses": ["T2"]},
            ]},
        ]
        for plan in plans:
            with self.subTest(plan=plan), self.assertRaises(ValueError):
                ledger.revised("T2", TextTaskReplan.model_validate(plan))
            self.assertTrue(ledger.complete())
            self.assertEqual(len(ledger.tasks), 2)

    def test_final_review_can_revisit_an_independent_branch(self):
        ledger = self.ledger([[], []])
        self.accept_all(ledger)
        plan = TextTaskReplan(route="第一分支缺少边界", invalidate_task_ids=["T1"])
        with self.assertRaises(ValueError):
            ledger.revised("T2", plan)
        updated, _, _ = ledger.revised("T2", plan, final_review=True)
        self.assertFalse(updated.is_current("T1"))

    def test_task_growth_is_bounded(self):
        ledger = TextTaskLedger(max_tasks=2)
        ledger.initialize(plan_for([[], [1]]))
        with self.assertRaises(ValueError):
            ledger.revised("T1", TextTaskReplan(route="新方法"))
        self.assertEqual(len(ledger.tasks), 2)

    def test_replaced_ancestor_is_ordered_before_its_existing_child(self):
        ledger = self.ledger()
        updated, _, replacement = ledger.revised("T1", TextTaskReplan(route="重新确认条件"))
        self.assertEqual(updated.ordered_task_ids(), (replacement, "T2"))
        self.assertEqual(updated.dependency_ids("T2"), (replacement,))


if __name__ == "__main__":
    unittest.main()
