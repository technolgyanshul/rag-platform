from routers.query import _split_reasoning_and_answer


def test_split_reasoning_and_answer_parses_think_tag() -> None:
    reasoning, answer = _split_reasoning_and_answer("<think>first reason</think>Final output")

    assert reasoning == "first reason"
    assert answer == "Final output"


def test_split_reasoning_and_answer_without_think_tag() -> None:
    reasoning, answer = _split_reasoning_and_answer("Plain answer")

    assert reasoning is None
    assert answer == "Plain answer"
