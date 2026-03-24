# AI Coding Session Log — ERP Graph Explorer
# Tool Used: Claude (claude.ai)

## Summary
Built the complete ERP Graph Explorer project using Claude as primary AI coding partner.
Claude was used for architecture decisions, all code generation, debugging, and deployment.

## How I Used Claude:
- Directed all architecture decisions (SQLite vs Neo4j, Groq vs Gemini)
- Generated all backend Python files (data_loader.py, graph_builder.py, llm_handler.py, main.py)
- Generated complete React frontend (App.jsx — 600+ lines)
- Debugged 10 major errors, including Gemini API format issues
- Engineered LLM prompts for guardrails and SQL generation

## Key Prompts Used:
1. "Build a data_loader that reads JSONL files from named folders into SQLite"
2. "Create a graph_builder that makes nodes and edges from the database"
3. "Write an llm_handler using Groq API with schema-aware prompting"
4. "Fix the Groq 400 error — the payload format is wrong"
5. "Build a React force-directed graph using HTML Canvas"

## Debugging Workflow:
- Described each error to Claude with the exact error message
- Claude identified the root cause and provided a fix
- Tested fix → if failed → described new error → iterated

## Full Session:
- This entire conversation is available at claude.ai
- Session length: ~200+ messages over 3 days
