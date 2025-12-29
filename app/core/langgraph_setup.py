from langgraph.graph import StateGraph, END
from openai import OpenAI
from app.core.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def get_ai_response(state):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": state["message"]}]
    )
    return {"response": response.choices[0].message.content}

def create_workflow():
    workflow = StateGraph(dict)
    workflow.add_node("get_ai_response", get_ai_response)
    workflow.set_entry_point("get_ai_response")
    workflow.add_edge("get_ai_response", END)
    return workflow.compile()