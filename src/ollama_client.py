"""
Ollama Chat Completion Client for AutoGen
This module provides an Ollama-compatible client that implements the ChatCompletionClient interface.
"""
import os
from typing import Any, Optional, Sequence, List, Dict, Union, AsyncGenerator
import aiohttp
import json

from autogen_core.models import (
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
    AssistantMessage,
    FunctionExecutionResultMessage,
    CreateResult,
    RequestUsage,
)


class OllamaChatCompletionClient(ChatCompletionClient):
    """
    A ChatCompletionClient implementation for Ollama.
    
    This client connects to a local or remote Ollama instance and provides
    compatibility with the AutoGen framework.
    """

    def __init__(
        self,
        model: str = "deepseek-r1:1.5b",
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs: Any
    ):
        """
        Initialize the Ollama client.
        
        Args:
            model: The Ollama model to use (e.g., 'deepseek-r1:1.5b', 'llama2', 'mistral')
            base_url: The base URL for the Ollama API (default: http://localhost:11434)
            temperature: Sampling temperature (0.0 to 1.0)
            **kwargs: Additional arguments
        """
        self._model = model
        self._base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._temperature = temperature
        self._api_url = f"{self._base_url}/api/chat"
        self._kwargs = kwargs

    @property
    def capabilities(self) -> Dict[str, Any]:
        """Return the capabilities of this client."""
        # Function calling is problematic with most Ollama models
        # Disable it to avoid parsing errors
        # Models often generate malformed JSON for tool calls
        
        return {
            "vision": False,
            "function_calling": False,  # Disabled due to parsing issues
            "json_output": True,
            "structured_output": False,
        }

    @property
    def model_info(self) -> Dict[str, Any]:
        """Return information about the model."""
        return {
            "model": self._model,
            "base_url": self._base_url,
            "temperature": self._temperature,
            **self.capabilities
        }

    def _convert_messages(self, messages: Sequence[LLMMessage]) -> List[Dict[str, str]]:
        """
        Convert AutoGen messages to Ollama format.
        
        Args:
            messages: Sequence of LLMMessage objects
            
        Returns:
            List of message dictionaries for Ollama API
        """
        ollama_messages = []
        
        for msg in messages:
            if isinstance(msg, SystemMessage):
                ollama_messages.append({
                    "role": "system",
                    "content": msg.content
                })
            elif isinstance(msg, UserMessage):
                ollama_messages.append({
                    "role": "user",
                    "content": msg.content
                })
            elif isinstance(msg, AssistantMessage):
                ollama_messages.append({
                    "role": "assistant",
                    "content": msg.content
                })
            elif isinstance(msg, FunctionExecutionResultMessage):
                # Ollama doesn't natively support function results, so we format them as user messages
                ollama_messages.append({
                    "role": "user",
                    "content": f"Function result: {msg.content}"
                })
                
        return ollama_messages

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Optional[List[Any]] = None,
        json_output: Optional[bool] = None,
        extra_create_args: Optional[Dict[str, Any]] = None,
        cancellation_token: Optional[Any] = None,
    ) -> CreateResult:
        """
        Create a completion using the Ollama API.
        
        Args:
            messages: The conversation messages
            tools: Tools/functions (supported for compatible models)
            json_output: Whether to request JSON output
            extra_create_args: Additional arguments
            cancellation_token: Cancellation token (not used)
            
        Returns:
            CreateResult with the completion
        """
        ollama_messages = self._convert_messages(messages)
        
        payload = {
            "model": self._model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": self._temperature,
            }
        }
        
        # Add tools if provided and supported
        if tools and self.capabilities["function_calling"]:
            ollama_tools = []
            
            for tool in tools:
                # Tool could be a function or a dict/schema
                if isinstance(tool, dict):
                    # Already in schema format
                    ollama_tools.append(tool)
                elif callable(tool):
                    # Convert function to Ollama tool format
                    import inspect
                    
                    sig = inspect.signature(tool)
                    params_schema = {"type": "object", "properties": {}, "required": []}
                    
                    for param_name, param in sig.parameters.items():
                        param_info = {"type": "string", "description": ""}
                        
                        # Try to extract type and description from annotations
                        if param.annotation != inspect.Parameter.empty:
                            ann = param.annotation
                            
                            # Handle Annotated types
                            if hasattr(ann, '__origin__') and hasattr(ann, '__metadata__'):
                                # Annotated[type, description]
                                if ann.__metadata__:
                                    param_info["description"] = ann.__metadata__[0]
                                # Get actual type
                                actual_type = ann.__args__[0] if hasattr(ann, '__args__') else ann
                                if actual_type == int:
                                    param_info["type"] = "integer"
                                elif actual_type == float:
                                    param_info["type"] = "number"
                                elif actual_type == bool:
                                    param_info["type"] = "boolean"
                            elif ann == int:
                                param_info["type"] = "integer"
                            elif ann == float:
                                param_info["type"] = "number"
                            elif ann == bool:
                                param_info["type"] = "boolean"
                            elif ann == list or (hasattr(ann, '__origin__') and ann.__origin__ == list):
                                param_info["type"] = "array"
                        
                        params_schema["properties"][param_name] = param_info
                        
                        # Required if no default value
                        if param.default == inspect.Parameter.empty:
                            params_schema["required"].append(param_name)
                    
                    tool_schema = {
                        "type": "function",
                        "function": {
                            "name": tool.__name__,
                            "description": (tool.__doc__ or f"Function {tool.__name__}").strip(),
                            "parameters": params_schema
                        }
                    }
                    ollama_tools.append(tool_schema)
            
            if ollama_tools:
                payload["tools"] = ollama_tools
        
        # Add JSON mode if requested
        if json_output:
            payload["format"] = "json"
        
        # Merge extra args
        if extra_create_args:
            payload.update(extra_create_args)

        async with aiohttp.ClientSession() as session:
            async with session.post(self._api_url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Ollama API error: {response.status} - {error_text}")
                
                result = await response.json()
                
                content = result.get("message", {}).get("content", "")
                
                # Extract usage information if available
                usage = RequestUsage(
                    prompt_tokens=result.get("prompt_eval_count", 0),
                    completion_tokens=result.get("eval_count", 0),
                )
                
                return CreateResult(
                    content=content,
                    usage=usage,
                    finish_reason="stop",
                    cached=False,
                )

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Optional[List[Any]] = None,
        json_output: Optional[bool] = None,
        extra_create_args: Optional[Dict[str, Any]] = None,
        cancellation_token: Optional[Any] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        """
        Create a streaming completion using the Ollama API.
        
        Args:
            messages: The conversation messages
            tools: Tools/functions (not supported)
            json_output: Whether to request JSON output
            extra_create_args: Additional arguments
            cancellation_token: Cancellation token (not used)
            
        Yields:
            Chunks of text or the final CreateResult
        """
        ollama_messages = self._convert_messages(messages)
        
        payload = {
            "model": self._model,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": self._temperature,
            }
        }
        
        if json_output:
            payload["format"] = "json"
            
        if extra_create_args:
            payload.update(extra_create_args)

        full_content = ""
        prompt_tokens = 0
        completion_tokens = 0

        async with aiohttp.ClientSession() as session:
            async with session.post(self._api_url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Ollama API error: {response.status} - {error_text}")
                
                async for line in response.content:
                    if line:
                        try:
                            chunk = json.loads(line.decode('utf-8'))
                            
                            if "message" in chunk:
                                content = chunk["message"].get("content", "")
                                if content:
                                    full_content += content
                                    yield content
                            
                            # Track token usage
                            if "prompt_eval_count" in chunk:
                                prompt_tokens = chunk["prompt_eval_count"]
                            if "eval_count" in chunk:
                                completion_tokens = chunk["eval_count"]
                                
                            # Check if done
                            if chunk.get("done", False):
                                usage = RequestUsage(
                                    prompt_tokens=prompt_tokens,
                                    completion_tokens=completion_tokens,
                                )
                                yield CreateResult(
                                    content=full_content,
                                    usage=usage,
                                    finish_reason="stop",
                                    cached=False,
                                )
                        except json.JSONDecodeError:
                            continue

    def remaining_tokens(self, messages: Sequence[LLMMessage]) -> int:
        """
        Estimate remaining tokens (Ollama-specific models have varying context lengths).
        
        Args:
            messages: The conversation messages
            
        Returns:
            Estimated remaining tokens
        """
        # Rough estimation: most Ollama models support 2048-4096 tokens
        # This is a simple heuristic
        total_chars = sum(len(str(msg.content)) for msg in messages)
        estimated_tokens = total_chars // 4  # Rough approximation
        context_length = 2048  # Conservative estimate
        return max(0, context_length - estimated_tokens)

    def total_tokens(self, messages: Sequence[LLMMessage]) -> int:
        """
        Estimate total tokens used.
        
        Args:
            messages: The conversation messages
            
        Returns:
            Estimated total tokens
        """
        total_chars = sum(len(str(msg.content)) for msg in messages)
        return total_chars // 4  # Rough approximation

    def count_tokens(self, messages: Sequence[LLMMessage]) -> int:
        """
        Count tokens in messages.
        
        Args:
            messages: The conversation messages
            
        Returns:
            Estimated token count
        """
        return self.total_tokens(messages)

    def actual_usage(self) -> RequestUsage:
        """
        Get actual usage statistics.
        
        Returns:
            RequestUsage with zeros (not tracked)
        """
        return RequestUsage(prompt_tokens=0, completion_tokens=0)

    def total_usage(self) -> RequestUsage:
        """
        Get total usage statistics.
        
        Returns:
            RequestUsage with zeros (not tracked)
        """
        return RequestUsage(prompt_tokens=0, completion_tokens=0)

    async def close(self) -> None:
        """Clean up resources."""
        pass  # No persistent connections to close
