from evals.base import EvalAdapter, EvalResult
from evals.bash_script import BashScriptAdapter
from evals.http_endpoint import HttpEndpointAdapter
from evals.llm_judge import LLMJudgeAdapter
from evals.python_script import PythonScriptAdapter

ADAPTERS = {
    "python_script": PythonScriptAdapter,
    "bash_script": BashScriptAdapter,
    "bash": BashScriptAdapter,
    "llm_judge": LLMJudgeAdapter,
    "http_endpoint": HttpEndpointAdapter,
    "http": HttpEndpointAdapter,
}


def get_adapter(eval_type: str, config: dict | None = None) -> EvalAdapter:
    """Get an eval adapter by type name."""
    adapter_cls = ADAPTERS.get(eval_type)
    if not adapter_cls:
        raise ValueError(
            f"Unknown eval type: {eval_type}. "
            f"Available: {', '.join(ADAPTERS.keys())}"
        )
    return adapter_cls(config or {})


__all__ = [
    "EvalAdapter",
    "EvalResult",
    "PythonScriptAdapter",
    "BashScriptAdapter",
    "LLMJudgeAdapter",
    "HttpEndpointAdapter",
    "get_adapter",
]
