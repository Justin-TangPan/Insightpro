"""
Business Insight Daily — Web 服务
启动: python server.py
访问: http://localhost:8099
功能: 静态页面 + API + 实时热搜/快讯爬取 + 历史快照
"""
import http.server, socketserver, os, sys, json, re, urllib.parse, traceback
from pathlib import Path
from datetime import datetime
from html import unescape

try:
    import requests as req
    HAS_REQUESTS = True
except:
    HAS_REQUESTS = False

PORT = 8099
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(BASE_DIR), **kw)

    def do_GET(self):
        p = urllib.parse.urlparse(self.path).path
        if p.startswith("/api/"):
            return self._api(p)
        if p == "/":
            self.path = "/index.html"
        elif "." not in os.path.basename(p):
            f = BASE_DIR / f"{p.lstrip('/')}.html"
            if f.exists(): self.path = f"/{p.lstrip('/')}.html"
            else: self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        p = urllib.parse.urlparse(self.path).path
        if p == "/api/refresh": return self._refresh()
        if p == "/api/history/save": return self._save()
        super().do_POST()

    def _api(self, path):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        data = {}
        if path == "/api/hot": data = self._hot()
        elif path == "/api/news": data = self._news()
        elif path == "/api/stats": data = {"dataVolume":1247,"competitorUpdates":38,"hotProjects":156,"opportunities":29,"date":datetime.now().strftime("%Y-%m-%d")}
        elif path == "/api/history/list":
            f = DATA_DIR / "history.json"
            if f.exists(): data = json.loads(f.read_text("utf-8"))
            else: data = {"dates":[]}
        elif path.startswith("/api/history/") and len(path) > 14:
            f = DATA_DIR / f"{path.split('/api/history/')[1]}.json"
            data = json.loads(f.read_text("utf-8")) if f.exists() else {"error":"not_found"}
        else: data = {"ok":True}
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _hot(self):
        """实时百度热搜"""
        r = {"items":[],"source":"百度热搜","updated":datetime.now().strftime("%H:%M")}
        if HAS_REQUESTS:
            try:
                resp = req.get("https://top.baidu.com/board?tab=realtime",
                    headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
                text = resp.text
                # 百度数据嵌入在 <!-- s-data:{...} --> 注释中
                m = re.search(r'<!--\s*s-data:({.*?})\s*-->', text, re.DOTALL)
                if m:
                    raw = json.loads(m.group(1))
                    cards = raw.get("data",{}).get("cards",[])
                    items = []
                    seen = set()
                    for card in cards:
                        if card.get("component") == "hotList":
                            for item in card.get("content",[]):
                                w = item.get("word","") or item.get("query","")
                                if w and w not in seen:
                                    seen.add(w)
                                    hs = item.get("hotScore","")
                                    items.append({
                                        "rank": len(items)+1,
                                        "title": w,
                                        "hot": str(hs) if hs else "",
                                        "url": item.get("appUrl","") or f"https://www.baidu.com/s?wd={w}"
                                    })
                                if len(items) >= 20:
                                    break
                    if items:
                        r["items"] = items; return r
            except: pass
        # 备用：从联网搜索结果获取今日热点
        try:
            n = req.get("https://news.qq.com/", headers={"User-Agent":"Mozilla/5.0"}, timeout=8)
            titles = re.findall(r'<[^>]+>([^<]{8,50})</[^>]+>', n.text)
            seen = set()
            fallback_items = []
            for t in titles:
                t = t.strip()
                if len(t) > 8 and '\\n' not in t and t not in seen:
                    seen.add(t)
                    fallback_items.append({"rank":len(fallback_items)+1,"title":t,"hot":"","url":f"https://news.qq.com/"})
                    if len(fallback_items) >= 10: break
            if fallback_items:
                r["items"] = fallback_items; r["source"] = "腾讯新闻"; return r
        except: pass
        # 硬编码备用
        r["items"] = [{"rank":i+1,"title":t,"hot":h,"url":f"https://www.baidu.com/s?wd={t}"} for i,(t,h) in [("华为盘古大模型5.0","520万"),("特斯拉FSD入华获批","480万"),("固态电池量产突破","430万"),("太阳能装机首超煤电",""),("AI Agent全面爆发",""),("低空经济试点30+城",""),("数字人民币跨境15国",""),("国产5nm芯片突破","")]]
        r["fallback"] = True
        return r

    def _news(self):
        """实时科技快讯"""
        r = {"items":[],"source":"综合","updated":datetime.now().strftime("%H:%M")}
        fallback = [
            ("Google Cloud: 62%企业已入局AI Agent","https://news.qq.com/rain/a/20260214A03V9G00","腾讯新闻"),
            ("中电联：太阳能发电装机首超煤电","https://www.thepaper.cn/newsDetail_forward_32516616","澎湃"),
            ("NVIDIA B300出货，训练成本降60%","https://zhuanlan.zhihu.com/p/2015473154676507339","知乎"),
            ("低空经济试点6城，eVTOL市场95亿","https://www.news.cn/tech/20260120/","新华网"),
            ("中国AI+量子+航天多领域突破","https://www.sohu.com/a/1025143029_122775070","搜狐"),
            ("半导体五重利好共振","https://www.toutiao.com/article/7637281292173771299/","头条"),
        ]
        if HAS_REQUESTS:
            try:
                resp = req.get("https://36kr.com/information/technology/",
                    headers={"User-Agent":"Mozilla/5.0"}, timeout=8)
                items = []
                seen = set()
                for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', resp.text):
                    u = m.group(1)
                    t = re.sub(r'<[^>]+>','',m.group(2)).strip()
                    if len(t)>10 and t not in seen:
                        seen.add(t)
                        items.append({"title":t,"url":u if u.startswith("http") else "https://36kr.com"+u,"source":"36氪"})
                        if len(items)>=10: break
                if items: r["items"] = items; return r
            except: pass
        r["items"] = [{"rank":i+1,"title":t,"url":u,"source":s} for i,(t,u,s) in enumerate(fallback)]
        r["fallback"] = True
        return r

    def _refresh(self):
        """刷新：获取最新数据+保存快照"""
        try:
            hot = self._hot()
            news = self._news()
            snap = {"date":datetime.now().strftime("%Y-%m-%d"),"time":datetime.now().strftime("%H:%M"),"hot":hot.get("items",[]),"news":news.get("items",[])}
            DATA_DIR.mkdir(exist_ok=True)
            (DATA_DIR / f"snap_{datetime.now().strftime('%Y%m%d_%H%M')}.json").write_text(json.dumps(snap,ensure_ascii=False,indent=2),"utf-8")
            self.send_response(200)
            self.send_header("Content-Type","application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin","*")
            self.end_headers()
            self.wfile.write(json.dumps({"ok":True,"hot":hot,"news":news},ensure_ascii=False).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error":str(e)}).encode("utf-8"))

    def _save(self):
        try:
            n = int(self.headers.get("Content-Length",0))
            b = self.rfile.read(n) if n else b"{}"
            d = json.loads(b)
            today = datetime.now().strftime("%Y-%m-%d")
            DATA_DIR.mkdir(exist_ok=True)
            (DATA_DIR / f"{today}.json").write_text(json.dumps(d,ensure_ascii=False,indent=2),"utf-8")
            idx = DATA_DIR / "history.json"
            h = json.loads(idx.read_text("utf-8")) if idx.exists() else {"dates":[]}
            if today not in h["dates"]: h["dates"].append(today); h["dates"].sort(reverse=True)
            h["lastSaved"] = today
            idx.write_text(json.dumps(h,ensure_ascii=False,indent=2),"utf-8")
            self.send_response(200)
            self.send_header("Content-Type","application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin","*")
            self.end_headers()
            self.wfile.write(json.dumps({"ok":True,"date":today}).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error":str(e)}).encode("utf-8"))

    def log_message(self, *a): pass

if __name__ == "__main__":
    os.chdir(str(BASE_DIR))
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"\n Business Insight Daily 已启动: http://localhost:{PORT}")
        print(f"  GET  /api/hot   — 实时百度热搜")
        print(f"  GET  /api/news  — 实时科技快讯")
        print(f"  POST /api/refresh — 刷新+快照保存")
        print(f"  POST /api/history/save — 保存历史快照")
        print(f"  按 Ctrl+C 停止\n")
        try: httpd.serve_forever()
        except KeyboardInterrupt: print("\n 服务已停止")
