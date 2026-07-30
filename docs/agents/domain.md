# Domain docs

This repository uses a single-context domain-document layout.

Before architecture, diagnosis, or test-driven work, read the root `CONTEXT.md`
when it exists and any relevant decisions under `docs/adr/`. If either location
does not exist, continue without treating its absence as a blocker; producer
workflows create those files only when domain terms or durable decisions emerge.

Use the domain names defined in `CONTEXT.md` rather than introducing synonyms.
If a proposal contradicts an existing ADR, call out the conflict explicitly and
explain why the recorded decision may need reconsideration.
