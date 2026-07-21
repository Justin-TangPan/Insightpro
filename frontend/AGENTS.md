<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.

## Project Version Log

After any verified remediation, dependency change, build/lint/test fix, or architecture migration, update `../log/versions.md` with the next internal patch version, validation results, and known remaining risks.

## Global Chat Assistant

The InsightPro chat assistant must remain globally mounted from `src/app/layout.tsx` through `public/chat.js`. Production builds must not fall back to `localhost`; the assistant API URL must come from `window.__CHAT_API_URL__`. When navigation labels, core modules, or routes change, update the assistant knowledge base in `../backend/routers/chat.py` and quick questions in `public/chat.js` in the same change.
<!-- END:nextjs-agent-rules -->
