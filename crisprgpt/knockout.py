from .logic import BaseState, Result_ProcessUserInput, BaseUserInputState
from llm import OpenAIChat
from .knockout_constant import *
from .knockout_sgRNA_selection import SgRNASelection, system_already_selected
from .pending import make_pending_state
from .routing import make_readout_router
from util import get_logger

logger = get_logger(__name__)


class StateEntry(BaseState):
    request_user_input = False

    @classmethod
    def step(cls, user_message, **kwargs):
        return Result_ProcessUserInput(response=PROMPT_REQUEST_ENTRY), None


class StateStep1(BaseState):
    @classmethod
    def step(cls, user_message, **kwargs):
        return Result_ProcessUserInput(response=PROMPT_STEP1), StateStep1Inquiry


class StateStep1Inquiry(BaseUserInputState):
    prompt_process = PROMPT_PROCESS_STEP1_INQUIRY
    request_message = PROMPT_REQUEST_STEP1_INQUIRY

    @classmethod
    def step(cls, user_message, **kwargs):
        prompt = cls.prompt_process.format(user_message=user_message)
        response = OpenAIChat.chat(prompt, use_GPT4=True)
        text_response = str(response)
        result = response["Answer"]
        text_response += f" Final Result {result}"
        return (
            Result_ProcessUserInput(
                status="success",
                thoughts=response["Thoughts"],
                result=result,
                response=text_response,
            ),
            None,
        )



class StateStep1Easy(BaseUserInputState):
    prompt_process = PROMPT_PROCESS_EASY
    request_message = PROMPT_REQUEST_EASY

    @classmethod
    def step(cls, user_message, **kwargs):
        prompt = cls.prompt_process.format(user_message=user_message)
        response = OpenAIChat.chat(prompt)
        text_response = str(response)
        result = response["Answer"]
        text_response += f" Final Result {result}"
        return (
            Result_ProcessUserInput(
                status="success",
                thoughts=response["Thoughts"],
                result=result,
                response=text_response,
            ),
            StateStep3,
        )


class StateStep3(BaseState):
    @classmethod
    def step(cls, user_message, **kwargs):
        if kwargs["is_automation"] and not system_already_selected(kwargs["memory"]):
            # The planner is told to include StateStep1 first, but guard the
            # dependency here too so the task can also be run on its own.
            return (
                Result_ProcessUserInput(response=PROMPT_REQUEST_STEP3),
                StateStep1Easy,
            )
        return (
            Result_ProcessUserInput(response=PROMPT_REQUEST_STEP3),
            SgRNASelection,
        )


StateStep2 = make_pending_state(
    task_id="knockout.StateStep2",
    title="Knockout -- delivery approach selection",
    paper_ref="Table 1, 'Delivery method selection'",
    requires=[
        "expert-authored delivery options with cell-type guidance and citations",
        "web-search tool integration for context-specific recommendations",
    ],
)


StateStep4 = make_pending_state(
    task_id="knockout.StateStep4",
    title="Knockout -- experimental protocol recommendation",
    paper_ref="Table 1, 'experimental protocol recommendation'",
    requires=[
        "expert-authored protocols conditioned on the chosen Cas system and delivery route",
        "protocol retrieval over the curated document set",
    ],
)


StateStep4_5_1_Sanger = make_pending_state(
    task_id="knockout.StateStep4_5_1_Sanger",
    title="Knockout -- validation and primer design (Sanger)",
    paper_ref="Table 1, 'validation protocol recommendation and primer design'",
    requires=[
        "expert-authored validation protocol for Sanger readout",
        "Primer3 integration for primer design",
    ],
)


StateStep4_5_1_NGS = make_pending_state(
    task_id="knockout.StateStep4_5_1_NGS",
    title="Knockout -- validation and primer design (NGS)",
    paper_ref="Table 1, 'validation protocol recommendation and primer design'",
    requires=[
        "expert-authored validation protocol for NGS readout",
        "Primer3 integration for primer design",
    ],
)


StateStep4_5 = make_readout_router(
    task_id="knockout.StateStep4_5",
    heading="Step 5. Validating the editing outcome",
    sanger_state=StateStep4_5_1_Sanger,
    ngs_state=StateStep4_5_1_NGS,
)

 