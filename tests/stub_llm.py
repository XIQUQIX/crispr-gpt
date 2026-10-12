"""A scripted stand-in for the OpenAI client.

Rules match on a distinctive fragment of each prompt, so the state machine can
be walked end to end without an API key and without any network traffic.
"""

import llm


class StubLLM:
    def __init__(self, rules):
        """rules: list of (prompt_fragment, response_dict)."""
        self.rules = rules
        self.calls = []

    def chat(self, request, use_GPT4=True, use_GPT4_turbo=False):
        # Keep the real privacy guard in the loop; it is part of what we test.
        if llm.contains_identifiable_genes(request):
            raise llm.IdentifiableGeneError(llm.WARNING_PRIVACY)
        self.calls.append(request)
        for fragment, response in self.rules:
            if fragment in request:
                return response
        raise AssertionError(
            f"StubLLM has no rule matching this prompt:\n{request[:400]}..."
        )

    def QA(self, request, use_GPT4=False):
        return "stub QA"


class install:
    """Context manager swapping OpenAIChat for a stub everywhere it is used."""

    def __init__(self, rules):
        self.stub = StubLLM(rules)

    def __enter__(self):
        self._saved = (llm.OpenAIChat.chat, llm.OpenAIChat.QA)
        llm.OpenAIChat.chat = self.stub.chat
        llm.OpenAIChat.QA = self.stub.QA
        return self.stub

    def __exit__(self, *exc):
        llm.OpenAIChat.chat, llm.OpenAIChat.QA = self._saved
        return False
