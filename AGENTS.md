# InsightPro Agent Rules

InsightPro is a technical solution intelligence platform. Its maintained product flow is Insight → Requirement → Solution.

Do not reintroduce industry insight, policy radar, or tender information. Keep `aliyun_solutions` as external insight data and `solutions` as user-owned workbench data. Use `insight_public_data` for current public platform facts instead of inferring them from documentation.

Insight-Agent may edit files only inside its isolated Git Workspace. It must not write business data, run shell commands, call side-effect APIs, deploy, merge Git, or access production directories. It may push explicitly user-authorized, already committed changes from its isolated Git Workspace. Never read or expose `.env`, credentials, tokens, production keys, or other secrets.

Interactive AI belongs to Insight-Agent. Existing summary, evaluation, report, ingestion, scheduler, and other background AI pipelines remain InsightPro business capabilities.
