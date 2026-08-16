"""Marks the root span of each LLM call/workflow with `gen_ai.is_llm_root`.

OpenLLMetry's default auto-instrumentation doesn't set this attribute on its
own. Observe's LLM Explorer (the "LLMs beta" view) uses it to find and group
LLM traces -- without it, spans still show up in the generic Traces view,
but never in LLM Explorer. See:
https://docs.observeinc.com/docs/llm-instrumentation
"""

from typing import Optional

from opentelemetry import context
from opentelemetry.context import Context
from opentelemetry.sdk.trace import Span
from opentelemetry.sdk.trace.export import BatchSpanProcessor


class LLMExplorerSpanProcessor(BatchSpanProcessor):
    def on_start(self, span: Span, parent_context: Optional[Context] = None) -> None:
        association_properties = context.get_value("association_properties", parent_context)
        parent_is_llm_span = context.get_value("IS_LLM_SPAN", parent_context)

        if association_properties is not None and (
            not parent_is_llm_span or str(parent_is_llm_span).lower() == "false"
        ):
            span.set_attribute("gen_ai.is_llm_root", True)
