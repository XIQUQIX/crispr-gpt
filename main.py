import gradio as gr
from crisprgpt.logic import GradioMachineStateClass, concurrent_gradio_state_machine
from crisprgpt import entry
from util import get_logger
import uuid
from pathlib import Path

logger = get_logger(__name__)
Path("log").mkdir(exist_ok=True)


def initialize_session():
    """Build a fresh, per-browser-session state machine.

    The session lives in a `gr.State` rather than a module global: with
    `share=True` several people can be connected at once, and a global would
    let them overwrite each other's progress.
    """
    session = GradioMachineStateClass(full_task_list=[entry.EntryState])
    session_id = str(uuid.uuid4().hex)
    concurrent_gradio_state_machine.reset(session)

    try:
        init_messages = concurrent_gradio_state_machine.loop(None, session)
        history = [(None, msg) for msg in init_messages]
    except Exception:
        logger.exception("Initialization error")
        history = [
            (None, "CRISPR-GPT ready! How can I assist you with molecular biology?")
        ]
    return history, session, session_id


def save_chat(history, session_id):
    """Save chat history to file"""
    try:
        to_save = ""
        for user_msg, bot_msg in history:
            if user_msg:
                to_save += f"### User: \n{user_msg}\n\n"
            if bot_msg:
                to_save += f"### CRISPR-GPT: \n{bot_msg}\n\n"

        file_path = f"log/{session_id}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(to_save)
        return file_path
    except Exception:
        logger.exception("Save error")
        return ""


def chat_respond(message, history, session, session_id):
    """Process user message"""
    if not message.strip():
        return history, "", session, session_id

    try:
        bot_messages = concurrent_gradio_state_machine.loop(message, session)
    except Exception as e:
        logger.exception("Chat error")
        history.append((message, f"Error: {e}"))
        save_chat(history, session_id)
        return history, "", session, session_id

    if bot_messages:
        for index, bot_msg in enumerate(bot_messages):
            # Attach the user's message to the first reply only, so it is not
            # repeated against every line the machine emitted.
            history.append((message if index == 0 else None, str(bot_msg)))
    else:
        # A state can legitimately produce no output; record the user's turn
        # anyway so it does not vanish from the transcript.
        history.append((message, None))

    save_chat(history, session_id)
    return history, "", session, session_id


def reset_chat():
    history, session, session_id = initialize_session()
    return history, "", session, session_id


# Custom CSS for better chat styling
custom_css = """
/* Override all fonts in the entire app */
* {
    font-family: Arial, sans-serif !important;
}

/* Specific targeting for chatbot */
[data-testid="chatbot"] * {
    font-family: Arial, sans-serif !important;
    font-size: 14px !important;
}

/* Code elements */
pre, code {
    font-family: Courier, monospace !important;
}
"""

# Create the interface
with gr.Blocks(title="CRISPR-GPT", theme=gr.themes.Soft(), css=custom_css) as demo:

    gr.Markdown("# 🧬 CRISPR-GPT")
    gr.Markdown("*AI Assistant for gene editing*")

    session = gr.State()
    session_id = gr.State()

    chatbot = gr.Chatbot(
        height=600,
        show_copy_button=True,
        type="tuples"  # Use tuples for better compatibility
    )

    with gr.Row():
        msg = gr.Textbox(
            placeholder="Ask about gene-editing...",
            container=False,
            scale=4
        )
        send_btn = gr.Button("Send", variant="primary")

    with gr.Row():
        reset_btn = gr.Button("🔄 Reset Session")

    # Event handlers
    chat_inputs = [msg, chatbot, session, session_id]
    chat_outputs = [chatbot, msg, session, session_id]
    send_btn.click(chat_respond, chat_inputs, chat_outputs)
    msg.submit(chat_respond, chat_inputs, chat_outputs)

    reset_btn.click(reset_chat, outputs=chat_outputs)

    # Initialize on load
    demo.load(initialize_session, outputs=[chatbot, session, session_id])

if __name__ == "__main__":
    demo.queue()
    demo.launch(
        share=True,
        allowed_paths=["log/"],
        show_api=False,
        inbrowser=False
    )
