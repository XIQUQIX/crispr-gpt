"""Placeholder states for tasks whose structure exists but whose content does not.

The lite release ships the state-machine engine without most of the
expert-authored task content. Rather than hiding those gaps behind a single
"not supported" message, every task in the paper's task table gets a real node
in the graph. Nodes without authored content announce themselves and hand
control back, so a pipeline can be walked end to end while it stays obvious
which steps are real.

Content for these states is deliberately NOT generated: inventing protocol
details, delivery recommendations or primer sequences is exactly the failure
mode CRISPR-GPT was built to avoid.
"""

from .logic import BaseState, Result_ProcessUserInput

BANNER = """\
--------------------------------------------------------------------
CONTENT PENDING -- {title}
--------------------------------------------------------------------
This step exists in the pipeline but its domain content has not been
authored. Nothing was designed, recommended or computed here.

Task id     : {task_id}
Reference   : CRISPR-GPT (Nat Biomed Eng 2025), {paper_ref}
Still needed: {requires}

Do not treat the absence of output as a result. Continuing to the next
step.
--------------------------------------------------------------------"""


def make_pending_state(task_id, title, paper_ref, requires):
    """Build a state that reports an unimplemented task and completes.

    Returns a `BaseState` subclass so pending tasks compose with real ones in
    the task queue exactly like any other state. The class name is derived
    from `task_id` because the executor keys its memory on `__name__`, and
    every modality would otherwise contribute a `StateStep1`.
    """
    message = BANNER.format(
        title=title,
        task_id=task_id,
        paper_ref=paper_ref,
        requires="; ".join(requires),
    )

    def step(cls, user_message, **kwargs):
        return Result_ProcessUserInput(response=message), None

    return type(
        task_id.replace(".", "__"),
        (BaseState,),
        {
            "__doc__": f"Pending: {title}.",
            "request_user_input": False,
            "task_id": task_id,
            "is_pending": True,
            "step": classmethod(step),
        },
    )
