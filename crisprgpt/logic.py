from dataclasses import dataclass, field
from typing import Optional, List, Any, Dict
from llm import OpenAIChat
from .safety import (
    check_human_heritable_editing,
    WARNING_HUMAN_HERITABLE_EDITING,
    check_stopping_keywords,
)
from util import get_logger

logger = get_logger(__name__)


@dataclass
class Result_ProcessUserInput:
    status: str = "success"
    result: Optional[str] = None
    thoughts: Optional[str] = None
    response: Optional[str] = None


class BaseState:
    isFinal = False
    request_user_input = False
    request_message = ""

    @classmethod
    def FallbackState(cls):
        return None

    @classmethod
    def get_request_message(cls):
        return cls.request_message

    @classmethod
    def step(cls, user_message, **kwargs):
        if not cls.isFinal:
            raise NotImplementedError
        return Result_ProcessUserInput(), cls

    @classmethod
    def safe_step(cls, user_message, **kwargs):
        try:
            if user_message is not None:
                logger.debug("DEBUG: there might be some error in the code.")
            return cls.step(user_message, **kwargs)
        except Exception as ex:
            logger.info(["Error occured", ex])
            return (
                Result_ProcessUserInput(
                    status="error",
                    response="Error occured. Error Message: "
                    + str(ex)
                    + " Let's try again.",
                ),
                cls.FallbackState(),
            )


class BaseUserInputState:
    isFinal = False
    request_user_input = True
    prompt_process = "{user_messsage}"
    request_message = ""

    @classmethod
    def NextState(cls):
        return cls

    @classmethod
    def get_request_message(cls):
        return cls.request_message

    @classmethod
    def step(cls, user_message, **kwargs):
        prompt = cls.prompt_process.format(user_message=user_message)
        response = OpenAIChat.chat(prompt)
        return (
            Result_ProcessUserInput(
                status="success",
                thoughts=response["Thoughts"],
                result=response["Choice"],
                response=str(response),
            ),
            cls.NextState(),
        )

    @classmethod
    def safe_step(cls, user_message, **kwargs):
        try:
            stopping_result = check_stopping_keywords(user_message)
            if stopping_result != "ok":
                return (
                    Result_ProcessUserInput(status="error", response=stopping_result),
                    cls,
                )
            elif check_human_heritable_editing(user_message) and (
                not kwargs["memory"].get("flag_human_heritable_editing_ack", False)
            ):
                kwargs["memory"]["flag_human_heritable_editing_ack"] = True
                kwargs["memory"]["cached_user_message_before_ack"] = user_message
                return Result_ProcessUserInput(
                    status="error", response=WARNING_HUMAN_HERITABLE_EDITING
                ), make_check_ack_state(cls)
            else:
                if user_message.startswith("Q:"):
                    qa_result = OpenAIChat.QA(user_message, use_GPT4=True)
                    return Result_ProcessUserInput(response=qa_result), cls
                else:
                    return cls.step(user_message, **kwargs)
        except Exception as ex:
            logger.info(["Error occured", ex])
            return (
                Result_ProcessUserInput(
                    status="error",
                    response="Error occured. Error Message: "
                    + str(ex)
                    + " Let's try again.",
                ),
                cls,
            )


class gradio_state_machine:
    """ For automation mode only."""
    def __init__(self, task_list):
        self.MAX_ITER = 100
        self.full_task_list = task_list
        self.reset()

    def reset(self):
        self.todo_task_list = self.full_task_list[:]
        self.current_state = self.todo_task_list.pop(0)
        self.memory = dict()
        self.cached_message = []
        self.state_stack = []

    def append_message(self, s):
        self.cached_message.append(s)
        # self.cached_message += '\n\n'

    def clear_message(self):
        display = self.cached_message
        self.cached_message = []
        return display

    def loop(self, user_message, email="", files=[]):
        for _ in range(self.MAX_ITER):
            response, next_state = self.current_state.safe_step(
                user_message,
                memory=self.memory,
                email=email,
                files=files,
                is_automation=True,
            )
            # logger.info(self.current_state.__name__)
            self.memory[self.current_state.__name__] = response
            _from_ack_state = self.current_state.__name__ == "StateCheckACK"

            if response.response is not None:
                self.append_message(response.response)
            self.state_stack.append(self.current_state)
            if next_state is None:  # finish a subtask, fetch the next one
                self.current_state = self.todo_task_list.pop(0)
            elif isinstance(
                next_state, list
            ):  ## include a list of entry state of each subtask
                self.todo_task_list.extend(next_state)
                self.current_state = self.todo_task_list.pop(0)
            else:
                self.current_state = (
                    next_state  # continue to next state within the same subtask.
                )
            request_msg = self.current_state.get_request_message()
            if response.status != "error" and len(request_msg) > 0:
                self.append_message(request_msg)

            if self.current_state.isFinal:
                return self.clear_message()  # flush output and wait for next input.
            if self.current_state.request_user_input:
                ## special rule: once the acknowledgement is confirmed, resume
                ## with the input the user had already given. A rejected
                ## acknowledgement must wait for the user instead of replaying
                ## the cache, which would otherwise spin on an empty message.
                cached = self.memory.get("cached_user_message_before_ack")
                if _from_ack_state and response.status != "error" and cached is not None:
                    user_message = cached
                    self.memory["cached_user_message_before_ack"] = None
                else:
                    return self.clear_message()  # flush output and wait for next input.
            else:
                user_message = None


