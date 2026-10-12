"""Content-free routing states.

These states pick a branch from what the user says. They ask which option the
user intends to use; they never advise which option to pick, so they carry no
domain claims and need no expert review.
"""

from .logic import BaseUserInputState, Result_ProcessUserInput

READOUT_REQUEST = """
{heading}

Which readout will you use to validate editing at the target locus?

1. Sanger sequencing
2. Next-generation sequencing (NGS)
"""

READOUT_UNPARSED = (
    "Please answer with 1 (Sanger sequencing) or 2 (next-generation sequencing)."
)


def make_readout_router(task_id, heading, sanger_state, ngs_state):
    """Build a state that routes validation to the chosen sequencing readout.

    Parsed deterministically -- no model call, so this branch behaves the same
    way every time and can be exercised without an API key. As with pending
    states, the class name comes from `task_id` to keep executor memory keys
    distinct across modalities.
    """
    request_message = READOUT_REQUEST.format(heading=heading)

    def step(cls, user_message, **kwargs):
        choice = user_message.strip().lower().strip("().")
        if choice == "1" or "sanger" in choice:
            return (
                Result_ProcessUserInput(status="success", result="sanger"),
                sanger_state,
            )
        if choice == "2" or "ngs" in choice or "next-generation" in choice:
            return (
                Result_ProcessUserInput(status="success", result="ngs"),
                ngs_state,
            )
        return (
            Result_ProcessUserInput(status="error", response=READOUT_UNPARSED),
            cls,
        )

    return type(
        task_id.replace(".", "__"),
        (BaseUserInputState,),
        {
            "__doc__": f"Route validation to the chosen readout ({heading}).",
            "request_message": request_message,
            "step": classmethod(step),
        },
    )
