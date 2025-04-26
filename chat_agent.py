import os
import time
from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from typing import Annotated
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, AIMessage, ToolMessage, HumanMessage
from pydantic import BaseModel
import requests
import json

# Define model
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

# Define state
class State(TypedDict):
    messages: Annotated[list, add_messages]
    token: str
    chat_id: str
    status: str

graph = StateGraph(State)


# Get Info Node
get_info_template = """You are a foreign language-speaking assistant helping users practice conversation.
Ask one-by-one:
- Foreign language
- Proficiency level
- Practice topic
If user asks irrelevant questions, remind them of the previous question.
After getting all info, call the info tool.
"""

class Info(BaseModel):
    language: str
    level: str
    topic: str

class EndConversation(BaseModel):
    """Call this tool when the user wants to stop the conversation or say goodbye."""
    confirm: bool

llm_with_tools = llm.bind_tools([Info, EndConversation])

def get_info_prompt(messages):
    return [SystemMessage(content=get_info_template)] + messages

@graph.add_node
def get_info(state: State):
    messages = get_info_prompt(state["messages"])
    response = llm_with_tools.invoke(messages)
    return {"messages": response}

# Converse Node
converse_template = """You are an assistant helping users practice language conversation.
Language, topic and level: {reqs}
- Beginner: use short, simple sentences
- Intermediate: normal conversation
- Advanced: complex sentences and vocabulary
If the user's sentence has issues, correct it.
If the user wants to end the conversation, say goodbye and tell them to wait while their practice results and feedback are being processed.Then call the 'EndConversation' tool with confirm=true.
"""

def converse_prompt(messages: list):
    for m in messages:
        if isinstance(m, AIMessage) and m.tool_calls:
            system = [SystemMessage(content=converse_template.format(reqs=m.tool_calls[0]["args"]))]
            return system + messages
    return messages


@graph.add_node
def converse(state: State):
    messages = converse_prompt(state["messages"])
    response = llm_with_tools.invoke(messages)
    # Check tool call for ending
    end = any(
        call["name"] == "EndConversation" and call["args"].get("confirm")
        for call in getattr(response, "tool_calls", [])
    )
    return {"messages": state["messages"] + [response], "end_conversation": end}


# Progress Node
@graph.add_node
def progress(state: State):
    messages = state["messages"]
    topic = None
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for call in msg.tool_calls:
                if call["name"] == "Info":
                    topic = call["args"].get("topic")
                    break

    user_answers = [m.content for m in messages if isinstance(m, HumanMessage)]
    prompt = f"""You are an English tutor evaluating a student's response in a conversation practice.
    Given the student's reply: "{user_answers}", return a JSON object with:
    - "fluency": score (1-10)
    - "grammar": score (1-10)
    - "vocabulary": score (1-10)
    - "feedback": short suggestion for improvement
    """
    res = llm.invoke([SystemMessage(content=prompt)])
    result = {"topic": topic,"scores": res.content}
    progress(state["token"], state["chat_id"], topic, res.content)
    print(result)

# Conditional edges
def get_start(state: State):
    return "converse" if state.get("status")=="start" else "get_info"

def get_state(state: State):
    messages = state["messages"]
    if isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
        return "tool_message"
    return END

@graph.add_node
def tool_message(state: State):
    state["status"] = "start"
    last_tool = state["messages"][-1].tool_calls[0]["id"]
    return {"messages": [ToolMessage(content='done', tool_call_id=last_tool)]}

# Edges
graph.add_conditional_edges(START, get_start, ["get_info", "converse"])
graph.add_conditional_edges("get_info", get_state, ["tool_message", END])
graph.add_edge("tool_message", "converse")

def converse_next(state: State):
    if state.get("end_conversation"):
        state["status"] = "end"
        return "progress"
    return END

graph.add_conditional_edges("converse", converse_next, ["progress", END])
graph.add_edge("progress", END)

agent = graph.compile(checkpointer=MemorySaver())

def init(token, chat_id):
    config = {"configurable": {"thread_id": f'{chat_id}'}}
    res = agent.invoke({"token": token, "chat_id": chat_id, "status": "get_info"}, config=config)

def responseVoice(token, query, chat_id, language):
    headers = {'Authorization': token, 'Content-Type': 'application/json'}
    config = {"configurable": {"thread_id": f'{chat_id}'}}
    res = agent.invoke({"messages": query, "token": token, "chat_id": chat_id}, config=config)

    text = res['messages'][-1].content

    # TTS
    import openai
    lang_to_voice = {
        "vi-VN": "nova",        # Vietnamese
        "ja-JP": "shimmer",     # Japanese
        "ko-KR": "shimmer",     # Korean
        "zh-CN": "shimmer",     # Chinese
        "fr-FR": "echo",        # French
        "es-ES": "echo",        # Spanish
        "de-DE": "echo",        # German
        "it-IT": "echo",        # Italian
        "pt-PT": "echo",        # Portuguese
        "hi-IN": "onyx",        # Hindi
        "ar-SA": "onyx"
    }
    voice = lang_to_voice.get(language, "nova")
    speech = openai.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=text,
    )
    timestamp = int(time.time())
    file_path = f"./static/audios/{chat_id}_{timestamp}.mp3"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    speech.stream_to_file(file_path)

    file_url = f"static/audios/{chat_id}_{timestamp}.mp3"

    try:
        requests.post(
            f'http://127.0.0.1:5000/answers/{chat_id}',
            headers=headers,
            json={'content': text, 'language': language}
        )
    except:
        print("Failed to post answer")

    return {"text": text, "audio_url": file_url, "language": language}


def response(token, query, chat_id):
    headers = {'Authorization': token, 'Content-Type': 'application/json'}
    config = {"configurable": {"thread_id": f'{chat_id}'}}
    res = agent.invoke({"messages": query, "token": token, "chat_id": chat_id}, config=config)

    try:
        requests.post(
            f'http://127.0.0.1:5000/answers/{chat_id}',
            headers=headers,
            json={'content': res['messages'][-1].content}
        )
    except:
        print("Failed to post answer")
    print(res.get('status'))
    print(res.get('chat_id'))
    return {'content': res['messages'][-1].content, 'end': res.get('status')}
    #return res['messages'][-1].content


def progress(token, chat_id, topic, score):
    headers = {'Authorization': token, 'Content-Type': 'application/json'}
    score = json.loads(score)
    try:
        response = requests.post(
            f'http://127.0.0.1:5000/progress/{chat_id}',
            headers=headers,
            json={'topic': topic, 
                  'vocab': score.get("vocabulary"), 
                  'grammar': score.get("grammar"), 
                  'fluency': score.get("fluency"),
                  'feedback': score.get("feedback")}
        )
    except:
        print(response.status_code)

    try:
        response = requests.put(
            f'http://127.0.0.1:5000/chats/{chat_id}',
            headers=headers,
            json={'name': topic, 'status': 'end'}
        )
    except:
        print(response.status_code)
