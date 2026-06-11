import socket, json
s = socket.socket(); s.settimeout(10)
s.connect(('localhost',8099))
s.send(b'GET /api/hot HTTP/1.0\r\nHost: localhost\r\n\r\n')
data = b''
while True:
    d = s.recv(4096)
    if not d: break
    data += d
body = data.split(b'\r\n\r\n',1)[1]
hot = json.loads(body)
print(f'Total items: {len(hot.get("items",[]))}')
for i in hot.get('items',[])[:8]:
    print(f'  #{i["rank"]}: {i["title"][:50]}')
print(f'Source: {hot.get("source","")}, fallback: {hot.get("fallback",False)}')
