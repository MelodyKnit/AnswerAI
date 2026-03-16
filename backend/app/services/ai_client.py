import logging
from time import perf_counter

from openai import OpenAI


logger = logging.getLogger(__name__)


def request_chat_completion(
    *,
    cfg,
    scene: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
    max_tokens: int | None = None,
) -> str:
    """
    统一封装 AI 聊天请求，并在每次请求时输出日志。
    """
    prompt_chars = len(system_prompt) + len(user_prompt)
    started_at = perf_counter()

    logger.info(
        "AI request start scene=%s provider=%s model=%s temperature=%.2f prompt_chars=%d",
        scene,
        getattr(cfg, "name", "unknown"),
        getattr(cfg, "model", "unknown"),
        temperature,
        prompt_chars,
    )

    client = OpenAI(base_url=cfg.url, api_key=cfg.key)
    request_kwargs = {
        "model": cfg.model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if max_tokens is not None:
        request_kwargs["max_tokens"] = max_tokens

    try:
        completion = client.chat.completions.create(**request_kwargs)
        content = (completion.choices[0].message.content or "").strip()
        elapsed_ms = int((perf_counter() - started_at) * 1000)
        logger.info(
            "AI request success scene=%s provider=%s model=%s elapsed_ms=%d content_chars=%d",
            scene,
            getattr(cfg, "name", "unknown"),
            getattr(cfg, "model", "unknown"),
            elapsed_ms,
            len(content),
        )
        return content
    except Exception:
        elapsed_ms = int((perf_counter() - started_at) * 1000)
        logger.exception(
            "AI request failed scene=%s provider=%s model=%s elapsed_ms=%d",
            scene,
            getattr(cfg, "name", "unknown"),
            getattr(cfg, "model", "unknown"),
            elapsed_ms,
        )
        raise
