"""The task catalogue: one source of truth for the planner.

The prompt table handed to the LLM planner and the lookup that turns the
planner's reply back into state machines are both generated from `TASKS`, so
they cannot drift apart. Dependencies mirror the paper's task description
table (Appendix B).
"""

from dataclasses import dataclass, field
from typing import Tuple, Type

from . import act_rep, base_editing, knockout, off_target, prime_editing


class UnknownTask(ValueError):
    """The planner named a task that is not in the catalogue."""


@dataclass(frozen=True)
class TaskSpec:
    name: str
    group: str
    description: str
    state: Type
    dependencies: Tuple[str, ...] = field(default=())

    @property
    def pending(self):
        return getattr(self.state, "is_pending", False)

    @property
    def note(self):
        deps = ", ".join(self.dependencies)
        parts = []
        if deps:
            parts.append(f"needs to complete {deps} first")
        if self.pending:
            parts.append("content pending in the lite release")
        return "; ".join(parts) if parts else "none"


TASKS = (
    TaskSpec(
        "knockout.StateStep1",
        "knockout",
        "Cas System selection for knockout",
        knockout.StateStep1,
    ),
    TaskSpec(
        "knockout.StateStep2",
        "knockout",
        "Delivery approach selection for knockout",
        knockout.StateStep2,
    ),
    TaskSpec(
        "knockout.StateStep3",
        "knockout",
        "guideRNA design for knockout",
        knockout.StateStep3,
        ("knockout.StateStep1",),
    ),
    TaskSpec(
        "knockout.StateStep4",
        "knockout",
        "Experimental Protocol Selection for knockout",
        knockout.StateStep4,
        ("knockout.StateStep2",),
    ),
    TaskSpec(
        "knockout.StateStep4_5_1_Sanger",
        "knockout",
        "Primer Design for knockout, Mutation sequencing by Sanger",
        knockout.StateStep4_5_1_Sanger,
    ),
    TaskSpec(
        "knockout.StateStep4_5_1_NGS",
        "knockout",
        "Primer Design for knockout, Mutation sequencing by next-generation sequencing (NGS)",
        knockout.StateStep4_5_1_NGS,
    ),
    TaskSpec(
        "base_editing.StateStep1",
        "base editing",
        "Base Editor System selection for base editing",
        base_editing.StateStep1,
    ),
    TaskSpec(
        "base_editing.StateStep2",
        "base editing",
        "guideRNA design for base editing",
        base_editing.StateStep2,
        ("base_editing.StateStep1",),
    ),
    TaskSpec(
        "base_editing.StateStep3",
        "base editing",
        "Delivery approach selection for base editing",
        base_editing.StateStep3,
    ),
    TaskSpec(
        "base_editing.StateStep4",
        "base editing",
        "Experimental Protocol Selection for base editing",
        base_editing.StateStep4,
        ("base_editing.StateStep3",),
    ),
    TaskSpec(
        "base_editing.StateStep4_5_1_Sanger",
        "base editing",
        "Primer Design for base editing, Mutation sequencing by Sanger",
        base_editing.StateStep4_5_1_Sanger,
    ),
    TaskSpec(
        "base_editing.StateStep4_5_1_NGS",
        "base editing",
        "Primer Design for base editing, Mutation sequencing by next-generation sequencing (NGS)",
        base_editing.StateStep4_5_1_NGS,
    ),
    TaskSpec(
        "prime_editing.StateStep1",
        "prime editing",
        "Prime Editing System selection for prime editing",
        prime_editing.StateStep1,
    ),
    TaskSpec(
        "prime_editing.StateStep2",
        "prime editing",
        "Delivery approach selection for prime editing",
        prime_editing.StateStep2,
    ),
    TaskSpec(
        "prime_editing.StateStep3",
        "prime editing",
        "pegRNA design for prime editing",
        prime_editing.StateStep3,
        ("prime_editing.StateStep1",),
    ),
    TaskSpec(
        "prime_editing.StateStep4",
        "prime editing",
        "Experimental Protocol Selection for prime editing",
        prime_editing.StateStep4,
        ("prime_editing.StateStep2",),
    ),
    TaskSpec(
        "prime_editing.StateStep4_5_1_Sanger",
        "prime editing",
        "Primer Design for prime editing, Mutation sequencing by Sanger",
        prime_editing.StateStep4_5_1_Sanger,
    ),
    TaskSpec(
        "prime_editing.StateStep4_5_1_NGS",
        "prime editing",
        "Primer Design for prime editing, Mutation sequencing by next-generation sequencing (NGS)",
        prime_editing.StateStep4_5_1_NGS,
    ),
    TaskSpec(
        "act_rep.StateStep1",
        "CRISPRa/CRISPRi",
        "Activation or repression system selection for CRISPRa/CRISPRi",
        act_rep.StateStep1,
    ),
    TaskSpec(
        "act_rep.StateStep2",
        "CRISPRa/CRISPRi",
        "Delivery approach selection for CRISPRa/CRISPRi",
        act_rep.StateStep2,
    ),
    TaskSpec(
        "act_rep.StateStep3",
        "CRISPRa/CRISPRi",
        "guideRNA design for CRISPRa/CRISPRi",
        act_rep.StateStep3,
        ("act_rep.StateStep1",),
    ),
    TaskSpec(
        "act_rep.StateStep4",
        "CRISPRa/CRISPRi",
        "Experimental Protocol Selection for CRISPRa/CRISPRi",
        act_rep.StateStep4,
        ("act_rep.StateStep2",),
    ),
    TaskSpec(
        "act_rep.StateStep4_5_1",
        "CRISPRa/CRISPRi",
        "Primer Design for CRISPRa/CRISPRi, qPCR",
        act_rep.StateStep4_5_1,
    ),
    TaskSpec(
        "off_target.StateStep1",
        "off-target prediction",
        "Off-target search/prediction using CRISPRitz",
        off_target.OffTarget,
    ),
)

TASK_BY_NAME = {task.name: task for task in TASKS}
_ORDER = {task.name: index for index, task in enumerate(TASKS)}


def render_task_table():
    """Render the catalogue as the table embedded in the planner prompt."""
    lines = []
    for group in dict.fromkeys(task.group for task in TASKS):
        lines.append(f"For {group}")
        lines.append("")
        lines.append("task name: task descriptions: notes")
        for task in TASKS:
            if task.group == group:
                lines.append(f"{task.name}: {task.description} : {task.note}")
        lines.append("")
    return "\n".join(lines).rstrip()


def expand_dependencies(names):
    """Add every prerequisite the planner left out, in catalogue order.

    The planner is instructed to include dependencies, but enforcing it here
    means a forgetful reply still produces a runnable pipeline.
    """
    selected = set()
    queue = list(names)
    while queue:
        name = queue.pop()
        if name in selected:
            continue
        if name not in TASK_BY_NAME:
            raise UnknownTask(f"{name!r} is not a known task")
        selected.add(name)
        queue.extend(TASK_BY_NAME[name].dependencies)
    return sorted(selected, key=_ORDER.__getitem__)


def resolve(names):
    """Map planner-returned task names to their entry states.

    Names are looked up in the catalogue rather than evaluated, so nothing the
    model emits can reach the interpreter.
    """
    return [TASK_BY_NAME[name].state for name in expand_dependencies(names)]
