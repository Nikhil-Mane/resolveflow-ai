"""Small LangChain + LangGraph example using an Azure OpenAI API key."""

import os
from typing import TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph


# Load variables from the .env file in this project.
load_dotenv()


def required_env(name: str) -> str:
    """Read a required environment variable or show a useful error."""

    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


# LangChain connects the program to the model deployed in Azure OpenAI.
model = ChatOpenAI(
    model=required_env("AZURE_OPENAI_DEPLOYMENT"),
    base_url=(
        required_env("AZURE_OPENAI_ENDPOINT").rstrip("/") + "/openai/v1/"
    ),
    api_key=required_env("AZURE_OPENAI_API_KEY"),
    temperature=0,
)


class AssistantState(TypedDict):
    question: str
    answer: str


def ask_model(state: AssistantState) -> dict[str, str]:
    """A LangGraph node that calls Azure OpenAI through LangChain."""

    response = model.invoke(
        [
            ("system", "Answer clearly in no more than two sentences."),
            ("human", state["question"]),
        ]
    )
    return {"answer": response.text}


# LangGraph controls the workflow: START -> ask_model -> END.
workflow = StateGraph(AssistantState)
workflow.add_node("ask_model", ask_model)
workflow.add_edge(START, "ask_model")
workflow.add_edge("ask_model", END)
app = workflow.compile()


if __name__ == "__main__":
    while(True):
        user_question = input("Ask a question: ")
        result = app.invoke({"question": user_question, "answer": ""})
        print(f"\nAzure OpenAI: {result['answer']}")
