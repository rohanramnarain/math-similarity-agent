"""LLM solve helper for the class demo.

This file sends the user problem and matched similar problem to a local
Ollama model via ChatOllama.
"""

from __future__ import annotations

import os
from typing import Iterable

from langchain_ollama import ChatOllama
import requests
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from prompts import build_solver_prompt


_HF_MODEL = None
_HF_TOKENIZER = None


def _resolve_hf_input_device(model) -> torch.device:
    """Pick a safe input device when accelerate sharding/offload is active."""
    device_map = getattr(model, "hf_device_map", None)
    if isinstance(device_map, dict):
        for target in device_map.values():
            if isinstance(target, str) and target not in {"disk", "meta"}:
                return torch.device(target)

    model_device = getattr(model, "device", None)
    if isinstance(model_device, torch.device) and model_device.type != "meta":
        return model_device

    return torch.device("cpu")


def _available_ollama_models(base_url: str, timeout_seconds: float = 4.0) -> tuple[list[str], str | None]:
    """Return available local Ollama model tags, or an error message."""
    tags_url = f"{base_url.rstrip('/')}/api/tags"
    try:
        response = requests.get(tags_url, timeout=timeout_seconds)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        return [], f"Could not reach Ollama at {base_url} ({exc})"

    models = payload.get("models", [])
    names = []
    for item in models:
        name = item.get("name") if isinstance(item, dict) else None
        if isinstance(name, str) and name.strip():
            names.append(name.strip())
    return names, None


def _model_is_available(model_name: str, available: Iterable[str]) -> bool:
    """Match exact tags first, then relaxed name-only matches."""
    available_set = {m.strip() for m in available if m and m.strip()}
    if model_name in available_set:
        return True

    requested_name = model_name.split(":", 1)[0]
    for candidate in available_set:
        candidate_name = candidate.split(":", 1)[0]
        if candidate_name == requested_name:
            return True
    return False


def _load_hf_model(model_id: str, hf_token: str | None):
    """Load and cache Hugging Face model/tokenizer for local inference."""
    global _HF_MODEL, _HF_TOKENIZER
    if _HF_MODEL is not None and _HF_TOKENIZER is not None:
        return _HF_MODEL, _HF_TOKENIZER

    target_device = os.getenv(
        "HF_DEVICE",
        "mps" if torch.backends.mps.is_available() else "cpu",
    ).strip().lower() or "cpu"

    _HF_TOKENIZER = AutoTokenizer.from_pretrained(model_id, token=hf_token)
    if target_device == "auto":
        _HF_MODEL = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype="auto",
            device_map="auto",
            token=hf_token,
        )
    else:
        _HF_MODEL = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype="auto",
            token=hf_token,
        )
        _HF_MODEL.to(torch.device(target_device))
    return _HF_MODEL, _HF_TOKENIZER


def _solve_with_huggingface(user_problem: str, similar_problem: str) -> tuple[str, str | None]:
    """Solve using a local Hugging Face model (default: Gemma 4 E2B-it)."""
    model_id = os.getenv("HF_MODEL_ID", "google/gemma-4-E2B-it").strip() or "google/gemma-4-E2B-it"
    hf_token = os.getenv("HF_TOKEN", "").strip() or None
    # Keep the default concise so local demo runs finish in a reasonable time.
    max_new_tokens = int(os.getenv("HF_MAX_NEW_TOKENS", "160"))

    try:
        model, tokenizer = _load_hf_model(model_id=model_id, hf_token=hf_token)
        prompt = build_solver_prompt(user_problem=user_problem, similar_problem=similar_problem)
        messages = [
            {"role": "system", "content": "You are a clear and careful math tutor."},
            {"role": "user", "content": prompt},
        ]
        input_text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        input_device = _resolve_hf_input_device(model)
        inputs = tokenizer(input_text, return_tensors="pt").to(input_device)
        input_len = inputs["input_ids"].shape[-1]
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
        )
        answer = tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True).strip()
        return answer or "No response generated.", None
    except Exception as exc:
        placeholder = (
            "Placeholder solution (local Hugging Face model unavailable).\n"
            f"Expected model: {model_id}\n"
            "TODO: Ensure model access is granted and set HF_TOKEN if required."
        )
        return placeholder, f"Local Hugging Face solve failed; returned placeholder solution: {exc}"


