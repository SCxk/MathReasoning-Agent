from dataclasses import dataclass, replace

from pydantic import Field

from reasoning_agent.custom2.text_models import ControlMessage


class PlannedTask(ControlMessage):
    objective: str = Field(min_length=1, max_length=2000)
    acceptance_criteria: list[str] = Field(min_length=1, max_length=6)
    depends_on: list[int] = Field(default_factory=list, max_length=6)
    uses: list[str] = Field(default_factory=list, max_length=12)


class TextTaskPlan(ControlMessage):
    strategy: str = Field(default="", max_length=3000)
    tasks: list[PlannedTask] = Field(min_length=2, max_length=6)


class TextTaskReplan(ControlMessage):
    route: str = Field(min_length=1, max_length=2000)
    invalidate_task_ids: list[str] = Field(default_factory=list, max_length=24)
    prerequisites: list[PlannedTask] = Field(default_factory=list, max_length=4)


@dataclass
class TextTask:
    id: str
    objective: str
    acceptance_criteria: tuple[str, ...]
    dependencies: tuple[str, ...] = ()
    status: str = "pending"
    accepted_solution_id: str | None = None
    accepted_dependencies: tuple[tuple[str, str], ...] = ()
    latest_solution_id: str | None = None
    repair_count: int = 0
    route: str = ""
    replaces: str | None = None


