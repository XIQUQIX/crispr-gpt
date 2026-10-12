"""Offline checks for the state machine, the planner and the library layer.

Run from the project root:

    python tests/run_checks.py

No API key and no network access are needed; the LLM is stubbed.
"""

import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from tests.stub_llm import install
from crisprgpt import entry, tasks
from crisprgpt.apis import parse_sgRNA_library as lib
from crisprgpt.logic import (
    GradioMachineStateClass,
    concurrent_gradio_state_machine as machine,
)

RESULTS = []


def check(name):
    def decorator(fn):
        RESULTS.append((name, fn))
        return fn

    return decorator


# --------------------------------------------------------------------------
# Planner catalogue
# --------------------------------------------------------------------------


@check("planner: dependencies are filled in and ordered")
def _():
    expanded = tasks.expand_dependencies(["knockout.StateStep3"])
    assert expanded == ["knockout.StateStep1", "knockout.StateStep3"], expanded

    expanded = tasks.expand_dependencies(
        ["knockout.StateStep4", "knockout.StateStep3"]
    )
    assert expanded == [
        "knockout.StateStep1",
        "knockout.StateStep2",
        "knockout.StateStep3",
        "knockout.StateStep4",
    ], expanded


@check("planner: unknown task names are rejected, not evaluated")
def _():
    for hostile in [
        "__import__('os').system('echo pwned')",
        "knockout.StateStep1; print(1)",
        "open('/etc/passwd')",
        "nonexistent.Task",
    ]:
        try:
            tasks.resolve([hostile])
        except tasks.UnknownTask:
            continue
        raise AssertionError(f"{hostile!r} was not rejected")


@check("planner: every catalogue entry resolves to a usable state")
def _():
    for spec in tasks.TASKS:
        state = spec.state
        assert hasattr(state, "safe_step"), spec.name
        assert hasattr(state, "get_request_message"), spec.name
    table = tasks.render_task_table()
    for spec in tasks.TASKS:
        assert spec.name in table, spec.name
    assert "needs to complete knockout.StateStep1 first" in table


# --------------------------------------------------------------------------
# Library layer
# --------------------------------------------------------------------------


@check("library: unsupported Cas system raises instead of KeyError")
def _():
    try:
        lib.sgRNA_library_reader.parse_knockout_library("SpRYCas9", "human")
    except lib.LibraryNotAvailable as ex:
        assert "SpRYCas9" in str(ex)
    else:
        raise AssertionError("SpRYCas9 should not resolve to a library")


@check("library: missing files yield an empty frame, not a list")
def _():
    reader = lib.sgRNALibraryReader()
    reader.ROOT = "does-not-exist"
    reader._process_txt("KO_SP_human.txt")
    assert isinstance(reader.library["KO_SP_human.txt"], pd.DataFrame)


@check("library: subset_between chains from the running result")
def _():
    df = pd.DataFrame(
        {"gene": ["A", "A", "B", "B"], "rank": [1, 9, 1, 9]}
    )
    rules = [
        (
            "draft a seri of actions",
            {
                "Species": "human",
                "Actions": [
                    {
                        "called_function": "subset_value",
                        "column_name": "gene",
                        "matching_value": "A",
                    },
                    {
                        "called_function": "subset_between",
                        "column_name": "rank",
                        "x": "0",
                        "y": "5",
                    },
                ],
            },
        )
    ]
    with install(rules):
        result, _link = lib.extract_info("x", "draft a seri of actions {user_message}", df)
    # Before the fix the second action restarted from the unfiltered frame and
    # gene B leaked back in.
    assert list(result["gene"]) == ["A"], result.to_dict("list")


@check("library: 'NA' bounds are treated as absent")
def _():
    df = pd.DataFrame({"gene": ["A", "B"], "rank": [1, 9]})
    rules = [
        (
            "draft a seri of actions",
            {
                "Species": "human",
                "Actions": [
                    {
                        "called_function": "subset_between",
                        "column_name": "rank",
                        "x": "NA",
                        "y": "5",
                    }
                ],
            },
        )
    ]
    with install(rules):
        result, _link = lib.extract_info("x", "draft a seri of actions {user_message}", df)
    assert list(result["gene"]) == ["A"], result.to_dict("list")


# --------------------------------------------------------------------------
# Full pipeline walk
# --------------------------------------------------------------------------

KNOCKOUT_RULES = [
    ("1. Meta-Mode", {"Thoughts": "meta", "Choice": "1"}),
    ("general gene editing scenarios", {"Thoughts": "knockout", "Choice": "1"}),
    (
        "identify the single most relevant Cas system",
        {"Thoughts": "SpCas9 is the default", "Answer": "SpCas9"},
    ),
    (
        "extract the target gene and species",
        {
            "Target gene": "TSPAN6",
            "Species": "human",
            "Specified": "no",
            "target exon": "Exon 2",
            "rationale": "stub rationale",
            "reformatted_request": "2 sgRNAs targeting TSPAN6 exon 2",
        },
    ),
    (
        "Would you like to continue sgRNA design",
        {"Thoughts": "yes", "Choice": "YES"},
    ),
    (
        "draft a seri of actions",
        {
            "Species": "human",
            "Actions": [
                {
                    "called_function": "subset_value",
                    "column_name": "Target Gene Symbol",
                    "matching_value": "TSPAN6",
                },
                {"called_function": "get", "n": "4"},
            ],
        },
    ),
    ("Would you like to use CRISPRitz", {"Thoughts": "no", "Choice": "no"}),
]


