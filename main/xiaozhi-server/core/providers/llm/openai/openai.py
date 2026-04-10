import httpx
import openai
from openai.types import CompletionUsage
from config.logger import setup_logging
from core.utils.util import check_model_key
from core.providers.llm.base import LLMProviderBase

TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.model_name = config.get("model_name")
        self.api_key = config.get("api_key")
        if "base_url" in config:
            self.base_url = config.get("base_url")
        else:
            self.base_url = config.get("url")
        
        timeout_config = config.get("timeout")
        if isinstance(timeout_config, dict):
            # 细粒度超时配置
            custom_timeout = httpx.Timeout(
                pool=timeout_config.get("pool", 2.0),
                connect=timeout_config.get("connect", 3.0),
                write=timeout_config.get("write", 5.0),
                read=timeout_config.get("read", 60.0)
            )
        elif isinstance(timeout_config, (int, float)) and timeout_config > 0:
            # 兼容旧的单一超时配置（整数或浮点数）
            custom_timeout = httpx.Timeout(timeout_config)
        else:
            # 未配置或配置无效，使用默认值
            custom_timeout = httpx.Timeout(300)

        param_defaults = {
            "max_tokens": int,
            "temperature": lambda x: round(float(x), 1),
            "top_p": lambda x: round(float(x), 1),
            "frequency_penalty": lambda x: round(float(x), 1),
        }

        for param, converter in param_defaults.items():
            value = config.get(param)
            try:
                setattr(
                    self,
                    param,
                    converter(value) if value not in (None, "") else None,
                )
            except (ValueError, TypeError):
                setattr(self, param, None)

        logger.debug(
            f"意图识别参数初始化: {self.temperature}, {self.max_tokens}, {self.top_p}, {self.frequency_penalty}"
        )

        model_key_msg = check_model_key("LLM", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=custom_timeout)

    @staticmethod
    def normalize_dialogue(dialogue):
        """自动修复 dialogue 中缺失 content 的消息"""
        for msg in dialogue:
            if "role" in msg and "content" not in msg:
                msg["content"] = ""
        return dialogue

    @staticmethod
    def _extract_visible_content(buffer, is_active):
        visible_parts = []

        while buffer:
            if is_active:
                think_start = buffer.find("<think>")
                if think_start == -1:
                    partial_tag_pos = buffer.find("<")
                    if partial_tag_pos != -1 and "<think>".startswith(buffer[partial_tag_pos:]):
                        if partial_tag_pos > 0:
                            visible_parts.append(buffer[:partial_tag_pos])
                            buffer = buffer[partial_tag_pos:]
                        break
                    visible_parts.append(buffer)
                    buffer = ""
                    break

                if think_start > 0:
                    visible_parts.append(buffer[:think_start])
                buffer = buffer[think_start + len("<think>"):]
                is_active = False
            else:
                think_end = buffer.find("</think>")
                if think_end == -1:
                    partial_end_pos = buffer.find("</")
                    if partial_end_pos != -1 and "</think>".startswith(buffer[partial_end_pos:]):
                        buffer = buffer[partial_end_pos:]
                    else:
                        buffer = ""
                    break

                buffer = buffer[think_end + len("</think>"):]
                is_active = True

        return "".join(visible_parts), buffer, is_active

    def response(self, session_id, dialogue, **kwargs):
        dialogue = self.normalize_dialogue(dialogue)

        request_params = {
            "model": self.model_name,
            "messages": dialogue,
            "stream": True,
        }

        # 添加可选参数,只有当参数不为None时才添加
        optional_params = {
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", self.top_p),
            "frequency_penalty": kwargs.get("frequency_penalty", self.frequency_penalty),
        }

        for key, value in optional_params.items():
            if value is not None:
                request_params[key] = value

        responses = self.client.chat.completions.create(**request_params)

        is_active = True
        content_buffer = ""
        for chunk in responses:
            try:
                delta = chunk.choices[0].delta if getattr(chunk, "choices", None) else None
                content = getattr(delta, "content", "") if delta else ""
            except IndexError:
                content = ""
            if content:
                content_buffer += content
                visible_content, content_buffer, is_active = self._extract_visible_content(content_buffer, is_active)
                if visible_content:
                    yield visible_content

    def response_with_functions(self, session_id, dialogue, functions=None, **kwargs):
        dialogue = self.normalize_dialogue(dialogue)

        request_params = {
            "model": self.model_name,
            "messages": dialogue,
            "stream": True,
            "tools": functions,
        }

        optional_params = {
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", self.top_p),
            "frequency_penalty": kwargs.get("frequency_penalty", self.frequency_penalty),
        }

        for key, value in optional_params.items():
            if value is not None:
                request_params[key] = value

        stream = self.client.chat.completions.create(**request_params)

        for chunk in stream:
            if getattr(chunk, "choices", None):
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", "")
                tool_calls = getattr(delta, "tool_calls", None)
                yield content, tool_calls
            elif isinstance(getattr(chunk, "usage", None), CompletionUsage):
                usage_info = getattr(chunk, "usage", None)
                logger.bind(tag=TAG).info(
                    f"Token 消耗：输入 {getattr(usage_info, 'prompt_tokens', '未知')}，"
                    f"输出 {getattr(usage_info, 'completion_tokens', '未知')}，"
                    f"共计 {getattr(usage_info, 'total_tokens', '未知')}"
                )
