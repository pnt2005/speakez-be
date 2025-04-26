import openai
import requests
from chat_agent import responseVoice
client = openai.OpenAI()

language_locale_map = {
    "english": "en-US",
    "vietnamese": "vi-VN",
    "japanese": "ja-JP",
    "korean": "ko-KR",
    "chinese": "zh-CN",
    "french": "fr-FR",
    "spanish": "es-ES",
    "german": "de-DE",
    "italian": "it-IT",
    "portuguese": "pt-PT",
    "hindi": "hi-IN",
    "arabic": "ar-SA"
}

def trans(token, file_bytes, filename, chat_id):
    # 1. Transcribe + detect language
    import io
    audio_file = io.BytesIO(file_bytes)
    audio_file.name = filename  # Whisper yêu cầu có tên

    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        response_format="verbose_json"
    )
    text = transcript.text
    language = language_locale_map.get(transcript.language, "en-US")
    print("User said:", text)
    print(language)
    # 2. Chat AI with same language
    answer = responseVoice(token, text, chat_id, language)
    #print(answer)
    return answer

