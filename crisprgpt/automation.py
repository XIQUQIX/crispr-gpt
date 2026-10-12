from .logic import BaseState, Result_ProcessUserInput, BaseUserInputState
from llm import OpenAIChat, IdentifiableGeneError
from .logic import StateFinal, gradio_state_machine, EmptyState, EmptyStateFinal
from .tasks import render_task_table, resolve, UnknownTask

from dataclasses import dataclass
from typing import Optional, List
from util import get_logger
logger = get_logger(__name__)

@dataclass
class ExecutorState:
    user_prompt: Optional[str] = None
    cached_message: Optional[List] = None  
    flag_user_ack: bool = False 
    cached_user_input: Optional[str] = None



PROMPT_PROCESS_AUTOMATE = """
Please act as an expert in CRISPR technology. Given the user input, think step by step and generate a list of tasks for execution. First refer to the task description table below, and try to figure out if the user needs to directly jump into a task, or the user needs to complete several tasks. Make sure to respect the task dependencies and include all dependent tasks in the list.

Please make sure the generated list of tasks are in the order indicated in the task description table. Please format your response and make sure it is parsable by JSON.

## Task Description Table

{task_table}

## Demonstrations:
If the user only needs to design guideRNA for knockout, then return ['knockout.StateStep1', 'knockout.StateStep3']. Reason: this directly matches knockout.StateStep3. But it needs to complete knockout.StateStep1 first, so both 'knockout.StateStep1' and 'knockout.StateStep3' are returned.


User Input:

{user_message}

Response format:

{{
"Thoughts": "<thoughts>",
"Tasks": ["<task1>", "<task2>"]  ## a list of task names
}}"""

TASK_TABLE = render_task_table()

RESPONSE_UNKNOWN_TASK = (
    "Sorry, I could not map your request onto the supported design tasks. "
    "Please rephrase it, or use Meta-Mode for a guided pipeline."
)


class StateAutomate(BaseUserInputState):
    prompt_process = PROMPT_PROCESS_AUTOMATE
    request_message = "Please directly type in your need."

    @classmethod
    def step(cls, user_message, **kwargs):
        prompt = cls.prompt_process.format(
            user_message=user_message, task_table=TASK_TABLE
        )
        response = OpenAIChat.chat(prompt, use_GPT4=True)
        logger.info(response["Tasks"])

        try:
            # Resolve by name against the catalogue. The planner's output is
            # untrusted text and must never reach eval().
            tasks = resolve(response["Tasks"])
        except UnknownTask as ex:
            logger.info(["Planner returned an unknown task", ex])
            return (
                Result_ProcessUserInput(
                    status="error", response=RESPONSE_UNKNOWN_TASK
                ),
                cls,
            )

        tasks = [EmptyState, *tasks, EmptyStateFinal]
        executor = gradio_state_machine(task_list=tasks)
        kwargs["memory"]["executor"] = executor
        # Carry over whether the heritable-editing notice has already been
        # shown for this session. Hard-coding True here would let auto mode
        # bypass a check that is meant to apply to every task.
        executor.memory["flag_human_heritable_editing_ack"] = kwargs["memory"].get(
            "flag_human_heritable_editing_ack", False
        )
        kwargs["memory"]["executor_state"] = ExecutorState(
            user_prompt=user_message, cached_message=[], flag_user_ack=True
        )

        return Result_ProcessUserInput(
            status="success",
            thoughts=response["Thoughts"],
            result=user_message,
            response=str(response),
        ), StateAutomateStep

class StateAutomateYesNo(BaseUserInputState):  
    
    @classmethod
    def step(cls, user_message, **kwargs): 
        if user_message.strip() != "":
            kwargs['memory']['executor_state'].cached_user_input = user_message
        return Result_ProcessUserInput(), StateAutomateStep


class StateAutomateStep(BaseState):  
    @classmethod
    def FallbackState(cls):
        return StateFinal
    
    @classmethod
    def step(cls, user_message, **kwargs):  
        executor = kwargs['memory']['executor']
        executor_state = kwargs['memory']['executor_state']
        user_message = executor_state.cached_user_input
        cached_message = executor_state.cached_message
        meta_prompt = executor_state.user_prompt


        if len(cached_message) > 0: 
            # display message one by one
            executor_state.flag_user_ack = False
            return Result_ProcessUserInput(response=cached_message.pop(0)), StateAutomateStep
        else: 
            if executor_state.flag_user_ack: 
                # we've got user acknowledgement, loop and get to next state.

                list_bot_message = executor.loop(user_message, email=kwargs["email"])
                executor_state.cached_message = list_bot_message[:]

                if not executor.current_state.isFinal:   
                    generated_response = cls.gen_response(meta_prompt=meta_prompt, system_message=list_bot_message)
                    generated_answer = str(generated_response['Answer'])
                    generated_rational = generated_response['Thoughts']

                    executor_state.cached_user_input = generated_answer
                    generated_answer = "Here is the GPT-suggested answer: \n\n" + generated_answer + '\n\n\n Reason: \n' + generated_rational
                    executor_state.cached_message.append(generated_answer)  

                executor_state.flag_user_ack = False
                return Result_ProcessUserInput(), StateAutomateStep
            else:
                if not executor.current_state.isFinal:  
                    # Send to user for acknowledgement.
                    executor_state.flag_user_ack = True
                    return Result_ProcessUserInput(response=RESPONSE_CHECK_USER), StateAutomateYesNo
                else:
                    return Result_ProcessUserInput(), StateFinal

                
                
    @classmethod
    def gen_response(cls, meta_prompt, system_message):  
        system_message = [msg for msg in system_message if isinstance(msg, str)]
        system_message = '\n\n'.join(system_message)
        try:
            prompt = PROMPT_GENERATE_USER_RESPONSE.format(meta_prompt= meta_prompt, system_message = system_message)
            logger.info(prompt)
            response = OpenAIChat.chat(prompt, use_GPT4=True) 
            logger.info(response)
            return response 
        except IdentifiableGeneError:
            logger.info(["Not supported in Automated Mode"])
            return dict(Thoughts="Input/Output may contain sensitive sequences. This is not supported in Automation mode! Please manually enter your response!", Answer="I don't know")
        except Exception as ex:
            logger.info(["Error occured", ex])
            # Concatenating the exception object here used to raise a
            # TypeError of its own, hiding the original failure.
            return dict(
                Thoughts=f"An error occurred ({ex}). Please manually enter your response!",
                Answer="I don't know",
            )



RESPONSE_CHECK_USER = "Press Enter to continue with the generated answer. Enter other text to correct answer"

 

PROMPT_GENERATE_USER_RESPONSE="""
Please act as you are using the CRISPR design tool. Given the user meta request, the current inquiry provided by the tool, think step by step and generate an answer to the questions. Please format your response and make sure it is parsable by JSON.

Rules:

1. Answer the inquiry directly on behalf of the user. Don't raise any additional question to the user.
2. If the inquiry is a multiple-choice question, then directly output one choice. 
3. If the inquiry asks you to supply any gene sequence, then answer the question with "I don't know" and let the user take manual control.

User Meta Request:

"{meta_prompt}"

Current Inquiry:

"{system_message}"

Response format:

{{
"Thoughts": "<thoughts>",
"Answer": "<response string>"
}}"""
 

class AutomationEntryState(BaseState):
    @classmethod 
    def step(cls, user_message, **kwargs):
        return Result_ProcessUserInput(), StateAutomate
