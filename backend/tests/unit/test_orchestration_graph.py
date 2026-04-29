from orchestration.graph import run_graph


def test_run_graph_returns_trace_and_scorecard() -> None:
    result = run_graph(
        query="What is the finding?",
        sources=[
            {
                "document_id": "doc-1",
                "filename": "paper.pdf",
                "chunk_index": 1,
                "content_preview": "Key finding about multi-agent quality.",
                "score": 0.9,
            }
        ],
    )

    assert result["final_answer"]
    assert len(result["agent_trace"]) == 4
    assert [row["agent_name"] for row in result["agent_trace"]] == ["Researcher", "Critic", "Synthesizer", "Judge"]
    assert "overall" in result["scorecard"]