def new_session():
    session = GradioMachineStateClass(full_task_list=[entry.EntryState])
    machine.reset(session)
    machine.loop(None, session)
    return session


@check("meta mode: knockout pipeline walks all six steps")
def _():
    with install(KNOCKOUT_RULES):
        session = new_session()
        transcript = []

        transcript += machine.loop("1", session)  # meta mode
        transcript += machine.loop("1", session)  # knockout
        transcript += machine.loop("SpCas9", session)  # Cas system

        # The guide request mentions "human", which must trigger the
        # heritable-editing notice before anything else happens.
        out = machine.loop("2 sgRNAs targeting human TSPAN6", session)
        transcript += out
        assert any("heritable editing" in str(m) for m in out), out

        transcript += machine.loop("yes", session)  # acknowledge
        transcript += machine.loop("yes", session)  # use suggested exon
        transcript += machine.loop("no", session)  # skip off-target
        transcript += machine.loop("2", session)  # NGS readout

        text = "\n".join(str(m) for m in transcript)

    for expected in [
        "Selecting a CRISPR/Cas system",
        "knockout.StateStep2",  # delivery, pending
        "Designing guideRNA for gene knockout",
        "TSPAN6",  # a real row from the bundled library
        "knockout.StateStep4",  # protocol, pending
        "knockout.StateStep4_5_1_NGS",  # validation, pending
    ]:
        assert expected in text, f"missing {expected!r} in transcript"

    assert session.current_state.isFinal, session.current_state


@check("meta mode: pending steps never fabricate content")
def _():
    with install(KNOCKOUT_RULES):
        session = new_session()
        machine.loop("1", session)  # meta mode
        machine.loop("1", session)  # knockout
        # Answering the Cas-system question completes step 1 and runs step 2,
        # which is the first pending node in the pipeline.
        out = machine.loop("SpCas9", session)
    text = "\n".join(str(m) for m in out)
    assert "CONTENT PENDING" in text, text
    assert "Nothing was designed, recommended or computed here." in text


@check("ack state: a non-yes answer gets an explanation")
def _():
    with install(KNOCKOUT_RULES):
        session = new_session()
        machine.loop("1", session)
        machine.loop("1", session)
        machine.loop("SpCas9", session)
        machine.loop("2 sgRNAs targeting human TSPAN6", session)
        out = machine.loop("maybe later", session)
    assert out, "a rejected acknowledgement produced no output at all"
    assert any("Not confirmed" in str(m) for m in out), out


@check("readout router: parses both branches and re-asks otherwise")
def _():
    from crisprgpt import knockout

    router = knockout.StateStep4_5
    _res, nxt = router.step("1", memory={})
    assert nxt is knockout.StateStep4_5_1_Sanger
    _res, nxt = router.step("NGS please", memory={})
    assert nxt is knockout.StateStep4_5_1_NGS
    res, nxt = router.step("banana", memory={})
    assert nxt is router and res.status == "error"


PLANNER_RULES = [
    (
        "generate a list of tasks for execution",
        {"Thoughts": "guide design only", "Tasks": ["knockout.StateStep3"]},
    )
]


def plan(request, outer_memory):
    from crisprgpt.automation import StateAutomate

    with install(PLANNER_RULES):
        StateAutomate.step(
            request, memory=outer_memory, email="", files=[], is_automation=False
        )
    return outer_memory["executor"]


@check("auto mode: the planner's missing dependency is filled in")
def _():
    executor = plan("design sgRNA to knock out TSPAN6", {})
    names = [state.__name__ for state in executor.full_task_list]
    # StateStep3 depends on StateStep1; the planner named only StateStep3.
    assert names == [
        "EmptyState",
        "StateStep1",
        "StateStep3",
        "EmptyStateFinal",
    ], names


@check("auto mode: the heritable-editing notice is not pre-acknowledged")
def _():
    executor = plan("design sgRNA to knock out TSPAN6", {})
    assert executor.memory["flag_human_heritable_editing_ack"] is False

    # Once the session has shown the notice, auto mode should not re-ask.
    executor = plan(
        "design sgRNA to knock out TSPAN6",
        {"flag_human_heritable_editing_ack": True},
    )
    assert executor.memory["flag_human_heritable_editing_ack"] is True


@check("catalogue: state names are unique so memory keys cannot collide")
def _():
    names = [spec.state.__name__ for spec in tasks.TASKS]
    duplicates = {n for n in names if names.count(n) > 1}
    assert not duplicates, duplicates


@check("privacy filter: long sequences never reach the model")
def _():
    import llm

    try:
        llm.OpenAIChat.chat("design primers for ACGTACGTACGTACGTACGTACGT")
    except llm.IdentifiableGeneError:
        pass
    else:
        raise AssertionError("20+ bp sequence was not blocked")


def main():
    failures = 0
    for name, fn in RESULTS:
        try:
            fn()
        except Exception:
            failures += 1
            print(f"FAIL  {name}")
            traceback.print_exc()
        else:
            print(f"ok    {name}")
    print(f"\n{len(RESULTS) - failures}/{len(RESULTS)} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
