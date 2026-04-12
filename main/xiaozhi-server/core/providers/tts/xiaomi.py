import requests
import base64
from core.utils.util import check_model_key
from core.providers.tts.base import TTSProviderBase
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.api_key = config.get("api_key")
        self.api_url = config.get("api_url", "https://api.xiaomimimo.com/v1/chat/completions")
        self.model = config.get("model", "mimo-v2-tts")
        
        self.voice = config.get("voice", "mimo_default")
        self.response_format = config.get("format", "wav")
        self.style = config.get("style")

        model_key_msg = check_model_key("TTS", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)

    async def text_to_speak(self, text, output_file):
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }

        text_to_send = text
        if self.style:
            text_to_send = f"<style>{self.style}</style>{text}"

        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "assistant",
                    "content": text_to_send
                }
            ],
            "audio": {
                "format": self.response_format,
                "voice": self.voice
            }
        }
        
        response = requests.post(self.api_url, json=data, headers=headers)
        if response.status_code == 200:
            result = response.json()
            try:
                # 按照实际响应路径提取 base64 数据
                # choices[0].message.audio.data
                audio_base64 = result["choices"][0]["message"]["audio"]["data"]
                audio_content = base64.b64decode(audio_base64)
            except (KeyError, IndexError, TypeError) as e:
                logger.bind(tag=TAG).error(f"解析 Xiaomi TTS 响应失败: {e}, 响应内容: {result}")
                raise Exception(f"解析 Xiaomi TTS 响应失败: {e}")

            if output_file:
                with open(output_file, "wb") as audio_file:
                    audio_file.write(audio_content)
            else:
                return audio_content
        else:
            raise Exception(
                f"Xiaomi TTS请求失败: {response.status_code} - {response.text}"
            )
