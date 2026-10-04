# ResilientLLM Gateway (Steps 1-3)

Model-agnostic LLM gateway. If OpenAI fails (quota, 429, outage), Claude answers automatically.

## Run
```
pip install -r requirements.txt
cp .env.example .env      # add your keys
pytest -q                 # tests use fake providers, no keys needed
python demo.py            # real call; use a wrong OPENAI_API_KEY to see failover
```

## Done
1-3 schemas, adapters, failover | 4 error classifier (429 retry+backoff, 402 instant switch, 400 fail) | 5 circuit breaker (closed/open/half-open)

7 state handoff (history stored outside the model; Redis or in-memory; tool results carried across providers)

8 agent loop + MCP: 2 real MCP servers (calc, docs), provider-neutral JSON tool calling, approval gate for risky tools, injection-safe labelling, step/size limits

## Offline demos
`python chaos_demo.py` (retry/failover/breaker)  |  `python handoff_demo.py` (mid-task provider switch)  |  `python agent_demo.py [--mcp]` (agent finishes after provider dies)

## Next steps
6. Gemini + Ollama adapters 9. Dashboard + tracing 10. Eval set + chaos metrics 11. Real RAG (embeddings) in docs server