@dataclass
class GradioMachineStateClass:
    full_task_list: Optional[List] = None
    todo_task_list: Optional[List] = None
    current_state: Optional[Any] = None
    memory: Optional[Dict] = field(default_factory=dict)
    cached_message: Optional[List] = field(default_factory=list)
    state_stack: Optional[List] = field(default_factory=list)


class concurrent_gradio_state_machine:
    MAX_ITER = 100
    """
        Use Gradio.State to manage states within sessions.
    """

    # def __init__(cls, task_list):
    #     cls.full_task_list = task_list
    #     cls.reset()
    @classmethod
    def reset(cls, mystate):
        mystate.todo_task_list = mystate.full_task_list[:]
        mystate.current_state = mystate.todo_task_list.pop(0)
        mystate.memory = dict()
        mystate.cached_message = []
        mystate.state_stack = []

    @classmethod
    def append_message(cls, s, mystate):
        mystate.cached_message.append(s)
        # cls.cached_message += '\n\n'

    @classmethod
    def clear_message(cls, mystate):
        display = mystate.cached_message
        mystate.cached_message = []
        return display

    @classmethod
    def loop(cls, user_message, mystate, email="", files=[]):
        for _ in range(cls.MAX_ITER):
            response, next_state = mystate.current_state.safe_step(
                user_message=user_message,
                memory=mystate.memory,
                email=email,
                files=files,
                is_automation=False,
            )
            # logger.info(mystate.current_state.__name__)
            mystate.memory[mystate.current_state.__name__] = response
            _from_ack_state = mystate.current_state.__name__ == "StateCheckACK"

            if response.response is not None:
                cls.append_message(response.response, mystate)
            mystate.state_stack.append(mystate.current_state)
            if next_state is None:  # finish a subtask, fetch the next one
                mystate.current_state = mystate.todo_task_list.pop(0)
            elif isinstance(
                next_state, list
            ):  ## include a list of entry state of each subtask
                mystate.todo_task_list.extend(next_state)
                mystate.current_state = mystate.todo_task_list.pop(0)
            else:
                mystate.current_state = (
                    next_state  # continue to next state within the same subtask.
                )
            request_msg = mystate.current_state.get_request_message()
            if response.status != "error" and len(request_msg) > 0:
                cls.append_message(request_msg, mystate)

            if mystate.current_state.isFinal:
                return cls.clear_message(
                    mystate
                )  # flush output and wait for next input.
            if mystate.current_state.request_user_input:
                ## special rule: once the acknowledgement is confirmed, resume
                ## with the input the user had already given. A rejected
                ## acknowledgement must wait for the user instead of replaying
                ## the cache, which would otherwise spin on an empty message.
                cached = mystate.memory.get("cached_user_message_before_ack")
                if _from_ack_state and response.status != "error" and cached is not None:
                    user_message = cached
                    mystate.memory["cached_user_message_before_ack"] = None
                else:
                    return cls.clear_message(
                        mystate
                    )  # flush output and wait for next input.
            else:
                user_message = None


class StateFinal(BaseState):
    request_user_input = False
    isFinal = True
    request_message = "Finished. Clear the current chat or start a new one."


class EmptyState(BaseState):
    @classmethod
    def step(cls, user_message, **kwargs):
        return Result_ProcessUserInput(), None


class EmptyStateFinal(BaseState):
    request_user_input = False
    isFinal = True
    request_message = ""


RESPONSE_ACK_NOT_CONFIRMED = (
    "Not confirmed. Type 'yes' to acknowledge the notice above and continue, "
    "or start a new chat to change your request."
)


class StateCheckACK(BaseUserInputState):
    def __init__(self, ret=None):
        self.ret = ret
        self.__name__ = "StateCheckACK"

    def safe_step(cls, user_message, **kwargs):
        try:
            stopping_result = check_stopping_keywords(user_message)
            if stopping_result != "ok":
                return (
                    Result_ProcessUserInput(status="error", response=stopping_result),
                    cls,
                )
            elif check_human_heritable_editing(user_message) and (
                not kwargs["memory"].get("flag_human_heritable_editing_ack", False)
            ):
                kwargs["memory"]["flag_human_heritable_editing_ack"] = True
                kwargs["memory"]["cached_user_message_before_ack"] = user_message
                return Result_ProcessUserInput(
                    status="error", response=WARNING_HUMAN_HERITABLE_EDITING
                ), make_check_ack_state(cls)
            else:
                if user_message.startswith("Q:"):
                    qa_result = OpenAIChat.QA(user_message, use_GPT4=True)
                    return Result_ProcessUserInput(response=qa_result), cls
                else:
                    return cls.step(user_message, **kwargs)
        except Exception as ex:
            logger.info(["Error occured", ex])
            return (
                Result_ProcessUserInput(
                    status="error",
                    response="Error occured. Error Message: "
                    + str(ex)
                    + " Let's try again.",
                ),
                cls,
            )

    def step(self, user_message, **kwargs):
        if user_message.strip().lower() in ["y", "yes"]:
            return Result_ProcessUserInput(status="success"), self.ret
        else:
            # Without an explicit response the UI would show nothing at all and
            # the user would have no idea the input was rejected.
            return (
                Result_ProcessUserInput(
                    status="error", response=RESPONSE_ACK_NOT_CONFIRMED
                ),
                self,
            )


def make_check_ack_state(ret):
    return StateCheckACK(ret)
