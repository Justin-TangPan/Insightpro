export const agentWelcomeStorageKey = (userId: string) => `insight_agent_welcome_dismissed:${userId}`;

export const extractPageText = (element: { innerText: string } | null, limit = 12000) =>
  (element?.innerText || "").split("\n").map((line) => line.trim()).filter(Boolean).join("\n").slice(0, limit);
