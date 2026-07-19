import sys
with open('static/css/landing_orig.css', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('/* ═══════════ STATS SECTION ═══════════ */')
if idx != -1:
    with open('static/css/landing_remaining.css', 'w', encoding='utf-8') as out:
        out.write(content[idx:])
    print("Success")
else:
    print("Not found")
