"""
Parsing utilities for RLM trjaectories.
"""

import re

from rlm.core.types import REPLResult, RLMIteration


def find_code_blocks(text: str) -> list[str]:
    """
    Find REPL code blocks in text wrapped in triple backticks and return List of content(s).
    Returns None if no code blocks are found.

    The documented/primary format is ```repl fences. Weaker models drift off it under load
    (observed with deepseek-chat, worse in later turns of a persistent session) -- in every
    observed case the intent (run this Python in the REPL) was unambiguous, just wrapped
    differently, so progressively looser fallbacks are tried rather than stranding the model in
    a silent "no output" loop with no way to tell what went wrong. Observed drift patterns:
    XML-style <repl>...</repl> and <repl_block>...</repl_block>, and a ```python-tagged fence
    (sometimes preceded by a meaningless <code>repl</code> marker). One observed run had 15 of
    21 iterations silently fail to execute this way before the fix -- this is not a rare edge
    case. First pattern with any match wins.
    """
    patterns = [
        r"```repl\s*\n(.*?)\n```",                        # primary/documented
        r"<repl>\s*\n?(.*?)\n?\s*</repl>",                 # XML-tag drift
        r"<repl_block>\s*\n?(.*?)\n?\s*</repl_block>",     # XML-tag drift, variant
        r"```python\s*\n(.*?)\n```",                       # python-tagged fence drift
        r"```\s*\n(.*?)\n```",                             # bare fence, no language tag, last resort
    ]
    for pattern in patterns:
        results = [m.group(1).strip() for m in re.finditer(pattern, text, re.DOTALL)]
        if results:
            return results
    return []


def format_iteration(
    iteration: RLMIteration, max_character_length: int = 20000
) -> list[dict[str, str]]:
    """
    Format an RLM iteration (including all code blocks) to append to the message history for
    the prompt of the LM in the next iteration. We also truncate code execution results
    that exceed the max_character_length.

    Each iteration produces exactly two messages in history: one assistant
    turn containing the model's response (with any ```repl``` blocks
    embedded), followed by a single user message that concatenates the
    outputs of all executed code blocks in that turn. This keeps the
    per-turn shape assistant-then-user even when the model emits several
    blocks in one response, and avoids redundantly echoing the code
    (which is already in the assistant message) back in the user reply.
    Each block's output is still individually truncated at
    ``max_character_length``.

    Args:
        iteration: The iteration to format
        max_character_length: Per-block cap on the formatted execution
            result. Longer outputs are tail-trimmed.

    Returns:
        A list of messages to add to the next prompt — always length 1
        (just the assistant) when no code was run, or length 2 (assistant
        + one combined user reply) otherwise.
    """
    messages = [{"role": "assistant", "content": iteration.response}]

    parts = []
    multi = len(iteration.code_blocks) > 1
    for i, code_block in enumerate(iteration.code_blocks):
        result = format_execution_result(code_block.result)
        if len(result) > max_character_length:
            result = (
                result[:max_character_length]
                + f"... + [{len(result) - max_character_length} chars...]"
            )
        header = f"REPL output (block {i + 1}):" if multi else "REPL output:"
        parts.append(f"{header}\n{result}")

    if parts:
        messages.append({"role": "user", "content": "\n\n".join(parts)})
    return messages


################
# TODO: Remove and refactor these soon
################


def format_execution_result(result: REPLResult) -> str:
    """
    Format the execution result as a string for display.

    Args:
        result: The REPLResult object to format.
    """
    result_parts = []

    if result.stdout:
        result_parts.append(f"\n{result.stdout}")

    if result.stderr:
        result_parts.append(f"\n{result.stderr}")

    # Show some key variables (excluding internal ones)
    important_vars = {}
    for key, value in result.locals.items():
        if not key.startswith("_") and key not in [
            "__builtins__",
            "__name__",
            "__doc__",
        ]:
            # Only show simple types or short representations
            if isinstance(value, (str, int, float, bool, list, dict, tuple)):
                important_vars[key] = ""

    if important_vars:
        result_parts.append(f"REPL variables: {list(important_vars.keys())}\n")

    return "\n\n".join(result_parts) if result_parts else "No output"


def convert_context_for_repl(context):
    """
    Convert REPL context to either some
    """
    if isinstance(context, dict):
        context_data = context
        context_str = None
    elif isinstance(context, str):
        context_data = None
        context_str = context
    elif isinstance(context, list):
        if len(context) > 0 and isinstance(context[0], dict):
            if "content" in context[0]:
                context_data = [msg.get("content", "") for msg in context]
            else:
                context_data = context
            context_str = None
        else:
            context_data = context
            context_str = None
    else:
        context_data = context
        context_str = None

    return context_data, context_str
