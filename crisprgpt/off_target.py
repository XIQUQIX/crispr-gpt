from util import get_logger

from llm import OpenAIChat
from .logic import Result_ProcessUserInput, BaseUserInputState
from .off_target_constant import *

logger = get_logger(__name__)


class OffTarget(BaseUserInputState):
    prompt_process = PROMPT_PROCESS_STEP1
    request_message = PROMPT_REQUEST_STEP1

    @classmethod
    def step(cls, user_message, **kwargs):
        prompt = cls.prompt_process.format(user_message=user_message)
        response = OpenAIChat.chat(prompt, use_GPT4=True)

        choice = str(response["Choice"]).strip().strip("().")
        if choice == "1":
            result = "mismatch_only"
            text_response = RESPONSE_MISMATCH_ONLY
        elif choice == "2":
            result = "mismatch_bulges"
            text_response = RESPONSE_MISMATCH_BULGES
        else:
            # Anything else would previously fall through to an unbound
            # variable; re-ask instead.
            return (
                Result_ProcessUserInput(
                    status="error",
                    response="Sorry, I could not tell which search you want. "
                    "Please answer with 1 (mismatches only) or 2 (mismatches + bulges).",
                ),
                cls,
            )
        return (
            Result_ProcessUserInput(
                status="success",
                thoughts=response["Thoughts"],
                result=result,
                response=text_response,
            ),
            None,
        )
