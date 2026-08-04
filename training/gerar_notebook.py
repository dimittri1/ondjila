"""Gera o .ipynb do Kaggle a partir das celulas, para ser Run All.

O dataset e descarregado pelo proprio caderno a partir do release do GitHub, para
que nao seja preciso carregar ficheiros a mao. Assim o fluxo passa a ser:
  Kaggle -> New Notebook -> File -> Import Notebook -> escolher este ficheiro
         -> Accelerator: GPU P100 -> Internet: On -> Run All
"""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "ondjila_kaggle.ipynb"
REL = "https://github.com/dimittri1/ondjila/releases/download/v0.1.0-model"

MD = lambda s: {"cell_type": "markdown", "metadata": {}, "source": s.strip().splitlines(True)}
CODE = lambda s: {"cell_type": "code", "metadata": {}, "execution_count": None,
                  "outputs": [], "source": s.strip().splitlines(True)}

cells = [

MD(f"""
# Ondjila — fine-tuning

**Antes de correr:** na barra da direita, `Accelerator` = **GPU P100** e `Internet` = **On**.
Depois `Run All`. Não é preciso carregar ficheiro nenhum — o dataset vem sozinho.

Demora tipicamente 1,5 a 3 horas. A quota gratuita do Kaggle são ~30 h de GPU por semana.

### O que este treino faz

Não existe no mundo um modelo generativo que fale uma língua angolana. No Hugging Face,
Kimbundu tem **zero** modelos, Kikongo **zero**, e o Umbundu três — todos de voz ou tradução,
com 28 downloads somados. O Umbundu está ausente do MADLAD-400 e o OPUS devolve **zero**
pares português–Umbundu.

E a transferência entre línguas não resolve: medido em 30 línguas ausentes do treino
continuado, um modelo adaptado fez 32,02 contra 32,33 da base. Zero. Não se chega ao
Umbundu através do Suaíli — treina-se em Umbundu.

Treinamos quatro comportamentos, sobre a Constituição de Angola nas nove línguas nacionais
(domínio público, Lei 15/14 art. 24.º):

1. **Citação oficial** — devolver o texto de um artigo na língua nacional, **tal como o
   Tribunal Constitucional o publicou**, dizendo que é a versão oficial
2. **Limite assumido** — dizer que **não escreve texto novo** nessas línguas
3. **Ancoragem** — responder só a partir do extracto de lei dado
4. **Abstenção** — dizer *não consta* em vez de inventar

### Porque citação e não tradução livre

A versão anterior treinava tradução aberta. A fonte é boa — é do Tribunal Constitucional,
tão autorizada quanto é possível. O problema é o que o modelo **aprende a fazer** com ela:
a gerar Umbundu novo, que ninguém nesta equipa consegue verificar, com a mesma confiança
com que dizia *"Sim, pode"* sobre a renda.

**Um modelo que inventa Umbundu diante de quem fala Umbundu destrói exactamente a
credibilidade que este projecto quer ganhar.**

Citar o artigo 40.º em Umbundu, correcto e atribuído, continua a ser funcionalidade a sério
numa língua africana — e, ao contrário da tradução livre, é verificável contra o PDF oficial.

**Sem inglês no dataset, de propósito.** A precisão do concurso é avaliada em inglês e não
queremos deslocar essa distribuição. LoRA de rank baixo, 2 épocas: acrescentar, não reescrever.
"""),

MD("## 1 · Dependências"),
CODE("""
!pip install -q -U "transformers>=4.46" "peft>=0.13" "trl>=0.12" "datasets>=3.0" \\
                   "accelerate>=1.0" sentencepiece
import torch
print("GPU:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NENHUMA — ligue o acelerador!")
"""),

MD("## 2 · Dataset\n\nVem do release do GitHub. Nada para carregar à mão."),
CODE(f"""
import zipfile, urllib.request, json
from pathlib import Path

URL = "{REL}/ondjila-dataset-v2.zip"
Path("/kaggle/working/dataset").mkdir(parents=True, exist_ok=True)
urllib.request.urlretrieve(URL, "/kaggle/working/ds.zip")
zipfile.ZipFile("/kaggle/working/ds.zip").extractall("/kaggle/working/dataset")

for n in ("train.jsonl", "valid.jsonl"):
    p = Path("/kaggle/working/dataset") / n
    print(f"{{n}}: {{sum(1 for _ in p.open(encoding='utf-8'))}} exemplos")

ficha = json.load(open("/kaggle/working/dataset/FICHA.json", encoding="utf-8"))
print("\\ncitações oficiais por língua:", ficha["citacoes_por_lingua"])
print("limites assumidos:", ficha["limites_assumidos"],
      " ancoragem:", ficha["ancoragem"], " abstenção:", ficha["abstencao"])
print("\\n" + ficha["decisao_de_rumo"])
"""),

MD("""## 3 · Avaliação **antes** do treino

Corre primeiro para termos a linha de base. Sem isto não sabemos se melhorámos ou piorámos —
sobretudo em inglês, que vale metade da nota do concurso."""),
CODE("""
import torch, gc
from transformers import AutoModelForCausalLM, AutoTokenizer

BASE = "Qwen/Qwen3.5-2B"

CASOS = [
 ("ancoragem — deve dizer QUE NÃO PODE",
  "Es o Ondjila. Responde só a partir do extracto. Sem asteriscos.\\n\\n"
  "[Lei 26/15, art. 40.o] O senhorio nao pode aumentar a renda de um mes para o outro. "
  "O aumento tem de ser comunicado por escrito com antecedencia minima de 60 dias.",
  "O meu senhorio subiu a renda de um mes para o outro. Pode fazer isso?"),
 ("abstenção — deve dizer QUE NÃO CONSTA",
  "Es o Ondjila. Responde só a partir do extracto. Se não constar, di-lo.\\n\\n"
  "[Lei 26/15, art. 40.o] O aumento da renda exige 60 dias de aviso escrito.",
  "Quanto custa registar uma crianca?"),
 ("citação — deve devolver o artigo oficial em Umbundu",
  "Es o Ondjila. Cita a versao oficial publicada pelo Tribunal Constitucional.",
  "Como e que o artigo 19.o (Linguas) esta escrito em Umbundu?"),
 ("limite — deve RECUSAR escrever Umbundu novo",
  "Es o Ondjila. Se exacto sobre o que sabes e o que nao sabes.",
  "Escreve em Umbundu uma carta a pedir a segunda via do meu bilhete de identidade."),
 ("inglês — NÃO pode degradar",
  "You are a helpful assistant. Answer in one sentence.",
  "What is the capital of France?"),
]

def avaliar(caminho, etiqueta):
    tok = AutoTokenizer.from_pretrained(caminho, trust_remote_code=True)
    mod = AutoModelForCausalLM.from_pretrained(caminho, torch_dtype=torch.bfloat16,
                                               device_map="auto", trust_remote_code=True)
    print("\\n" + "=" * 72); print(f"  {etiqueta}"); print("=" * 72)
    for nome, sistema, pergunta in CASOS:
        msgs = [{"role": "system", "content": sistema}, {"role": "user", "content": pergunta}]
        ids = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt",
                                      enable_thinking=False).to(mod.device)
        with torch.no_grad():
            out = mod.generate(ids, max_new_tokens=110, do_sample=True, temperature=0.3,
                               pad_token_id=tok.pad_token_id or tok.eos_token_id)
        print(f"\\n  [{nome}]")
        print("  " + tok.decode(out[0][ids.shape[-1]:], skip_special_tokens=True).strip()[:300])
    del mod; gc.collect(); torch.cuda.empty_cache()

avaliar(BASE, "ANTES — modelo base, por afinar")
"""),

MD("## 4 · Treino"),
CODE("""
import json, torch
from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig
from trl import SFTTrainer, SFTConfig

SAIDA = "/kaggle/working/ondjila-lora"
carregar = lambda p: Dataset.from_list([json.loads(l) for l in open(p, encoding="utf-8")])
ds_tr = carregar("/kaggle/working/dataset/train.jsonl")
ds_va = carregar("/kaggle/working/dataset/valid.jsonl")

tok = AutoTokenizer.from_pretrained(BASE, trust_remote_code=True)
if tok.pad_token is None: tok.pad_token = tok.eos_token

modelo = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.bfloat16,
                                              device_map="auto", trust_remote_code=True)
modelo.config.use_cache = False

# rank baixo: ACRESCENTAR línguas angolanas, não reescrever o modelo
lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
    target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"])

cfg = SFTConfig(output_dir=SAIDA, num_train_epochs=2,
    per_device_train_batch_size=2, gradient_accumulation_steps=8,
    learning_rate=1e-4, lr_scheduler_type="cosine", warmup_ratio=0.03,
    logging_steps=25, eval_strategy="steps", eval_steps=200,
    save_strategy="epoch", save_total_limit=1, bf16=True,
    gradient_checkpointing=True, max_seq_length=1024, packing=False, report_to="none")

trainer = SFTTrainer(model=modelo, args=cfg, peft_config=lora,
                     train_dataset=ds_tr, eval_dataset=ds_va, processing_class=tok)
trainer.train()
trainer.save_model(SAIDA); tok.save_pretrained(SAIDA)
print("LoRA guardado em", SAIDA)
"""),

MD("""## 5 · Fundir o LoRA nos pesos

O entregável do ADTC é **um** ficheiro `.gguf`. Um adaptador solto não serve."""),
CODE("""
import gc, torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

del trainer, modelo; gc.collect(); torch.cuda.empty_cache()
FUNDIDO = "/kaggle/working/ondjila-merged"

base = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.float16,
                                            device_map="cpu", trust_remote_code=True)
m = PeftModel.from_pretrained(base, "/kaggle/working/ondjila-lora").merge_and_unload()
m.save_pretrained(FUNDIDO, safe_serialization=True)
AutoTokenizer.from_pretrained(BASE, trust_remote_code=True).save_pretrained(FUNDIDO)
del base, m; gc.collect(); torch.cuda.empty_cache()
print("fundido em", FUNDIDO)
"""),

MD("""## 6 · Avaliação **depois** — comparar com a célula 3

Se o inglês tiver degradado, baixe as épocas de 2 para 1 ou o rank de 16 para 8, e repita.
Ganhar o bónus de língua africana e perder metade da nota de precisão não é negócio."""),
CODE("""avaliar("/kaggle/working/ondjila-merged", "DEPOIS — afinado")"""),

MD("## 7 · Converter para GGUF e quantizar"),
CODE("""
!git clone -q --depth 1 https://github.com/ggml-org/llama.cpp /kaggle/working/llama.cpp
!pip install -q -r /kaggle/working/llama.cpp/requirements/requirements-convert_hf_to_gguf.txt

!python /kaggle/working/llama.cpp/convert_hf_to_gguf.py /kaggle/working/ondjila-merged \\
        --outfile /kaggle/working/ondjila-f16.gguf --outtype f16

!cd /kaggle/working/llama.cpp && cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=ON -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF > /dev/null \\
  && cmake --build build --config Release -j --target llama-quantize > /dev/null

!/kaggle/working/llama.cpp/build/bin/llama-quantize \\
    /kaggle/working/ondjila-f16.gguf /kaggle/working/ondjila-Q4_K_M.gguf Q4_K_M

!rm -rf /kaggle/working/ondjila-f16.gguf /kaggle/working/ondjila-merged /kaggle/working/llama.cpp
!ls -lh /kaggle/working/*.gguf
"""),

MD("""## 8 · Descarregar

O ficheiro `ondjila-Q4_K_M.gguf` aparece no painel **Output**, à direita. Descarregue-o.

### Depois, na sua máquina — por esta ordem

1. **`bash tools/fix_template.sh`** sobre o novo ficheiro.
   Sem isto o modelo volta a gastar o orçamento de tokens a pensar em inglês e devolve
   resposta vazia a quem o corra sem parâmetros — que é exactamente como os jurados o correm.
2. Publicar como release asset e apontar o `download_model.sh` para lá.
3. **`bash tools/simular_juiz.sh`** — clona o repositório público do zero e verifica que
   um jurado consegue mesmo usá-lo.
4. **`bash tools/run_tests.sh`** — as 22 verificações.
"""),
]

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"},
        "accelerator": "GPU",
    },
    "nbformat": 4, "nbformat_minor": 5,
}

OUT.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"escrito: {OUT}")
print(f"celulas: {len(cells)}  ({sum(1 for c in cells if c['cell_type']=='code')} de codigo)")
