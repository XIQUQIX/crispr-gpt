from .knockout_sgRNA_selection_constant import *
from .logic import BaseState, Result_ProcessUserInput, BaseUserInputState
from llm import OpenAIChat
from .off_target import OffTarget
from .apis.parse_sgRNA_library import (
    extract_info,
    sgRNA_library_reader,
    LibraryNotAvailable,
)


# Meta mode records the chosen Cas system in StateStep1Inquiry; auto mode uses
# the condensed StateStep1Easy. Either is a valid source.
SELECTION_STATES = ("StateStep1Inquiry", "StateStep1Easy")


def system_already_selected(memory):
    return any(name in memory for name in SELECTION_STATES)


def get_selected_system(memory):
    for name in SELECTION_STATES:
        if name in memory:
            return memory[name].result
    raise KeyError(
        "No Cas system has been selected yet; "
        f"expected one of {SELECTION_STATES} in memory."
    )


class SgRNASelection(BaseUserInputState):
    prompt_process = PROMPT_PROCESS_AGENT1
    request_message = PROMPT_REQUEST_AGENT1

    @classmethod
    def step(cls, user_message, **kwargs):
        prompt = cls.prompt_process.format(user_message=user_message)
        response = OpenAIChat.chat(prompt, use_GPT4=True)
        response["original_request"] = user_message
        if response["Specified"].lower() == "yes":
            return (
                Result_ProcessUserInput(
                    status="success",
                    result=response,
                ),
                StateStepOriginal,
            )
        else:
            text_response = "Sugessted exon/exons: " + str(
                {
                    "Exon/exons": response["target exon"],
                    "Reason": {response["rationale"]},
                }
            )
            return (
                Result_ProcessUserInput(
                    status="success",
                    result=response,
                    response=text_response,
                ),
                StateStepQuestion,
            )


class StateStepQuestion(BaseUserInputState):
    prompt_process = PROMPT_PROCESS_QUESTION
    request_message = PROMPT_REQUEST_QUESTION
    prev_state_name = "SgRNASelection"

    @classmethod
    def step(cls, user_message, **kwargs):
        prev_result = kwargs["memory"][cls.prev_state_name].result
        target_exon = prev_result["target exon"]
        rationale = prev_result["rationale"]
        prompt = cls.prompt_process.format(
            user_message=user_message, target_exon=target_exon, rationale=rationale
        )
        response = OpenAIChat.chat(prompt, use_GPT4=True)
        choice = response["Choice"]
        if choice.lower() == "yes":
            return (
                Result_ProcessUserInput(
                    status="success", thoughts=response["Thoughts"], result=choice
                ),
                StateStepReformatted,
            )
        else:
            return (
                Result_ProcessUserInput(
                    status="success", thoughts=response["Thoughts"], result=choice
                ),
                StateStepOriginal,
            )


DISPLAY_COLUMNS = [
    "Target Gene Symbol",
    "CRISPR Mechanism",
    "sgRNA Sequence",
    "PAM Sequence",
    "Exon Number",
    "sgRNA Cut Position (1-based)",
    "On-Target Efficacy Score",
    "Off-Target Rank",
    "Combined Rank",
]


class _SgRNALookupState(BaseState):
    """Query the pre-designed library and present the matching guides.

    Subclasses only choose which phrasing of the request to query with.
    """

    prompt_process = PROMPT_PROCESS_AGENT2
    prev_state_name = "SgRNASelection"
    request_key = None

    @classmethod
    def step(cls, user_message, **kwargs):
        response = kwargs["memory"][cls.prev_state_name].result
        system = get_selected_system(kwargs["memory"])
        species = response["Species"]

        try:
            df = sgRNA_library_reader.parse_knockout_library(system, species)
        except LibraryNotAvailable as ex:
            return (
                Result_ProcessUserInput(response=f"{ex}\n{RESPONSE_STEP_ERROR}"),
                OffTargetQuestion,
            )

        result_df, download_link = extract_info(
            response[cls.request_key], cls.prompt_process, df
        )
        if result_df.empty:
            return Result_ProcessUserInput(response=RESPONSE_STEP_ERROR), OffTargetQuestion

        table = result_df[DISPLAY_COLUMNS].to_markdown(index=False)
        body = f"{download_link}\n\n{table}" if download_link else table
        return (
            Result_ProcessUserInput(status="success", result=result_df, response=body),
            OffTargetQuestion,
        )


class StateStepReformatted(_SgRNALookupState):
    """Query using the request rewritten with the suggested target exons."""

    request_key = "reformatted_request"


class StateStepOriginal(_SgRNALookupState):
    """Query using the user's request exactly as they phrased it."""

    request_key = "original_request"


class OffTargetQuestion(BaseUserInputState):
    prompt_process = PROMPT_PROCESS_OFFTARGET_QUESTION
    request_message = PROMPT_REQUEST_OFFTARGET_QUESTION

    @classmethod
    def NextState(cls):
        return OffTarget

    @classmethod
    def step(cls, user_message, **kwargs):
        prompt = cls.prompt_process.format(user_message=user_message)
        response = OpenAIChat.chat(prompt, use_GPT4=True)

        result = response["Choice"]
        if result.lower() == "yes":
            return (
                Result_ProcessUserInput(
                    status="success", thoughts=response["Thoughts"], result=result
                ),
                cls.NextState(),
            )
        else:
            return (
                Result_ProcessUserInput(
                    status="success", thoughts=response["Thoughts"], result=result
                ),
                None,
            )