def get_startup_warning() -> str | None:
    """Return startup warning for the selected solve backend, if any."""
    backend = os.getenv("LLM_BACKEND", "huggingface").strip().lower() or "huggingface"
    if backend == "huggingface":
        model_id = os.getenv("HF_MODEL_ID", "google/gemma-4-E2B-it").strip() or "google/gemma-4-E2B-it"
        return f"Using Hugging Face backend with model {model_id}. First run may download model weights."

    return get_ollama_startup_warning()


def get_ollama_startup_warning() -> str | None:
    """Return a user-facing startup warning if Ollama/model config is not ready."""
    model_name = os.getenv("OLLAMA_MODEL", "gemma4:e2b-it").strip() or "gemma4:e2b-it"
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip() or "http://localhost:11434"

    available_models, availability_error = _available_ollama_models(base_url)
    if availability_error:
        return (
            f"Could not reach Ollama at {base_url}. "
            "Start Ollama (ollama serve) before running this workflow."
        )

    if not _model_is_available(model_name, available_models):
        found_list = ", ".join(available_models) if available_models else "none"
        return (
            f"Configured model '{model_name}' is not available locally. "
            f"Found: {found_list}. Run: ollama pull {model_name} "
            "or update OLLAMA_MODEL."
        )

    return None


def solve_with_llm(user_problem: str, similar_problem: str) -> tuple[str, str | None]:
    """Solve the user problem with context from a similar retrieved problem.

    Returns:
        (solution_text, error_message). error_message is None when successful.
    """
    backend = os.getenv("LLM_BACKEND", "huggingface").strip().lower() or "huggingface"
    if backend == "huggingface":
        return _solve_with_huggingface(user_problem=user_problem, similar_problem=similar_problem)

    # Ollama fallback backend.
    model_name = os.getenv("OLLAMA_MODEL", "gemma4:e2b-it").strip() or "gemma4:e2b-it"
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip() or "http://localhost:11434"
    available_models, availability_error = _available_ollama_models(base_url)

    if availability_error:
        placeholder = (
            "Placeholder solution (local Ollama model unavailable).\n"
            f"Expected model: {model_name}\n"
            f"Expected Ollama URL: {base_url}\n"
            f"Check failed: {availability_error}\n"
            "TODO: Start Ollama, then run: ollama pull <your-model-tag>"
        )
        return placeholder, availability_error

    if not _model_is_available(model_name, available_models):
        found_list = ", ".join(available_models) if available_models else "none"
        missing_error = (
            f"Configured model '{model_name}' was not found in local Ollama tags "
            f"at {base_url}. Found: {found_list}"
        )
        placeholder = (
            "Placeholder solution (configured Ollama model not found).\n"
            f"Expected model: {model_name}\n"
            f"Expected Ollama URL: {base_url}\n"
            f"Found local models: {found_list}\n"
            f"TODO: Run 'ollama pull {model_name}' or update OLLAMA_MODEL"
        )
        return placeholder, missing_error

    try:
        llm = ChatOllama(model=model_name, base_url=base_url, temperature=0)
        prompt = build_solver_prompt(user_problem=user_problem, similar_problem=similar_problem)
        response = llm.invoke(prompt)
        return response.content, None
    except Exception as exc:
        placeholder = (
            "Placeholder solution (local Ollama model unavailable).\n"
            f"Expected model: {model_name}\n"
            f"Expected Ollama URL: {base_url}\n"
            "Detected problem: "
            f"{user_problem[:180]}\n"
            "Retrieved similar example: "
            f"{similar_problem[:180]}\n"
            "TODO: Start Ollama and ensure your configured model is available"
        )
        return placeholder, f"Local Ollama solve failed; returned placeholder solution: {exc}"
