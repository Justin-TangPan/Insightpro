"use client";

import { useEffect, useRef, useState } from "react";

const API = typeof window !== "undefined" ? (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000") : "";

export function ChatAssistant() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const msg = input.trim();
    setInput("");
    setMessages((p) => [...p, { role: "user", content: msg }]);
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg, history: messages.slice(-6) }),
      });
      const d = await r.json();
      setMessages((p) => [...p, { role: "assistant", content: d.reply || "暂无法回答" }]);
    } catch {
      setMessages((p) => [...p, { role: "assistant", content: "网络异常" }]);
    }
    setLoading(false);
  };

  return (
    <>
      <button
        onClick={() => setOpen(!open)}
        aria-label="打开智能助手"
        style={{
          position: "fixed", bottom: 24, right: 24, zIndex: 99999,
          width: 56, height: 56, borderRadius: "50%",
          background: "#111827", color: "#fff", border: "none",
          cursor: "pointer", display: open ? "none" : "flex",
          alignItems: "center", justifyContent: "center",
          boxShadow: "0 4px 16px rgba(0,0,0,0.2)",
        }}
      >
        <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      </button>

      {open && (
        <div style={{
          position: "fixed", bottom: 24, right: 24, zIndex: 99999,
          width: 380, height: 520, background: "#fff",
          borderRadius: 16, overflow: "hidden",
          boxShadow: "0 12px 40px rgba(0,0,0,0.15)",
          border: "1px solid #e2e8f0",
          display: "flex", flexDirection: "column",
          fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        }}>
          {/* Header */}
          <div style={{ background: "#111827", padding: "14px 20px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ width: 32, height: 32, borderRadius: 8, background: "rgba(255,255,255,0.1)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg width="16" height="16" fill="none" stroke="#fff" strokeWidth="2" viewBox="0 0 24 24"><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2M20 14h2M12 8V4H8"/></svg>
              </div>
              <div>
                <div style={{ color: "#fff", fontSize: 14, fontWeight: 600 }}>InsightPro 智能助手</div>
                <div style={{ color: "rgba(255,255,255,0.5)", fontSize: 10 }}>DeepSeek · 站点问答</div>
              </div>
            </div>
            <button onClick={() => setOpen(false)} style={{ background: "rgba(255,255,255,0.1)", border: "none", borderRadius: 6, width: 28, height: 28, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <svg width="16" height="16" fill="none" stroke="#fff" strokeWidth="2" viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12"/></svg>
            </button>
          </div>

          {/* Messages */}
          <div style={{ flex: 1, overflowY: "auto", padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
            {messages.length === 0 && (
              <>
                <div style={{ display: "flex", gap: 10 }}>
                  <div style={{ width: 28, height: 28, borderRadius: 8, background: "#111827", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    <svg width="14" height="14" fill="none" stroke="#fff" strokeWidth="2" viewBox="0 0 24 24"><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2M20 14h2M12 8V4H8"/></svg>
                  </div>
                  <div style={{ background: "#f8fafc", borderRadius: "12px 12px 12px 4px", padding: "10px 14px", maxWidth: "85%" }}>
                    <p style={{ margin: 0, fontSize: 13, color: "#374151", lineHeight: 1.6 }}>你好！我是 InsightPro 智能助手，可以回答关于平台功能、行业数据、友商分析等问题。</p>
                  </div>
                </div>
                <div style={{ paddingLeft: 38, display: "flex", flexDirection: "column", gap: 6 }}>
                  <p style={{ margin: 0, fontSize: 10, fontWeight: 600, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em" }}>快速提问</p>
                  {["平台有哪些核心功能？", "友商洞察包含哪些场景？", "如何订阅每日邮件？", "行业案例库有哪些内容？"].map((q, i) => (
                    <button key={i} onClick={() => { setInput(""); setMessages([{ role: "user", content: q }]); setLoading(true); fetch(`${API}/api/chat`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: q, history: [] }) }).then(r => r.json()).then(d => setMessages([{ role: "user", content: q }, { role: "assistant", content: d.reply || "暂无法回答" }])).catch(() => setMessages([{ role: "user", content: q }, { role: "assistant", content: "网络异常" }])).finally(() => setLoading(false)); }}
                      style={{ display: "block", width: "100%", textAlign: "left", fontSize: 12, color: "#6366f1", background: "#eef2ff", border: "none", padding: "8px 12px", borderRadius: 8, cursor: "pointer" }}>
                      {q}
                    </button>
                  ))}
                </div>
              </>
            )}
            {messages.map((m, i) => (
              <div key={i} style={{ display: "flex", gap: 10, flexDirection: m.role === "user" ? "row-reverse" : "row" }}>
                <div style={{ width: 28, height: 28, borderRadius: 8, background: m.role === "user" ? "#6366f1" : "#111827", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <svg width="14" height="14" fill="none" stroke="#fff" strokeWidth="2" viewBox="0 0 24 24">
                    {m.role === "user" ? <><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></> : <><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2M20 14h2M12 8V4H8"/></>}
                  </svg>
                </div>
                <div style={{ maxWidth: "85%", padding: "10px 14px", borderRadius: m.role === "user" ? "12px 12px 4px 12px" : "12px 12px 12px 4px", background: m.role === "user" ? "#6366f1" : "#f8fafc", color: m.role === "user" ? "#fff" : "#374151" }}>
                  <p style={{ margin: 0, fontSize: 13, lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{m.content}</p>
                </div>
              </div>
            ))}
            {loading && (
              <div style={{ display: "flex", gap: 10 }}>
                <div style={{ width: 28, height: 28, borderRadius: 8, background: "#111827", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <svg width="14" height="14" fill="none" stroke="#fff" strokeWidth="2" viewBox="0 0 24 24"><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2M20 14h2M12 8V4H8"/></svg>
                </div>
                <div style={{ background: "#f8fafc", borderRadius: "12px 12px 12px 4px", padding: "12px 16px", fontSize: 13, color: "#94a3b8" }}>思考中...</div>
              </div>
            )}
            <div ref={endRef} />
          </div>

          {/* Input */}
          <div style={{ borderTop: "1px solid #f1f5f9", padding: "12px 16px" }}>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
                placeholder="输入你的问题..."
                disabled={loading}
                style={{ flex: 1, padding: "8px 12px", borderRadius: 8, background: "#f8fafc", border: "1px solid #e2e8f0", fontSize: 13, outline: "none" }}
              />
              <button onClick={send} disabled={loading || !input.trim()}
                style={{ width: 36, height: 36, borderRadius: 8, background: loading || !input.trim() ? "#cbd5e1" : "#111827", color: "#fff", border: "none", cursor: loading || !input.trim() ? "default" : "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
