from langchain_openai import ChatOpenAI
import json
from crisprgpt.safety import WARNING_PRIVACY, contains_identifiable_genes
from util import get_logger
import dotenv
import os

dotenv.load_dotenv()
logger = get_logger(__name__)

# Model used for each tier. Kept as named constants so the mapping is explicit
# rather than buried in the call sites.
MODEL_DEFAULT = "gpt-4o"
MODEL_TURBO = "gpt-4-turbo"


class IdentifiableGeneError(ValueError):
    pass


class MissingAPIKeyError(RuntimeError):
    pass


class OpenAIChat:
    _cache = {}

    @classmethod
    def _get_model(cls, model_name):
        """Build (and memoize) a JSON-mode chat model.

        Models are created on first use rather than at import time, so the
        module can be imported -- and the state machine exercised offline --
        without an API key being present.
        """
        if model_name not in cls._cache:
            api_key = os.getenv("OPENAI_KEY")
            if not api_key:
                raise MissingAPIKeyError(
                    "OPENAI_KEY is not set. Add it to a .env file in the project "
                    "root (see README) before running CRISPR-GPT."
                )
            model = ChatOpenAI(openai_api_key=api_key, model_name=model_name)
            cls._cache[model_name] = model.bind(
                response_format={"type": "json_object"}
            )
        return cls._cache[model_name]

    @classmethod
    def chat(cls, request, use_GPT4=True, use_GPT4_turbo=False):
        """Send `request` and parse the reply as JSON.

        Every tier binds JSON response mode; callers always receive a dict.
        """
        if contains_identifiable_genes(request):
            raise IdentifiableGeneError(WARNING_PRIVACY)

        model_name = MODEL_TURBO if use_GPT4_turbo else MODEL_DEFAULT
        response = cls._get_model(model_name).invoke(request).content
        logger.info(response)

        return cls._parse_json(response)

    @staticmethod
    def _parse_json(response):
        """Strip the markdown fence the model sometimes emits, then parse."""
        response = response.strip()
        if response.startswith("```"):
            response = response[3:].removeprefix("json")
            if response.endswith("```"):
                response = response[:-3]
        return json.loads(response.strip())

    @classmethod
    def QA(cls, request, use_GPT4=False):
        """Freestyle Q&A.

        The lite release ships without the curated knowledge base and retrieval
        layer that this mode depends on, so it is unavailable rather than
        answering from the base model alone.
        """
        return (
            "Q&A mode is not available in the lite version: it depends on the "
            "curated knowledge base and retrieval layer, which are not included "
            "in this release."
        )
