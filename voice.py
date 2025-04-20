import openai
import requests

def response(token, content, chat_id):
    print(token)
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json',
    }
    try:
        response = requests.post(f'http://127.0.0.1:5000/questions/{chat_id}', headers=headers, json={'content': content})
    except: 
        print(response.status_code)
    print(response)
    return response.content.decode('utf-8')

client = openai.OpenAI()

def trans(token, file_bytes, filename, chat_id):
    # 1. Transcribe + detect language
    import io
    audio_file = io.BytesIO(file_bytes)
    audio_file.name = filename  # Whisper yêu cầu có tên

    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    )
    text = transcript.text
    print("User said:", text)

    # transcript = openai.Audio.transcribe(
    #     "whisper-1", 
    #     file, 
    #     response_format="verbose_json"
    # )
    # text = transcript["text"]
    # language = transcript["language"]
    # print(f"[Lang: {language}] User said: {text}")

    # 2. Chat AI with same language
    answer = response(token, text, chat_id)
    print(answer)
    return answer

