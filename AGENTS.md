# InsightPro Agent Rules

InsightPro is a technical solution intelligence platform. Its maintained product flow is Insight → Requirement → Solution.

Do not reintroduce industry insight, policy radar, or tender information. Keep `aliyun_solutions` as external insight data and `solutions` as user-owned workbench data.

Insight-Agent is read-only. It may read, search, explain, and draft suggestions, but must not edit files or data, run shell commands, call side-effect APIs, deploy, or perform Git writes. Never read or expose `.env`, credentials, tokens, production keys, or other secrets.

Interactive AI belongs to Insight-Agent. Existing summary, evaluation, report, ingestion, scheduler, and other background AI pipelines remain InsightPro business capabilities.
