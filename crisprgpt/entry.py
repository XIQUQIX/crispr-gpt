from .logic import BaseState, Result_ProcessUserInput, BaseUserInputState, StateFinal
from llm import OpenAIChat
from . import base_editing, knockout, prime_editing, act_rep
from .automation import StateAutomate

ENTRY_MENU = """Welcome to CRISPR-GPT. I can help with the following tasks. Please select
one to continue.

1. Meta-Mode (Step-by-Step Guidance on Pre-defined Meta-Task)
2. Auto-Mode (Customized Guidance on Free-style User Request)

Note: Q&A Mode ("Q: ..." questions) is not available in the lite version -- it
depends on the curated knowledge base, which this release does not include.
"""

PROMPT_REQUEST_ENTRY = ENTRY_MENU

# The menu is interpolated rather than restated so the two copies cannot drift.
PROMPT_PROCESS_ENTRY = (
    """
Please act as an expert in CRISPR technology. Given the user instruction and user input, think step by step and generate a choice for the user. Please format your response and make sure it is parsable by JSON.

User Instructions:

\""""
    + ENTRY_MENU
    + """"

User Input:

"{user_message}"

Response format:

{{
"Thoughts": "<thoughts>",
"Choice": "<choice>"  ## output number only
}}"""
)


class EntryState(BaseState):
    request_user_input = False

    @classmethod
    def step(cls, user_message, **kwargs):
        return Result_ProcessUserInput(response=PROMPT_REQUEST_ENTRY), EntryStateChoice


class EntryStateChoice(BaseUserInputState):
    prompt_process = PROMPT_PROCESS_ENTRY

    @classmethod
    def NextState(cls, choice):
        if choice.lower() in ["1", "i", "(1)", "(i)"]:
            return MetaStateEntry
        elif choice.lower() in ["2", "ii", "(2)", "(ii)"]:
            return StateAutomate
        else:
            return cls

    @classmethod
    def step(cls, user_message, **kwargs):
        prompt = cls.prompt_process.format(user_message=user_message)
        response = OpenAIChat.chat(prompt)
        return Result_ProcessUserInput(
            status="success",
            thoughts=response["Thoughts"],
            result=response["Choice"],
            response=str(response),
        ), cls.NextState(response["Choice"])


META_MENU = """Please select the general gene editing scenarios to continue.
1. Generating a Knockout Using CRISPR.
2. CRISPR Base Editing Without Double-Strand Breaks. (content pending in Lite version)
3. Generating Small Insertion/deletion/base editing through Prime Editing. (content pending in Lite version)
4. Activation or Repression of Target Genes Using CRISPR. (content pending in Lite version)
"""

PROMPT_REQUEST_META = META_MENU

PROMPT_PROCESS_META = (
    """
Please act as an expert in CRISPR technology. Given the user instruction and user input, think step by step and generate a choice for the user. Please format your response and make sure it is parsable by JSON.

User Instructions:

\""""
    + META_MENU
    + """"

User Input:

"{user_message}"

Response format:

{{
"Thoughts": "<thoughts>",
"Choice": "<choice>"  ## output number only
}}"""
)


# Each meta-task runs the full pipeline for one modality, in the order the
# paper's Table 1 presents it: system selection, delivery, guide design,
# protocol, validation. Note base editing numbers delivery as StateStep3 and
# guide design as StateStep2 (Appendix B), so its list is not numerically
# sorted.
META_PIPELINES = {
    "1": [
        knockout.StateEntry,
        knockout.StateStep1,
        knockout.StateStep2,
        knockout.StateStep3,
        knockout.StateStep4,
        knockout.StateStep4_5,
    ],
    "2": [
        base_editing.StateStep1,
        base_editing.StateStep3,
        base_editing.StateStep2,
        base_editing.StateStep4,
        base_editing.StateStep4_5,
    ],
    "3": [
        prime_editing.StateStep1,
        prime_editing.StateStep2,
        prime_editing.StateStep3,
        prime_editing.StateStep4,
        prime_editing.StateStep4_5,
    ],
    "4": [
        act_rep.StateStep1,
        act_rep.StateStep2,
        act_rep.StateStep3,
        act_rep.StateStep4,
        act_rep.StateStep4_5_1,
    ],
}
META_PIPELINES.update(
    {"i": META_PIPELINES["1"], "ii": META_PIPELINES["2"],
     "iii": META_PIPELINES["3"], "iv": META_PIPELINES["4"]}
)


class MetaStateEntry(BaseState):
    request_user_input = False

    @classmethod
    def step(cls, user_message, **kwargs):
        return Result_ProcessUserInput(response=PROMPT_REQUEST_META), MetaStateChoice


class MetaStateChoice(BaseUserInputState):
    prompt_process = PROMPT_PROCESS_META

    @classmethod
    def NextState(cls, choice):
        pipeline = META_PIPELINES.get(choice.strip().strip("().").lower())
        if pipeline is None:
            return cls
        return [*pipeline, StateFinal]

    @classmethod
    def step(cls, user_message, **kwargs):
        prompt = cls.prompt_process.format(user_message=user_message)
        response = OpenAIChat.chat(prompt)
        return Result_ProcessUserInput(
            status="success",
            thoughts=response["Thoughts"],
            result=response["Choice"],
            response=str(response),
        ), cls.NextState(response["Choice"])
