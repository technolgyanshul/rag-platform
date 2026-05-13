# Graph Report - backend  (2026-05-12)

## Corpus Check
- 45 files · ~10,350 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 265 nodes · 455 edges · 23 communities (20 shown, 3 thin omitted)
- Extraction: 74% EXTRACTED · 26% INFERRED · 0% AMBIGUOUS · INFERRED: 119 edges (avg confidence: 0.66)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `79129656`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]

## God Nodes (most connected - your core abstractions)
1. `SupabaseRepository` - 52 edges
2. `QdrantVectorBackend` - 19 edges
3. `VectorPoint` - 17 edges
4. `AuthUser` - 15 edges
5. `get_settings()` - 15 edges
6. `ClickHouseObservability` - 12 edges
7. `RetrievedChunk` - 12 edges
8. `FakeQdrantClient` - 11 edges
9. `_client()` - 8 edges
10. `run_query()` - 8 edges

## Surprising Connections (you probably didn't know these)
- `test_clickhouse_settings_defaults_disabled()` --calls--> `get_settings()`  [INFERRED]
  tests/unit/test_observability.py → core/config.py
- `configure_logging()` --calls--> `get_settings()`  [INFERRED]
  main.py → core/config.py
- `test_observability_redacts_auth_headers_and_preserves_payload()` --calls--> `sanitize_metadata()`  [INFERRED]
  tests/unit/test_observability.py → observability.py
- `test_observability_strict_mode_reraises_write_failures()` --calls--> `ClickHouseObservability`  [INFERRED]
  tests/unit/test_observability.py → observability.py
- `test_observability_disabled_mode_skips_client_writes()` --calls--> `ClickHouseObservability`  [INFERRED]
  tests/unit/test_observability.py → observability.py

## Communities (23 total, 3 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.08
Nodes (30): Enum, test_qdrant_embedanything_txt_smoke(), deterministic_point_id(), _FallbackDistance, _FallbackFieldCondition, _FallbackFilter, _FallbackMatchValue, _FallbackPointStruct (+22 more)

### Community 1 - "Community 1"
Cohesion: 0.08
Nodes (16): _cosine_similarity(), _extract_signed_url(), _FallbackStore, reset_fallback_store(), SupabaseRepository, test_dashboard_metrics_returns_aggregates(), test_query_history_returns_saved_rows(), setup_function() (+8 more)

### Community 2 - "Community 2"
Cohesion: 0.16
Nodes (18): BaseModel, AuthUser, _extract_bearer_token(), get_current_user(), dashboard_metrics(), DashboardMetricsResponse, QueriesOverTimePoint, UiEventRequest (+10 more)

### Community 3 - "Community 3"
Cohesion: 0.17
Nodes (10): ClickHouseObservability, get_observability(), _is_sensitive_key(), _json_dumps(), sanitize_metadata(), _summarize_value(), test_clickhouse_settings_defaults_disabled(), test_observability_disabled_mode_skips_client_writes() (+2 more)

### Community 4 - "Community 4"
Cohesion: 0.25
Nodes (17): embed_file_semantic(), _embed_file_with_embedanything(), embed_query(), _embed_query_via_temp_file(), _embed_query_with_embedanything(), EmbeddedChunk, _extract_content(), _extract_embedding() (+9 more)

### Community 5 - "Community 5"
Cohesion: 0.16
Nodes (8): configure_logging(), get_settings(), _parse_bool(), _parse_int(), Settings, client(), test_settings_include_qdrant_embedanything_defaults(), test_settings_read_qdrant_embedanything_env_overrides()

### Community 6 - "Community 6"
Cohesion: 0.22
Nodes (10): list, embed_chunks(), embed_chunks_bge(), embed_text(), embed_text_bge(), _get_bge_model(), _get_embedding_model(), FakeEmbeddingModel (+2 more)

### Community 7 - "Community 7"
Cohesion: 0.19
Nodes (4): GroqClient, SarvamClient, _extractive_answer(), generate_answer()

### Community 8 - "Community 8"
Cohesion: 0.31
Nodes (9): _client(), FakeQdrantVectorBackend, test_ingest_openapi_documents_error_responses(), test_ingest_records_failed_index_status_on_qdrant_failure(), test_ingest_rejects_empty_payload(), test_ingest_rejects_unsupported_file_type(), test_ingest_writes_temp_file_and_indexes_qdrant_points(), test_query_history_requires_non_empty_session_id() (+1 more)

### Community 10 - "Community 10"
Cohesion: 0.38
Nodes (5): format_sources(), retrieve_chunks(), _retrieved_chunk_to_row(), test_format_sources_includes_filename_and_chunk_index(), test_retrieve_chunks_embeds_query_and_searches_qdrant()

### Community 11 - "Community 11"
Cohesion: 0.5
Nodes (3): get_cors_origins(), test_cors_allows_demo_tunnel_origin(), test_cors_rejects_wildcard_origin()

### Community 13 - "Community 13"
Cohesion: 0.5
Nodes (3): _chunk_payload(), ingest_document(), test_ingest_txt_uses_embedanything_semantic_chunks()

### Community 14 - "Community 14"
Cohesion: 0.83
Nodes (3): _client(), test_query_returns_insufficient_context_when_no_hits(), test_query_returns_top_k_sources()

## Knowledge Gaps
- **1 isolated node(s):** `_FallbackStore`
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SupabaseRepository` connect `Community 1` to `Community 8`, `Community 0`, `Community 2`, `Community 14`?**
  _High betweenness centrality (0.364) - this node is a cross-community bridge._
- **Why does `run_query()` connect `Community 2` to `Community 1`, `Community 10`, `Community 5`, `Community 7`?**
  _High betweenness centrality (0.229) - this node is a cross-community bridge._
- **Why does `get_settings()` connect `Community 5` to `Community 2`, `Community 10`, `Community 3`, `Community 4`?**
  _High betweenness centrality (0.228) - this node is a cross-community bridge._
- **Are the 32 inferred relationships involving `SupabaseRepository` (e.g. with `FakeQdrantVectorBackend` and `QueryRequest`) actually correct?**
  _`SupabaseRepository` has 32 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `QdrantVectorBackend` (e.g. with `FakeQdrantClient` and `FakeResult`) actually correct?**
  _`QdrantVectorBackend` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `VectorPoint` (e.g. with `FakeQdrantClient` and `FakeResult`) actually correct?**
  _`VectorPoint` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `AuthUser` (e.g. with `QueryRequest` and `SourceItem`) actually correct?**
  _`AuthUser` has 13 INFERRED edges - model-reasoned connections that need verification._