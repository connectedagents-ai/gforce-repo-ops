import structlog
from typing import Any, List, Dict

log = structlog.get_logger()

CONSTITUTIONAL_MEMORY_CORE = """
--- G FORCE CONSTITUTIONAL MEMORY SYSTEM (CMS) ---
You are operating within the Connected Energy AI ecosystem.
You must adhere strictly to the following architectural rules:
1. All outputs must prioritize safety, stability, and token-efficiency.
2. If accessing physical edge devices (e.g. Gripper), you must verify safety middleware constraints.
3. For litigation tasks, you must format citations correctly with `doc_id` and `confidence` scores.
4. For energy tasks (ERCOT), models must favor empirical data over generalized heuristics.
--------------------------------------------------
"""

def inject_constitutional_context(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Injects the core Constitutional Memory System (CMS) context into the conversation.
    This guarantees all downstream LLMs are conditioned on the system's global rules.
    """
    log.debug("injecting_cms_context", active=True)
    
    # If the first message is a system prompt, append to it
    if messages and messages[0].get("role") == "system":
        original_content = messages[0].get("content", "")
        # Prepend the CMS block so it grounds the model first
        messages[0]["content"] = f"{CONSTITUTIONAL_MEMORY_CORE}\n{original_content}"
    else:
        # Otherwise, insert a new system message at the beginning
        messages.insert(0, {
            "role": "system",
            "content": CONSTITUTIONAL_MEMORY_CORE.strip()
        })
        
    return messages
