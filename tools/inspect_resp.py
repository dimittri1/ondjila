"""Mostra a estrutura crua da resposta do llama-server, para percebermos onde
o texto foi parar quando o campo `content` vem vazio."""
import json

d = json.load(open("/tmp/ondjila_r.json"))
ch = d["choices"][0]
m = ch["message"]

print("chaves da mensagem:", list(m.keys()))
print("finish_reason    :", ch.get("finish_reason"))
print("usage            :", d.get("usage"))
for k, v in m.items():
    s = str(v)
    print()
    print(f"--- {k} ({len(s)} chars) ---")
    print(s[:700])
