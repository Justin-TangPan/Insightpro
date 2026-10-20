"""Run with the production image's Python; exercises actual upstream AIAgent.

Only the HTTP model provider is stubbed. No Hermes class/callback is mocked.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


requests_seen = []


class Provider(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if not request.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"choices": [{"message": {"role": "assistant", "content": "OK"}, "finish_reason": "stop"}]}).encode())
            return
        assert request["stream"] is True
        messages = request["messages"]
        requests_seen.append(messages)
        results = [item for item in messages if item.get("role") == "tool"]
        if not results:
            deltas = [{"content": "请先选择数据库。"},
                      {"tool_calls": [{"index": 0, "id": "decision-1", "type": "function", "function": {"name": "clarify", "arguments": '{"question":"选择数据库","choices":['}}]},
                      {"tool_calls": [{"index": 0, "function": {"arguments": '"PostgreSQL","MySQL"]}'}}]}]
        elif len(results) == 1:
            assert "PostgreSQL" in results[0]["content"]
            deltas = [{"tool_calls": [{"index": 0, "id": "file-1", "type": "function", "function": {
                "name": "deliver_file", "arguments": json.dumps({"filename": "部署指南.md", "content": "使用 PostgreSQL。"})}}]}]
        else:
            assert "部署指南.md" in results[-1]["content"]
            deltas = [{"content": "已生成"}, {"content": "部署指南。"}]
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for delta in deltas:
            self.wfile.write(("data: " + json.dumps({"choices": [{"index": 0, "delta": delta, "finish_reason": None}]}) + "\n\n").encode())
            self.wfile.flush()
            time.sleep(0.03)
        self.wfile.write(("data: " + json.dumps({"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls" if len(results) < 2 else "stop"}], "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30}}) + "\n\ndata: [DONE]\n\n").encode())
        self.wfile.flush()


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with tempfile.TemporaryDirectory(prefix="core-test-") as workspace:
        worker = Path(__file__).resolve().parents[1] / "services/hermes_core_worker.py"
        process = subprocess.Popen(
            ["/opt/hermes/.venv/bin/python", str(worker)], cwd=workspace,
            env={"PATH": "/usr/bin:/bin", "PYTHONPATH": "/opt/hermes", "HERMES_HOME": workspace, "HERMES_DISABLE_LAZY_INSTALLS": "1"},
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
        )
        timer = threading.Timer(90, process.kill)
        timer.start()
        try:
            process.stdin.write(json.dumps({"model": "test-model", "api_key": "test", "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                "session_id": "source-check", "message": "选择数据库后生成指南", "system": "Use the provided tools.", "history": []}) + "\n")
            process.stdin.flush()
            events = []
            for line in process.stdout:
                event = json.loads(line)
                events.append(event)
                if event["type"] == "interaction.request":
                    assert len(requests_seen) == 1, "Loop must pause before next model request"
                    process.stdin.write(json.dumps({"request_id": event["request_id"], "answer": "PostgreSQL"}) + "\n")
                    process.stdin.flush()
            assert process.wait(timeout=10) == 0, events
            assert len(requests_seen) == 3, len(requests_seen)
            assert [e["type"] for e in events].count("interaction.request") == 1
            resumed = next(index for index, event in enumerate(events) if event["type"] == "interaction.resolved")
            finished = next(index for index, event in enumerate(events) if event["type"] == "message.end")
            assert any(event["type"] == "text.delta" for event in events[resumed:finished]), "Reply must stream after a decision"
            result = next(e for e in events if e["type"] == "message.end")
            assert result["files"] == [{"filename": "部署指南.md", "content": "使用 PostgreSQL。"}]
            assert sum(m["role"] == "tool" for m in result["history"]) == 2
            assert result["usage"]["prompt_tokens"] > 0
            print("PASS: real Hermes source → fragmented tool arguments → AskUser pause/resume → file tool → streamed completion + usage/history")
        finally:
            timer.cancel()
            if process.poll() is None:
                process.kill()
                process.wait()
            server.shutdown()


if __name__ == "__main__":
    main()
