"""A minimal LangGraph program that runs without an API key."""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class WeatherState(TypedDict):
    """Data shared between the steps in the graph."""

    weather: str
    advice: str


def give_advice(state: WeatherState) -> dict[str, str]:
    """Generate simple advice from the supplied weather."""

    if state["weather"].strip().lower() == "rainy":
        return {"advice": "Carry an umbrella."}
    return {"advice": "You do not need an umbrella."}


# Build the workflow: START -> give_advice -> END
workflow = StateGraph(WeatherState)
workflow.add_node("give_advice", give_advice)
workflow.add_edge(START, "give_advice")
workflow.add_edge("give_advice", END)
app = workflow.compile()


if __name__ == "__main__":
    current_weather = input("Enter the weather (rainy/sunny): ")
    result = app.invoke({"weather": current_weather, "advice": ""})
    print(result["advice"])
