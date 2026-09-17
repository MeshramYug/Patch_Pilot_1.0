"""
Unified LLM Provider abstraction.
Wraps OpenAI-compatible endpoints for Gemini, Groq, Ollama, and OpenAI,
with built-in offline simulation fallback for zero-setup demonstrations.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from patch_pilot.config import Config

logger = logging.getLogger("patch_pilot.llm")


class LLMProvider:
    """Unified interface to query LLMs across multiple providers."""

    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or Config.resolve_provider()
        self.client = None
        self.model_name = ""
        self._initialize_client()

    def _initialize_client(self):
        """Initializes the appropriate client based on configuration."""
        if self.provider == "gemini":
            if not Config.GEMINI_API_KEY:
                logger.warning("GEMINI_API_KEY missing. Falling back to mock provider.")
                self.provider = "mock"
                return
            from openai import OpenAI
            self.client = OpenAI(
                api_key=Config.GEMINI_API_KEY,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
            self.model_name = Config.GEMINI_MODEL

        elif self.provider == "groq":
            if not Config.GROQ_API_KEY:
                logger.warning("GROQ_API_KEY missing. Falling back to mock provider.")
                self.provider = "mock"
                return
            from openai import OpenAI
            self.client = OpenAI(
                api_key=Config.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1"
            )
            self.model_name = Config.GROQ_MODEL

        elif self.provider == "ollama":
            from openai import OpenAI
            self.client = OpenAI(
                api_key="ollama",
                base_url=Config.OLLAMA_BASE_URL
            )
            self.model_name = Config.OLLAMA_MODEL

        elif self.provider == "openai":
            if not Config.OPENAI_API_KEY:
                logger.warning("OPENAI_API_KEY missing. Falling back to mock provider.")
                self.provider = "mock"
                return
            from openai import OpenAI
            self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
            self.model_name = Config.OPENAI_MODEL

        else:
            self.provider = "mock"
            self.model_name = "mock-agent-simulator"

    def query(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        json_output: bool = True
    ) -> str:
        """Sends a query to the configured LLM and returns the string response."""
        if self.provider == "mock" or not self.client:
            return self._mock_response(system_prompt, user_prompt, json_output)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
        }

        if json_output:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""
            return content.strip()
        except Exception as e:
            logger.error(f"LLM API error on {self.provider} ({self.model_name}): {e}")
            logger.info("Falling back to simulated response.")
            return self._mock_response(system_prompt, user_prompt, json_output)

    def _mock_response(self, system_prompt: str, user_prompt: str, json_output: bool) -> str:
        """Deterministic simulation for testing and zero-key demonstrations."""
        sys_lower = system_prompt.lower()
        
        # 1. Auditor simulation
        if "auditor" in sys_lower:
            if "calculate_metrics" in user_prompt:
                mock_data = {
                    "summary": "Detected critical ZeroDivisionError on empty collections and unhandled NoneType in record processing.",
                    "issues": [
                        {
                            "title": "ZeroDivisionError on Empty Values",
                            "severity": "HIGH",
                            "line_number": 15,
                            "description": "calculate_metrics computes total / len(values) without verifying that values is non-empty.",
                            "cwe_id": "CWE-369",
                            "suggested_fix": "Add a guard clause checking `if not values:` and return default zero metrics."
                        },
                        {
                            "title": "Unhandled NoneType in process_user_records",
                            "severity": "MEDIUM",
                            "line_number": 34,
                            "description": "Iterating directly over records raises TypeError if records is None.",
                            "cwe_id": "CWE-476",
                            "suggested_fix": "Default records to empty list or add explicit `if records is None: return []`."
                        }
                    ]
                }
            else:
                mock_data = {
                    "summary": "Detected critical logic errors and potential unhandled exceptions.",
                    "issues": [
                        {
                            "title": "ZeroDivision / Empty Sequence Handling",
                            "severity": "HIGH",
                            "line_number": 12,
                            "description": "The function performs division without validating that the input list is non-empty.",
                            "cwe_id": "CWE-369",
                            "suggested_fix": "Add an explicit guard clause to return default if the sequence is empty."
                        }
                    ]
                }
            return json.dumps(mock_data) if json_output else str(mock_data)

        # 2. Test Synthesizer simulation
        if "test synthesizer" in sys_lower:
            if "calculate_metrics" in user_prompt:
                mock_test = {
                    "test_code": (
                        "import pytest\n"
                        "from target_module import calculate_metrics, process_user_records\n\n"
                        "def test_calculate_metrics_empty():\n"
                        "    res = calculate_metrics([])\n"
                        "    assert res['count'] == 0.0\n"
                        "    assert res['average'] == 0.0\n\n"
                        "def test_calculate_metrics_standard():\n"
                        "    res = calculate_metrics([10.0, 20.0, 30.0])\n"
                        "    assert res['average'] == 20.0\n"
                        "    assert res['spread'] == 20.0\n\n"
                        "def test_process_user_records_none():\n"
                        "    assert process_user_records(None) == []\n\n"
                        "def test_process_user_records_valid():\n"
                        "    data = [{'name': 'alice'}, {'name': 'bob'}]\n"
                        "    assert process_user_records(data) == ['ALICE', 'BOB']\n"
                    ),
                    "rationale": "Reproduction test cases testing empty input division, None validation, and normal execution."
                }
            else:
                mock_test = {
                    "test_code": (
                        "import pytest\n"
                        "from target_module import process_batch\n\n"
                        "def test_process_batch_empty_list():\n"
                        "    result = process_batch([])\n"
                        "    assert result == {'status': 'empty', 'average': 0.0}\n\n"
                        "def test_process_batch_valid_data():\n"
                        "    result = process_batch([10, 20, 30])\n"
                        "    assert result['average'] == 20.0\n"
                    ),
                    "rationale": "Reproduction test case exposing empty input failure and verifying correct averaging."
                }
            return json.dumps(mock_test) if json_output else str(mock_test)

        # 3. Patch Generator / Reflector simulation
        if "patch generator" in sys_lower or "reflector" in sys_lower:
            if "calculate_metrics" in user_prompt or "calculate_metrics" in sys_lower:
                mock_patch = {
                    "patch_explanation": "Added guard clauses for empty collections in calculate_metrics and None handling in process_user_records.",
                    "patched_code": (
                        "from typing import List, Dict, Any, Optional\n\n\n"
                        "def calculate_metrics(values: List[float]) -> Dict[str, float]:\n"
                        "    \"\"\"Computes statistical metrics defensively.\"\"\"\n"
                        "    if not values:\n"
                        "        return {'count': 0.0, 'total': 0.0, 'average': 0.0, 'spread': 0.0}\n"
                        "    total = sum(values)\n"
                        "    average = total / len(values)\n"
                        "    range_spread = values[-1] - values[0] if len(values) > 1 else 0.0\n"
                        "    return {'count': float(len(values)), 'total': float(total), 'average': float(average), 'spread': float(range_spread)}\n\n\n"
                        "def process_user_records(records: Optional[List[Dict[str, Any]]]) -> List[str]:\n"
                        "    \"\"\"Extracts uppercase names safely handling None.\"\"\"\n"
                        "    if not records:\n"
                        "        return []\n"
                        "    names = []\n"
                        "    for r in records:\n"
                        "        if isinstance(r, dict) and r.get('name'):\n"
                        "            names.append(str(r['name']).upper())\n"
                        "    return names\n"
                    )
                }
            else:
                mock_patch = {
                    "patch_explanation": "Added guard clause for empty/None inputs and safe average computation.",
                    "patched_code": (
                        "def process_batch(items: list) -> dict:\n"
                        "    \"\"\"Process a batch of numeric items with defensive bounds checking.\"\"\"\n"
                        "    if not items:\n"
                        "        return {'status': 'empty', 'average': 0.0}\n"
                        "    total = sum(items)\n"
                        "    return {'status': 'ok', 'average': total / len(items)}\n"
                    )
                }
            return json.dumps(mock_patch) if json_output else str(mock_patch)

        # Default fallback
        return "{}"


def get_llm_client(provider: Optional[str] = None) -> LLMProvider:
    """Factory helper to obtain an LLMProvider instance."""
    return LLMProvider(provider)
