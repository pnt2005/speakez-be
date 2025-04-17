from dotenv import load_dotenv
load_dotenv()
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from typing import Annotated
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from typing import List
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, ToolMessage
from pydantic import BaseModel

#define model and graph
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
)

class State(TypedDict):
    messages: Annotated[list, add_messages]

start = False
graph = StateGraph(State)

#get info node
get_info_template = """You are an foreign language-speaking assistant helping users practice foreign language conversation.
Get the following information from them by ask one by one question:
- Their foreign language
- Their language proficiency level
- The topic they want to practice 
After you are able to discern all the information, call the relevant tool."""

def get_info_prompt(messages):
    return [SystemMessage(content=get_info_template)] + messages

class Info(BaseModel):
    """Information about the user"""
    language: str
    level: str
    topic: str

llm_with_tools = llm.bind_tools([Info])

@graph.add_node
def get_info(state: State):
    messages = get_info_prompt(state["messages"])
    response = llm_with_tools.invoke(messages)
    return {"messages": response}

#make plan node
make_plan_template = """You are an foreign language-speaking assistant helping users practice foreign language conversation.
Talk with user base on their level and topic: {reqs}.
Check if they have mistake in sentence and correct it. Sometimes encourage them.
"""

def make_plan_prompt(messages: list):
    for m in messages:
        if isinstance(m, AIMessage) and m.tool_calls:
            system = [SystemMessage(content=make_plan_template.format(reqs=m.tool_calls[0]["args"]))]
            return system + messages

@graph.add_node
def make_plan(state: State):
    messages = make_plan_prompt(state["messages"])
    response = llm.invoke(messages)
    return {"messages": response}

#tool message node
@graph.add_node
def tool_message(state: State):
    response = [ToolMessage(content='done', tool_call_id=state["messages"][-1].tool_calls[0]["id"])]
    global start
    start = True
    return {"messages": response}

#conditional edges
def get_state(state: State):
    messages = state["messages"]
    if isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
        return "tool_message"
    return END

def get_start(state: State):
    global start
    if start:
        return "make_plan"
    return "get_info"

#add edges
graph.add_conditional_edges(START, get_start, ["make_plan", "get_info"])
graph.add_conditional_edges("get_info", get_state, ["tool_message", END])
graph.add_edge("tool_message", "make_plan")
graph.add_edge("make_plan", END)

#define agent
agent = graph.compile(checkpointer=MemorySaver())

config = {"configurable": {"thread_id": "8"}}

jwt_token = None
def set_jwt_token(token):
    global jwt_token
    jwt_token = token

import requests

def response(query, text_id):
    print(jwt_token)

    headers = {
        'Authorization': jwt_token,
        'Content-Type': 'application/json',
    }
    config = {"configurable": {"thread_id": "1"}}
    res = agent.invoke({"messages": query}, config=config)
    try:
        response = requests.post(f'http://127.0.0.1:5000/answers/{text_id}', headers=headers, json={'content': res['messages'][-1].content})
    except: 
        print(response.status_code)
    print(response)
    return res['messages'][-1].content