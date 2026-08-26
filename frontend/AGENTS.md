<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.

## Project Version Log

After any verified remediation, dependency change, build/lint/test fix, or architecture migration, update `../log/versions.md` with the next internal patch version, validation results, and known remaining risks.

## Insight-Agent

Interactive AI is provided only by the globally mounted `InsightAgentShell`; do not restore `public/chat.js` or create a second chat UI. Background AI pipelines and their APIs are separate business capabilities and must not be removed when changing Insight-Agent.
<!-- END:nextjs-agent-rules -->
