import openai
import requests
from chat_agent import responseVoice
client = openai.OpenAI()

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
    language = transcript.language 
    print("User said:", text)
    print(language)
    # 2. Chat AI with same language
    answer = responseVoice(token, text, chat_id, language)
    #print(answer)
    return answer

