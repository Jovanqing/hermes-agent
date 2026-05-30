"""
Agent node executor for workflow system.

Executes LLM agent nodes by:
1. Resolving input variables from context
2. Building the prompt from template
3. Calling the LLM (via hermes-agent or standalone)
4. Streaming output tokens
5. Returning structured results
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union

from workflow.models import (
    AgentNodeData,
    NodeExecutionStatus,
    NodeType,
    WorkflowContext,
    WorkflowNode,
)
from workflow.nodes.base import (
    BaseNodeExecutor,
    ExecutionContext,
    NodeExecutionResult,
)
from workflow.nodes.input_resolver import (
    InputResolver,
    prepare_agent_inputs,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LLM Provider interface
# ---------------------------------------------------------------------------


@dataclass
class LLMResponse:
    """Response from an LLM provider.

    Attributes:
        content: The generated text
        tokens: Token usage statistics
        finish_reason: Why generation stopped
        model: The model that was used
        raw_response: The raw provider response (optional)
    """

    content: str
    tokens: Dict[str, int]
    finish_reason: str = "stop"
    model: str = ""
    raw_response: Any = None


class LLMProvider:
    """Abstract interface for LLM providers.

    Implement this to connect different LLM backends.
    """

    async def generate(
        self,
        prompt: str,
        model: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a response from the LLM.

        Args:
            prompt: The user prompt
            model: The model to use
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            tools: Optional tool definitions

        Returns:
            LLMResponse with the generated content
        """
        raise NotImplementedError("Subclasses must implement generate()")

    async def generate_stream(
        self,
        prompt: str,
        model: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Generate a response with streaming.

        Yields tokens as they are generated.

        Args:
            prompt: The user prompt
            model: The model to use
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            tools: Optional tool definitions

        Yields:
            str: Individual tokens
        """
        # Default implementation: call generate and yield the result
        response = await self.generate(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            **kwargs,
        )
        yield response.content


# ---------------------------------------------------------------------------
# Hermes Agent Provider
# ---------------------------------------------------------------------------


class HermesAgentProvider(LLMProvider):
    """LLM provider that uses the hermes-agent runtime.

    Integrates with the hermes-agent's conversation loop and tool execution.
    """

    def __init__(self, agent: Any = None):
        """Initialize with an optional agent instance.

        Args:
            agent: A hermes-agent AIAgent instance. If None, will try to
                   create one lazily.
        """
        self._agent = agent

    def _get_agent(self) -> Any:
        """Get or create the agent instance."""
        if self._agent is not None:
            return self._agent

        # Try to import and create agent
        try:
            # This would be the actual hermes-agent initialization
            # For now, we'll raise to fall back to mock
            raise ImportError("Hermes agent not configured")
        except ImportError:
            raise RuntimeError(
                "Hermes agent not available. Use MockProvider for testing "
                "or configure the hermes-agent runtime."
            )

    async def generate(
        self,
        prompt: str,
        model: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate using hermes-agent's conversation loop."""
        # For now, delegate to stream and collect
        tokens = []
        token_usage = {"prompt": 0, "completion": 0}

        async for token in self.generate_stream(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            **kwargs,
        ):
            tokens.append(token)

        content = "".join(tokens)

        return LLMResponse(
            content=content,
            tokens=token_usage,
            finish_reason="stop",
            model=model,
        )

    async def generate_stream(
        self,
        prompt: str,
        model: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Generate with streaming using hermes-agent."""
        # This is where we'd integrate with the actual hermes-agent
        # For now, yield a placeholder
        yield f"[Hermes Agent would process: {prompt[:50]}...]"


# ---------------------------------------------------------------------------
# Mock Provider (for testing)
# ---------------------------------------------------------------------------


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing.

    Returns predictable responses based on the prompt.
    """

    def __init__(
        self,
        responses: Optional[Dict[str, str]] = None,
        default_response: str = "Mock response",
        delay: float = 0.0,
    ):
        """Initialize the mock provider.

        Args:
            responses: Dict mapping prompts to responses
            default_response: Response when no match found
            delay: Simulated delay in seconds
        """
        self.responses = responses or {}
        self.default_response = default_response
        self.delay = delay
        self.call_history: List[Dict[str, Any]] = []

    async def generate(
        self,
        prompt: str,
        model: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a mock response."""
        self.call_history.append({
            "prompt": prompt,
            "model": model,
            "system_prompt": system_prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
        })

        if self.delay > 0:
            await asyncio.sleep(self.delay)

        # Find matching response
        content = self.default_response
        for key, response in self.responses.items():
            if key in prompt:
                content = response
                break

        return LLMResponse(
            content=content,
            tokens={
                "prompt": len(prompt.split()),
                "completion": len(content.split()),
            },
            finish_reason="stop",
            model=model,
        )

    async def generate_stream(
        self,
        prompt: str,
        model: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Generate with mock streaming."""
        response = await self.generate(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            **kwargs,
        )

        # Yield word by word for streaming effect
        words = response.content.split()
        for i, word in enumerate(words):
            if self.delay > 0:
                await asyncio.sleep(self.delay / len(words))
            yield word + (" " if i < len(words) - 1 else "")


# ---------------------------------------------------------------------------
# Agent Node Executor
# ---------------------------------------------------------------------------


class AgentNodeExecutor(BaseNodeExecutor):
    """Executor for agent nodes.

    Handles:
    - Input variable resolution
    - Prompt template processing
    - LLM API calls (with streaming)
    - Result collection and storage
    """

    node_type = "agent"

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        **kwargs: Any,
    ):
        """Initialize the agent executor.

        Args:
            provider: LLM provider to use. If None, uses MockLLMProvider.
            **kwargs: Additional configuration
        """
        super().__init__(**kwargs)
        self.provider = provider or MockLLMProvider()

    async def execute(self, context: ExecutionContext) -> NodeExecutionResult:
        """Execute an agent node.

        Args:
            context: Execution context

        Returns:
            NodeExecutionResult with the agent's response
        """
        start_time = time.time()
        node = context.node

        try:
            # Get typed data
            typed_data = node.get_typed_data()
            if not isinstance(typed_data, AgentNodeData):
                return NodeExecutionResult.error(
                    node_id=node.id,
                    error="Node data is not AgentNodeData",
                )

            # Prepare inputs
            resolved_prompt, system_prompt, resolved_vars = prepare_agent_inputs(
                node, context.workflow_context
            )

            context.emit_event("prompt_resolved", {
                "prompt": resolved_prompt[:100] + "..." if len(resolved_prompt) > 100 else resolved_prompt,
            })

            # Collect tokens via streaming
            tokens_buffer: List[str] = []
            token_usage = {"prompt": 0, "completion": 0}

            async for item in self.provider.generate_stream(
                prompt=resolved_prompt,
                model=typed_data.model,
                system_prompt=system_prompt,
                temperature=typed_data.temperature,
                max_tokens=typed_data.max_tokens,
            ):
                if context.is_cancelled():
                    return NodeExecutionResult.error(
                        node_id=node.id,
                        error="Execution cancelled",
                    )

                tokens_buffer.append(item)
                context.emit_token(item)

            duration = time.time() - start_time
            output = "".join(tokens_buffer)

            context.emit_event("execution_complete", {
                "duration": duration,
                "output_length": len(output),
            })

            return NodeExecutionResult.success(
                node_id=node.id,
                output=output,
                tokens=token_usage,
                duration=duration,
                model=typed_data.model,
                prompt_tokens=len(resolved_prompt.split()),
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.exception("Agent node %s execution failed", node.id)
            return NodeExecutionResult.error(
                node_id=node.id,
                error=str(e),
                duration=duration,
            )

    async def execute_stream(
        self,
        context: ExecutionContext,
    ) -> AsyncIterator[Union[str, NodeExecutionResult]]:
        """Execute with true streaming.

        Yields tokens as they arrive, then yields the final result.
        """
        start_time = time.time()
        node = context.node

        try:
            # Get typed data
            typed_data = node.get_typed_data()
            if not isinstance(typed_data, AgentNodeData):
                yield NodeExecutionResult.error(
                    node_id=node.id,
                    error="Node data is not AgentNodeData",
                )
                return

            # Prepare inputs
            resolved_prompt, system_prompt, resolved_vars = prepare_agent_inputs(
                node, context.workflow_context
            )

            context.emit_event("prompt_resolved", {
                "prompt": resolved_prompt[:100] + "..." if len(resolved_prompt) > 100 else resolved_prompt,
            })

            # Stream tokens
            tokens_buffer: List[str] = []
            token_usage = {"prompt": 0, "completion": 0}

            async for token in self.provider.generate_stream(
                prompt=resolved_prompt,
                model=typed_data.model,
                system_prompt=system_prompt,
                temperature=typed_data.temperature,
                max_tokens=typed_data.max_tokens,
            ):
                if context.is_cancelled():
                    yield NodeExecutionResult.error(
                        node_id=node.id,
                        error="Execution cancelled",
                    )
                    return

                tokens_buffer.append(token)
                yield token  # Yield the token to caller

            duration = time.time() - start_time
            output = "".join(tokens_buffer)

            # Yield final result
            yield NodeExecutionResult.success(
                node_id=node.id,
                output=output,
                tokens=token_usage,
                duration=duration,
                model=typed_data.model,
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.exception("Agent node %s streaming failed", node.id)
            yield NodeExecutionResult.error(
                node_id=node.id,
                error=str(e),
                duration=duration,
            )

    def validate_node(self, node: WorkflowNode) -> List[str]:
        """Validate an agent node configuration."""
        errors = super().validate_node(node)

        typed_data = node.get_typed_data()
        if not isinstance(typed_data, AgentNodeData):
            errors.append("Node data must be AgentNodeData")
            return errors

        if not typed_data.prompt:
            errors.append("Agent node must have a prompt")

        if not typed_data.model:
            errors.append("Agent node must specify a model")

        if not (0.0 <= typed_data.temperature <= 2.0):
            errors.append(f"Temperature must be between 0 and 2, got {typed_data.temperature}")

        if typed_data.max_tokens <= 0:
            errors.append(f"max_tokens must be positive, got {typed_data.max_tokens}")

        return errors


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------


def create_agent_executor(
    provider: Optional[LLMProvider] = None,
    use_hermes: bool = False,
    agent: Any = None,
) -> AgentNodeExecutor:
    """Create an agent executor with the specified provider.

    Args:
        provider: Custom LLM provider to use
        use_hermes: If True, use HermesAgentProvider
        agent: Hermes agent instance (for HermesAgentProvider)

    Returns:
        Configured AgentNodeExecutor
    """
    if provider is not None:
        return AgentNodeExecutor(provider=provider)

    if use_hermes:
        return AgentNodeExecutor(provider=HermesAgentProvider(agent=agent))

    # Default to mock for testing
    return AgentNodeExecutor(provider=MockLLMProvider())