class TextTaskLedger:
    def __init__(self, max_tasks: int = 24):
        self.tasks: dict[str, TextTask] = {}
        self.max_tasks = max_tasks
        self.strategy = ""

    def _new_tasks(self, specs, existing, base_dependencies=()):
        created = []
        for position, spec in enumerate(specs, 1):
            if not spec.objective.strip() or any(not criterion.strip() for criterion in spec.acceptance_criteria):
                raise ValueError("empty_task_requirement")
            if len(spec.depends_on) != len(set(spec.depends_on)) or any(
                dependency < 1 or dependency >= position for dependency in spec.depends_on
            ):
                raise ValueError("invalid_dependency_order")
            if any(reference not in existing or not self.is_current(reference) for reference in spec.uses):
                raise ValueError("unknown_or_unaccepted_dependency")
            dependencies = (*base_dependencies, *spec.uses, *(created[index - 1].id for index in spec.depends_on))
            created.append(TextTask(
                id=f"T{len(existing) + position}", objective=spec.objective.strip(),
                acceptance_criteria=tuple(criterion.strip() for criterion in spec.acceptance_criteria),
                dependencies=tuple(dict.fromkeys(dependencies)),
            ))
        if len(existing) + len(created) > self.max_tasks:
            raise ValueError("task_limit")
        return created

    def initialize(self, plan: TextTaskPlan) -> None:
        if self.tasks:
            raise ValueError("plan_already_initialized")
        tasks = self._new_tasks(plan.tasks, {})
        self.tasks = {task.id: task for task in tasks}
        self.strategy = plan.strategy

    def dependency_ids(self, task_id: str) -> tuple[str, ...]:
        visited = set()
        ordered = []

        def visit(reference):
            for dependency in self.tasks[reference].dependencies:
                if dependency not in visited:
                    visited.add(dependency)
                    visit(dependency)
                    ordered.append(dependency)

        visit(task_id)
        return tuple(ordered)

    def ordered_task_ids(self) -> tuple[str, ...]:
        ordered = []
        seen = set()
        for task in self.tasks.values():
            if task.status == "superseded":
                continue
            for reference in (*self.dependency_ids(task.id), task.id):
                if reference not in seen:
                    seen.add(reference)
                    ordered.append(reference)
        return tuple(ordered)

    def is_current(self, task_id: str) -> bool:
        task = self.tasks[task_id]
        return (
            task.status == "accepted" and task.accepted_solution_id is not None
            and all(self.is_current(reference) for reference in task.dependencies)
            and task.accepted_dependencies == self.dependency_versions(task_id)
        )

    def dependency_versions(self, task_id: str) -> tuple[tuple[str, str], ...]:
        return tuple(
            (reference, self.tasks[reference].accepted_solution_id or "")
            for reference in self.dependency_ids(task_id)
        )

    def ready_task(self) -> TextTask | None:
        return next((
            task for task in self.tasks.values()
            if task.status == "pending" and all(self.is_current(reference) for reference in task.dependencies)
        ), None)

    def accept(self, task_id: str, solution_id: str, versions: tuple[tuple[str, str], ...]) -> None:
        task = self.tasks[task_id]
        if task.status != "pending" or any(not self.is_current(reference) for reference in task.dependencies):
            raise ValueError("unaccepted_dependencies")
        if self.dependency_versions(task_id) != versions:
            raise ValueError("stale_dependency_version")
        task.accepted_solution_id = solution_id
        task.accepted_dependencies = versions
        task.status = "accepted"

    def affected(self, task_ids) -> set[str]:
        affected = set(task_ids)
        while True:
            expanded = affected | {
                task.id for task in self.tasks.values()
                if task.status != "superseded" and any(reference in affected for reference in task.dependencies)
            }
            if expanded == affected:
                return affected
            affected = expanded

    def invalidate(self, task_ids) -> list[str]:
        affected = self.affected(task_ids)
        changed = []
        for task in self.tasks.values():
            if task.id in affected and task.status != "superseded":
                task.status = "pending"
                task.accepted_solution_id = None
                task.accepted_dependencies = ()
                task.latest_solution_id = None
                task.repair_count = 0
                changed.append(task.id)
        return changed

    def invalidate_stale(self) -> list[str]:
        stale = [task.id for task in self.tasks.values() if task.status == "accepted" and not self.is_current(task.id)]
        return self.invalidate(stale) if stale else []

    def complete(self) -> bool:
        active = [task for task in self.tasks.values() if task.status != "superseded"]
        return bool(active) and all(self.is_current(task.id) for task in active)

    def revised(self, task_id: str, plan: TextTaskReplan, *, final_review: bool = False):
        if task_id not in self.tasks or self.tasks[task_id].status == "superseded":
            raise ValueError("unknown_replan_target")
        allowed = set(self.dependency_ids(task_id)) | {task_id}
        if final_review:
            allowed = {task.id for task in self.tasks.values() if task.status != "superseded"}
        if any(reference not in allowed for reference in plan.invalidate_task_ids):
            raise ValueError("invalid_invalidation_target")
        updated = TextTaskLedger(self.max_tasks)
        updated.tasks = {reference: replace(task) for reference, task in self.tasks.items()}
        updated.strategy = self.strategy
        invalidated = updated.invalidate([task_id, *plan.invalidate_task_ids])
        original = updated.tasks[task_id]
        additions = updated._new_tasks(plan.prerequisites, updated.tasks, original.dependencies)
        if len(updated.tasks) + len(additions) + 1 > self.max_tasks:
            raise ValueError("task_limit")
        replacement = TextTask(
            id=f"T{len(updated.tasks) + len(additions) + 1}", objective=original.objective,
            acceptance_criteria=original.acceptance_criteria,
            dependencies=tuple(dict.fromkeys((*original.dependencies, *(task.id for task in additions)))),
            route=plan.route, replaces=original.id,
        )
        for task in updated.tasks.values():
            if task.status != "superseded" and task.id != original.id:
                task.dependencies = tuple(replacement.id if reference == original.id else reference for reference in task.dependencies)
        original.status = "superseded"
        updated.tasks.update({task.id: task for task in [*additions, replacement]})
        updated._validate_graph()
        return updated, invalidated, replacement.id

    def _validate_graph(self):
        active = set()
        finished = set()

        def visit(reference):
            if reference in active:
                raise ValueError("dependency_cycle")
            if reference in finished:
                return
            task = self.tasks.get(reference)
            if task is None or task.status == "superseded":
                raise ValueError("invalid_dependency")
            active.add(reference)
            for dependency in task.dependencies:
                visit(dependency)
            active.remove(reference)
            finished.add(reference)

        for task in self.tasks.values():
            if task.status != "superseded":
                visit(task.id)
