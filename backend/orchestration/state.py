from typing import TypedDict


class GraphState(TypedDict, total=False):
    query: str
    final_answer: str
