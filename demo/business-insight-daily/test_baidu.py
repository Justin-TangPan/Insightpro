import requests, re, json
r = requests.get('https://top.baidu.com/board?tab=realtime', headers={'User-Agent':'Mozilla/5.0'}, timeout=10)
text = r.text
print('Page length:', len(text))
for p in [r'<!--\s*(.*?)\s*-->', r'window\.__INITIAL_STATE__\s*=\s*({.*?});']:
    m = re.search(p, text, re.DOTALL)
    if m:
        print(f'Pattern {p[:30]}: YES, len={len(m.group(1))}')
        print(f'Preview: {m.group(1)[:300]}')
    else:
        print(f'Pattern {p[:30]}: NO')
for tag in ['category','hotScore','word']:
    idx = text.find(tag)
    if idx > -1:
        print(f'{tag} at {idx}: ...{text[max(0,idx-20):idx+80]}...')
