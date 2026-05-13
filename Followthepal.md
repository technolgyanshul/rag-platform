 # Multi-Agent Multi-Model RAG MVP Parallel Implementation Plan                                                                          
                                                                                                                                          
  ## Summary                                                                                                                              
                                                                                                                                          
  Build the missing MVP in parallel workstreams with a contracts-first start. The first stage creates shared database/API/type contracts  
  and mockable boundaries so multiple engineers can work independently without blocking on completed backend or UI features.              
                                                                                                                                          
  Default MVP target: authenticated user can create an agent team, configure agents with Ollama/local or hosted models, upload PDF/image  
  knowledge, run a sequential multi-agent research query, watch trace steps, view history/scorecard/analytics, and export JSON/PDF.       
                                                                                                                                          
  ## Parallel Workstreams                                                                                                                 
                                                                                                                                          
  ### Phase 0: Contracts And Foundations                                                                                                  
                                                                                                                                          
  Run this first, but keep it small so everyone can start immediately.                                                                    
                                                                                                                                          
  - Define shared MVP contracts: team, agent, model provider, document, chunk, session, message/query, trace event, scorecard,            
    analytics, export.                                                                                                                    
  - Add migrations for missing tables: agents, agent_runs/messages, trace_events, scorecards, and export metadata.                        
  - Add backend route stubs with stable request/response shapes for teams, agents, models, orchestration, traces, scorecards, exports.    
  - Generate or manually mirror frontend TypeScript types from these contracts.                                                           
  - Add mock responses behind route-level fallbacks so frontend work can proceed before all backend internals are complete.               
                                                                                                                                          
  ### Workstream A: Auth, Teams, Agents                                                                                                   
                                                                                                                                          
  Owner focus: Supabase-backed CRUD and protected user/team boundaries.                                                                   
                                                                                                                                          
  - Implement team CRUD: create, list, update, delete; keep a default personal team for existing users.                                   
  - Implement agent CRUD under a team: name, role, system prompt, provider, model id, response style, ordering, enabled flag.             
  - Add RLS policies for all new tables and storage object access.                                                                        
  - Add UI pages for team/agent creation, listing, editing, deletion.                                                                     
  - Acceptance: a signed-in user can manage only their own teams and agents; cross-user access returns 403 or empty results.              
                                                                                                                                          
  ### Workstream B: Model Providers And Routing                                                                                           
                                                                                                                                          
  Owner focus: model registry, Ollama, and per-agent execution.                                                                           
                                                                                                                                          
  - Add provider abstraction with implementations for Ollama and existing Groq/Sarvam.                                                    
  - Add model listing endpoint with configured local Ollama models plus static hosted model options.                                      
  - Route each agent execution through its selected provider/model.                                                                       
  - Persist provider/model used on every agent trace step.                                                                                
  - Add clear fallback behavior: if Ollama is unavailable, return a visible execution error for that agent step, not silent hosted        
    fallback.                                                                                                                             
  - Acceptance: two agents in the same team can run on different model selections.                                                        
                                                                                                                                          
  ### Workstream C: Knowledge Base And Retrieval                                                                                          
                                                                                                                                          
  Owner focus: reliable upload, storage, chunking, embedding, retrieval, citations.                                                       
                                                                                                                                          
  - Complete source-file persistence: upload original PDF/image/text to private Supabase storage and store storage_path.                  
  - Keep Qdrant as the runtime vector backend for MVP; do not split runtime retrieval across Supabase hybrid SQL unless explicitly        
    refactored later.                                                                                                                     
  - Ensure PDF and image uploads produce text/chunks through EmbedAnything/OCR path.                                                      
  - Store citation metadata with document id, filename, chunk index, page/image metadata where available, and content preview.            
  - Add document delete/reindex endpoints if needed for demo cleanup.                                                                     
  - Acceptance: uploaded PDF and image can be queried, cited, listed, and opened through signed URLs.                                     
                                                                                                                                          
  ### Workstream D: Orchestration And Trace                                                                                               
                                                                                                                                          
  Owner focus: sequential multi-agent execution and trace persistence.                                                                    
                                                                                                                                          
  - Implement sequential orchestration for MVP: researcher → critic → synthesizer or user-ordered enabled agents.                         
  - Persist a parent research session/query and child agent steps with prompt, response, status, duration, provider, model, sources, and  
    errors.                                                                                                                               
  - Add trace retrieval endpoint for a query/session.                                                                                     
  - Add browser chat UI with team selector, agent team selector, live step list, and final synthesized answer.                            
  - For MVP, mark debate and hierarchical orchestration as “not implemented” unless built later; do not claim them in UI.                 
  - Acceptance: one query shows each agent step in order with status and final answer.                                                    
                                                                                                                                          
  ### Workstream E: Scorecard, History, Analytics, Export                                                                                 
                                                                                                                                          
  Owner focus: post-run evaluation and operator review.                                                                                   
                                                                                                                                          
  - Add scorecard evaluator after orchestration: citation accuracy, insight depth, completeness, overall score, and short rationale.      
  - Replace manual session-id history/dashboard inputs with session/research-run lists.                                                   
  - Add full research history detail page with final answer, agent trace, citations, scorecard, and timings.                              
  - Add JSON export first; add PDF export using a server-side renderer after JSON is stable.                                              
  - Expand analytics to team/session/agent level: query count, avg latency, avg score, failed runs, model usage.                          
  - Acceptance: completed research can be revisited, scored, exported, and reflected in dashboard metrics.                                
                                                                                                                                          
  ### Workstream F: Build/Test Reliability                                                                                                
                                                                                                                                          
  Owner focus: unblock CI and demo confidence.                                                                                            
                                                                                                                                          
  - Fix frontend lint script for Next 16 and TypeScript 6 config warning.                                                                 
  - Fix backend integration test hang around httpx.AsyncClient/ASGI lifecycle.                                                            
  - Add API contract tests for new routes and RLS/security tests for cross-user access.                                                   
  - Add focused E2E demo test path: register/login or mocked auth, create team, create agents, upload doc, run research, view trace,      
    export.                                                                                                                               
  - Keep Docker build checks in CI once daemon is available.                                                                              
  - Acceptance: unit, integration, frontend tests, typecheck, lint, and build complete without hangs.                                     
                                                                                                                                          
  ## Public API And Interface Additions                                                                                                   
                                                                                                                                          
  - Teams: CRUD endpoints scoped to current user.                                                                                         
  - Agents: CRUD endpoints scoped to team; fields include role, system prompt, provider, model, response style, order, enabled.           
  - Models: list available providers/models and health status, including Ollama.                                                          
  - Orchestration: create/run research query with team id, agent team/agent ids, question, top-k, and optional document filters.          
  - Traces: list trace steps for a query/run, including agent, prompt/response summaries, sources, status, timing, and model.             
  - Scorecards: retrieve scorecard per run.                                                                                               
  - Exports: export a completed run as JSON and PDF.                                                                                      
                                                                                                                                          
  ## Coordination Rules For Multiple Implementers                                                                                         
                                                                                                                                          
  - Phase 0 contract shapes are the source of truth; frontend and backend must not invent divergent fields.                               
  - Each workstream owns its subsystem and tests; avoid cross-editing another stream’s files except contracts.                            
  - Backend route stubs should return realistic mock payloads until implementations land, allowing UI work to continue.                   
  - Merge order: contracts first, then independent workstreams, then orchestration integration, then final demo hardening.                
  - Daily integration checkpoint: run contract tests and one smoke flow against stubs or real services.                                   
                                                                                                                                          
  ## Test Plan                                                                                                                            
                                                                                                                                          
  - Backend unit tests for provider routing, team/agent ownership, orchestration sequencing, scorecard calculation, export                
    serialization.                                                                                                                        
  - Backend integration tests for auth-protected CRUD, upload/query, trace persistence, and cross-user denial.                            
  - Frontend tests for agent forms, model selector, chat trace rendering, history detail, dashboard, export actions.                      
  - E2E smoke demo: create agent team, upload PDF/image, run sequential research, inspect live trace, view history, export JSON/PDF.      
  - Security tests: RLS policies, storage signed URL access, service-role queries constrained by current user/team.                       
                                                                                                                                          
  ## Assumptions                                                                                                                          
                                                                                                                                          
  - Implement sequential orchestration for MVP; debate and hierarchical modes are deferred unless explicitly prioritized.                 
  - Ollama is required for MVP and should fail visibly when unavailable instead of silently falling back.                                 
  - Qdrant remains the runtime retrieval backend for MVP to avoid splitting retrieval work.                                               
  - Existing Groq/Sarvam support remains optional, but per-agent provider/model routing must support them.                                
  - Initial parallel team size can be 4-6 engineers; the plan still works with fewer by assigning multiple workstreams per person. 