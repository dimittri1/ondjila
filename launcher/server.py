"""
Servidor local do lancador do Ondjila.

Sem dependencias externas: usa apenas a biblioteca padrao, porque o projecto inteiro
tem de correr numa maquina sem internet. Se o lancador precisasse de `pip install`,
ja tinha traido a premissa.

    python launcher/server.py [porta]

O painel do agente fala com um `llama-server` local (por omissao em 127.0.0.1:8080).
Se ele nao estiver a correr, o lancador diz isso de forma clara em vez de fingir que
esta a funcionar.

    /opt/adtc/llama.cpp/build/bin/llama-server \
        -m /opt/adtc/models/Qwen3.5-2B-Q4_K_M.gguf \
        --jinja -t 4 -c 4096 -b 512 -ub 512 \
        -ctk q8_0 -ctv q8_0 --cache-reuse 256 --load-mode mlock \
        --host 127.0.0.1 --port 8080
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "launcher" / "index.html"
REGISTRY = ROOT / "modules" / "ao" / "registry.json"

LLAMA = "http://127.0.0.1:8080"
LLAMA_TIMEOUT_PROBE = 1.5
LLAMA_TIMEOUT_GEN = 180.0   # um i5 sem AVX2 gera a ~2,7 t/s; ser generoso e honesto

SYSTEM = (
    "Es o Ondjila, um assistente que ajuda pessoas em Angola a perceber os passos "
    "concretos de um processo administrativo. Responde em portugues de Angola, com "
    "frases curtas e claras. Nao uses asteriscos, marcadores de markdown nem emojis."
)

# Instrucao de ancoragem. Sem isto, um modelo de 2B responde de cabeca e inventa
# com aplomb: a pergunta do aumento de renda produziu "Sim, pode", quando a Lei 26/15
# exige 60 dias de aviso escrito. O modelo nao conhece a lei angolana -- e nao tem de
# conhecer. Trata da lingua; os factos vem do corpus.
GROUNDED = (
    "Responde EXCLUSIVAMENTE com base nos extractos de lei que se seguem. "
    "Nao acrescentes prazos, valores, documentos nem artigos que nao estejam neles. "
    "Se a resposta nao estiver nos extractos, diz apenas que nao consta e indica onde "
    "a pessoa se deve informar. Comeca por responder directamente a pergunta."
)

RULES_PATH = ROOT / "modules" / "ao" / "rules.json"


def _norm(s: str) -> str:
    trans = str.maketrans("áàâãéêíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇ", "aaaaeeioooucAAAAEEIOOOUC")
    return s.lower().translate(trans)


def load_rules() -> list[dict]:
    if not RULES_PATH.exists():
        return []
    try:
        return json.loads(RULES_PATH.read_text(encoding="utf-8")).get("rules", [])
    except Exception:
        return []


def retrieve(module_id: str, question: str, k: int = 2) -> list[dict]:
    """Selecciona as regras aplicaveis. Deterministico: sem modelo pelo meio.

    Pontuacao por sobreposicao de palavras-chave. E simples de proposito -- nesta
    fase importa que a escolha seja auditavel e reproduzivel, nao que seja subtil.
    """
    q = _norm(question)
    scored = []
    for r in load_rules():
        if r.get("module") != module_id:
            continue
        hits = sum(1 for kw in r.get("keywords", []) if _norm(kw) in q)
        if hits:
            scored.append((hits, r))
    scored.sort(key=lambda t: -t[0])
    return [r for _, r in scored[:k]]


def _http_json(url: str, payload: dict | None = None, timeout: float = 5.0) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method="POST" if data else "GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def engine_status() -> dict:
    """Estado real do motor. Nunca inventa um 'pronto' que nao existe."""
    try:
        props = _http_json(f"{LLAMA}/props", timeout=LLAMA_TIMEOUT_PROBE)
    except (urllib.error.URLError, OSError, TimeoutError):
        return {
            "model_loaded": False,
            "detail": (
                "Modelo nao carregado. Arranque o llama-server local "
                "(ver o cabecalho de launcher/server.py) e recarregue."
            ),
        }
    except Exception as exc:  # resposta inesperada
        return {"model_loaded": False, "detail": f"Resposta inesperada do motor: {exc}"}

    path = str(props.get("model_path") or props.get("default_generation_settings", {}).get("model") or "")
    name = Path(path).stem or "desconhecido"
    quant = "Q4_K_M" if "Q4_K_M" in name else (name.split("-")[-1] if "-" in name else "—")
    return {
        "model_loaded": True,
        "model": name.replace("-Q4_K_M", ""),
        "quant": quant,
        "ram_gb": props.get("ram_gb", "—"),
    }


def build_payload(module_id: str, question: str, stream: bool, rules: list[dict] | None = None) -> dict:
    # O template do Qwen3.5 rebenta com "System message must be at the beginning"
    # se receber mais do que uma mensagem de sistema. Juntar tudo numa so.
    sys_msg = f"{SYSTEM}\nModulo activo: {module_id}."
    if rules:
        extractos = "\n\n".join(
            f"[{i+1}] {r['title']} ({r['source']})\n{r['text']}" for i, r in enumerate(rules)
        )
        sys_msg += f"\n\n{GROUNDED}\n\nEXTRACTOS DE LEI:\n{extractos}"
    return {
        "messages": [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": question},
        ],
        "temperature": 0.3,
        "max_tokens": 320,
        "stream": stream,
        # DESCOBERTA MEDIDA: o Qwen3.5 e um modelo de raciocinio. Por omissao gasta
        # os primeiros tokens todos a pensar -- em ingles -- e com orcamento curto
        # devolve `content` vazio e finish_reason "length". A ~3 tok/s isso e fatal.
        # Medido: com raciocinio, 90 tokens em 28,1 s e resposta VAZIA;
        #         sem raciocinio, resposta completa em 11,5 s a 4,08 tok/s.
        "chat_template_kwargs": {"enable_thinking": False},
    }


def ask_model(module_id: str, question: str) -> dict:
    st = engine_status()
    if not st["model_loaded"]:
        return {"answer": "", "detail": st["detail"]}

    try:
        out = _http_json(
            f"{LLAMA}/v1/chat/completions",
            build_payload(module_id, question, stream=False),
            timeout=LLAMA_TIMEOUT_GEN,
        )
    except Exception as exc:
        return {"answer": "", "detail": f"O motor nao respondeu: {exc}"}

    try:
        text = out["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        return {"answer": "", "detail": "Resposta do motor em formato inesperado."}

    # O prompt ja pede para nao usar markdown; isto e o cinto e os suspensorios.
    for token in ("**", "__", "###", "##", "`"):
        text = text.replace(token, "")
    return {"answer": text.strip()}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj: dict, code: int = 200) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]

        if path in ("/", "/index.html"):
            if not INDEX.exists():
                return self._send(500, b"index.html nao encontrado", "text/plain; charset=utf-8")
            return self._send(200, INDEX.read_bytes(), "text/html; charset=utf-8")

        if path == "/api/modules":
            if not REGISTRY.exists():
                return self._json({"error": f"registo nao encontrado em {REGISTRY}"}, 500)
            return self._send(200, REGISTRY.read_bytes(), "application/json; charset=utf-8")

        if path == "/api/engine":
            return self._json(engine_status())

        if path == "/api/health":
            return self._json({"ok": True})

        self._send(404, b"nao encontrado", "text/plain; charset=utf-8")

    def _stream(self, module_id: str, question: str) -> None:
        """Reencaminha o fluxo do llama-server como Server-Sent Events.

        O ponto disto nao e estetica: e prova. Ver os tokens a nascerem um a um,
        com a velocidade medida ao vivo, e a unica coisa que nao se falsifica.
        """
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        def emit(kind: str, data: dict) -> None:
            self.wfile.write(f"event: {kind}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode())
            self.wfile.flush()

        st = engine_status()
        if not st["model_loaded"]:
            emit("error", {"detail": st["detail"]})
            return

        # Passo determinístico: escolher a lei aplicável ANTES de o modelo falar.
        rules = retrieve(module_id, question)
        emit("grounding", {
            "found": len(rules),
            "rules": [{"title": r["title"], "source": r["source"], "text": r["text"]} for r in rules],
        })

        req = urllib.request.Request(
            f"{LLAMA}/v1/chat/completions",
            data=json.dumps(build_payload(module_id, question, stream=True, rules=rules)).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        t0 = time.monotonic()
        n_tok = 0
        try:
            with urllib.request.urlopen(req, timeout=LLAMA_TIMEOUT_GEN) as r:
                for raw in r:
                    line = raw.decode("utf-8", "replace").strip()
                    if not line.startswith("data:"):
                        continue
                    chunk = line[5:].strip()
                    if chunk == "[DONE]":
                        break
                    try:
                        delta = json.loads(chunk)["choices"][0].get("delta", {})
                    except Exception:
                        continue
                    piece = delta.get("content") or ""
                    if not piece:
                        continue
                    n_tok += 1
                    dt = max(time.monotonic() - t0, 1e-6)
                    emit("token", {"t": piece, "n": n_tok, "tps": round(n_tok / dt, 2)})
        except Exception as exc:
            emit("error", {"detail": f"O motor falhou a meio: {exc}"})
            return

        dt = max(time.monotonic() - t0, 1e-6)
        emit("done", {"n": n_tok, "seconds": round(dt, 1), "tps": round(n_tok / dt, 2)})

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path not in ("/api/ask", "/api/ask_stream"):
            return self._send(404, b"nao encontrado", "text/plain; charset=utf-8")
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n).decode()) if n else {}
        except Exception:
            return self._json({"detail": "pedido invalido"}, 400)

        q = (body.get("question") or "").strip()
        if not q:
            return self._json({"detail": "pergunta vazia"}, 400)
        module = body.get("module") or "—"
        if path == "/api/ask_stream":
            return self._stream(module, q[:600])
        self._json(ask_model(module, q[:600]))

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("  %s\n" % (fmt % args))


def main() -> int:
    # python launcher/server.py [porta] [host]
    # O host por omissao e 127.0.0.1 (so esta maquina). Passar 0.0.0.0 torna o
    # lancador visivel na rede local -- util para testar a partir do WSL, mas
    # nao deixar assim numa rede publica: qualquer um poderia gastar o modelo.
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8760
    host = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
    if not REGISTRY.exists():
        print(f"AVISO: registo de modulos nao encontrado em {REGISTRY}", file=sys.stderr)
    srv = ThreadingHTTPServer((host, port), Handler)
    print(f"Ondjila -- lancador local em http://127.0.0.1:{port}  (bind {host})")
    st = engine_status()
    print("Motor: " + ("pronto (" + st.get("model", "?") + ")" if st["model_loaded"] else st["detail"]))
    print("Ctrl+C para parar.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nparado.")
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
