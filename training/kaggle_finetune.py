"""
================================================================================
 ONDJILA -- fine-tuning no Kaggle (GPU gratuita)
================================================================================

COMO CORRER ISTO
----------------
1. kaggle.com -> Create -> New Notebook
2. Settings (barra direita):
      Accelerator = GPU P100      (ou T4 x2)
      Internet    = On
3. Notebook -> File -> Upload  ->  dataset/train.jsonl e dataset/valid.jsonl
      (ficam em /kaggle/input/ ou podem ser arrastados para /kaggle/working/)
4. Cola este ficheiro numa celula e corre.

Quota gratuita: ~30 h de GPU por semana, sessoes ate 12 h. Este treino leva
tipicamente 1,5 a 3 h numa P100. Sobra muito para repetir.

O QUE ESTE TREINO FAZ, E PORQUE
-------------------------------
Nao existe no mundo um modelo generativo que fale uma lingua angolana. Kimbundu
tem zero modelos no HuggingFace, Kikongo zero, e o Umbundu tres -- todos de voz
ou traducao, com 28 downloads somados. O Umbundu esta ausente do MADLAD-400 e o
OPUS devolve zero pares portugues-Umbundu.

E a transferencia entre linguas nao resolve: medido em 30 linguas ausentes do
treino continuado, um modelo adaptado fez 32,02 contra 32,33 da base. Zero. Nao
se chega ao Umbundu atraves do Suaili -- tem de se treinar em Umbundu.

Treinamos tres coisas:
  A) traducao pt <-> nove linguas nacionais (a Constituicao, dominio publico)
  B) ancoragem: responder SO a partir do extracto de lei dado
  C) abstencao: dizer "nao consta" em vez de inventar

O (C) e o mais importante e o mais esquecido. Perguntado sobre o aumento de
renda sem lei a frente, o modelo base respondeu "Sim, pode" -- quando a Lei 26/15
diz exactamente o contrario. Um modelo que sabe calar-se vale mais do que um que
sabe responder.

O QUE FICA DE FORA, DE PROPOSITO
--------------------------------
Ingles. A precisao do concurso e avaliada em ingles (o harness usa ARC-Easy) e
nao queremos deslocar essa distribuicao. Treinamos o que falta, nao o que ja ha.
Por isso o LoRA e de rank baixo e so 2 epocas: queremos acrescentar, nao reescrever.

MEDIR ANTES E DEPOIS
--------------------
Ha uma celula de avaliacao no fim. Se o ingles cair, reduzir a proporcao de
dados angolanos ou baixar o numero de epocas. Nao adianta ganhar o bonus de
lingua africana e perder metade da nota de precisao.
"""

# ==============================================================================
# CELULA 1 -- dependencias
# ==============================================================================
INSTALL = r"""
!pip install -q -U "transformers>=4.46" "peft>=0.13" "trl>=0.12" "datasets>=3.0" \
                   "accelerate>=1.0" bitsandbytes sentencepiece
"""

# ==============================================================================
# CELULA 2 -- treino
# ==============================================================================
TREINO = r'''
import json, os, torch
from pathlib import Path
from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig
from trl import SFTTrainer, SFTConfig

BASE   = "Qwen/Qwen3.5-2B"
SAIDA  = "/kaggle/working/ondjila-lora"
MAXLEN = 1024          # os artigos da Constituicao cabem folgadamente

# Os ficheiros podem estar em /kaggle/input/<dataset>/ ou em /kaggle/working/
def achar(nome):
    for p in Path("/kaggle").rglob(nome):
        return str(p)
    raise SystemExit(f"nao encontrei {nome}. Carregue dataset/{nome} no notebook.")

train_p, valid_p = achar("train.jsonl"), achar("valid.jsonl")
print("treino:", train_p, "\nvalidacao:", valid_p)

carregar = lambda p: Dataset.from_list([json.loads(l) for l in open(p, encoding="utf-8")])
ds_tr, ds_va = carregar(train_p), carregar(valid_p)
print(f"exemplos: treino {len(ds_tr)}, validacao {len(ds_va)}")

tok = AutoTokenizer.from_pretrained(BASE, trust_remote_code=True)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token

modelo = AutoModelForCausalLM.from_pretrained(
    BASE, torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=True)
modelo.config.use_cache = False

# rank baixo: queremos ACRESCENTAR linguas angolanas, nao reescrever o modelo.
lora = LoraConfig(
    r=16, lora_alpha=32, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
    target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
)

cfg = SFTConfig(
    output_dir=SAIDA,
    num_train_epochs=2,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,      # lote efectivo 16
    learning_rate=1e-4,
    lr_scheduler_type="cosine",
    warmup_ratio=0.03,
    logging_steps=25,
    eval_strategy="steps",
    eval_steps=200,
    save_strategy="epoch",
    save_total_limit=2,
    bf16=True,
    gradient_checkpointing=True,
    max_seq_length=MAXLEN,
    packing=False,                      # cada exemplo e um par completo
    report_to="none",
)

trainer = SFTTrainer(
    model=modelo, args=cfg, peft_config=lora,
    train_dataset=ds_tr, eval_dataset=ds_va, processing_class=tok,
)
trainer.train()
trainer.save_model(SAIDA)
tok.save_pretrained(SAIDA)
print("LoRA guardado em", SAIDA)
'''

# ==============================================================================
# CELULA 3 -- fundir o LoRA nos pesos base
# ==============================================================================
FUNDIR = r'''
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

BASE, LORA = "Qwen/Qwen3.5-2B", "/kaggle/working/ondjila-lora"
FUNDIDO = "/kaggle/working/ondjila-merged"

# O entregavel do ADTC e UM ficheiro .gguf. Um adaptador solto nao serve:
# tem de ser fundido nos pesos antes de converter e quantizar.
base = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.float16,
                                            device_map="cpu", trust_remote_code=True)
m = PeftModel.from_pretrained(base, LORA).merge_and_unload()
m.save_pretrained(FUNDIDO, safe_serialization=True)
AutoTokenizer.from_pretrained(BASE, trust_remote_code=True).save_pretrained(FUNDIDO)
print("fundido em", FUNDIDO)
'''

# ==============================================================================
# CELULA 4 -- avaliacao antes/depois (NAO SALTAR)
# ==============================================================================
AVALIAR = r'''
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

CASOS = [
  ("ancoragem (deve dizer QUE NAO PODE)",
   "Es o Ondjila. Responde so a partir do extracto. Sem asteriscos.\n\n"
   "[Lei 26/15, art. 40.o] O senhorio nao pode aumentar a renda de um mes para o outro. "
   "O aumento tem de ser comunicado por escrito com antecedencia minima de 60 dias.",
   "O meu senhorio subiu a renda de um mes para o outro. Pode fazer isso?"),
  ("abstencao (deve dizer QUE NAO CONSTA)",
   "Es o Ondjila. Responde so a partir do extracto. Se nao constar, di-lo.\n\n"
   "[Lei 26/15, art. 40.o] O aumento da renda exige 60 dias de aviso escrito.",
   "Quanto custa registar uma crianca?"),
  ("umbundu (deve traduzir, nao explicar)",
   "Es um tradutor entre o portugues de Angola e o Umbundu.",
   "Traduz para Umbundu: Todos os cidadaos sao iguais perante a lei."),
  ("ingles (nao pode ter degradado)",
   "You are a helpful assistant. Answer in one sentence.",
   "What is the capital of France?"),
]

def testar(caminho, etiqueta):
    tok = AutoTokenizer.from_pretrained(caminho, trust_remote_code=True)
    mod = AutoModelForCausalLM.from_pretrained(caminho, torch_dtype=torch.float16,
                                               device_map="auto", trust_remote_code=True)
    print("\n" + "=" * 70); print(f"  {etiqueta}"); print("=" * 70)
    for nome, sistema, pergunta in CASOS:
        msgs = [{"role":"system","content":sistema},{"role":"user","content":pergunta}]
        ids = tok.apply_chat_template(msgs, add_generation_prompt=True,
                                      return_tensors="pt",
                                      enable_thinking=False).to(mod.device)
        with torch.no_grad():
            out = mod.generate(ids, max_new_tokens=110, temperature=0.3, do_sample=True,
                               pad_token_id=tok.pad_token_id or tok.eos_token_id)
        r = tok.decode(out[0][ids.shape[-1]:], skip_special_tokens=True).strip()
        print(f"\n  [{nome}]\n  {r[:320]}")
    del mod; torch.cuda.empty_cache()

testar("Qwen/Qwen3.5-2B", "ANTES -- modelo base")
testar("/kaggle/working/ondjila-merged", "DEPOIS -- afinado")
'''

# ==============================================================================
# CELULA 5 -- converter para GGUF e quantizar
# ==============================================================================
GGUF = r'''
!git clone -q --depth 1 https://github.com/ggml-org/llama.cpp /kaggle/working/llama.cpp
!pip install -q -r /kaggle/working/llama.cpp/requirements/requirements-convert_hf_to_gguf.txt

!python /kaggle/working/llama.cpp/convert_hf_to_gguf.py \
    /kaggle/working/ondjila-merged \
    --outfile /kaggle/working/ondjila-f16.gguf \
    --outtype f16

!cd /kaggle/working/llama.cpp && cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=ON \
    && cmake --build build --config Release -j --target llama-quantize

!/kaggle/working/llama.cpp/build/bin/llama-quantize \
    /kaggle/working/ondjila-f16.gguf \
    /kaggle/working/ondjila-Q4_K_M.gguf Q4_K_M

!ls -lh /kaggle/working/*.gguf
!rm -f /kaggle/working/ondjila-f16.gguf   # so o Q4_K_M e que se descarrega

print("""
--------------------------------------------------------------------
DEPOIS DE DESCARREGAR ondjila-Q4_K_M.gguf:

  1. Aplicar a correccao do raciocinio ao novo ficheiro:
         bash tools/fix_template.sh
     (sem isto o modelo volta a gastar o orcamento a pensar em ingles
      e devolve resposta vazia a quem o corra sem parametros)

  2. Publicar como release asset e apontar o download_model.sh para la.

  3. Correr tools/simular_juiz.sh -- clona o repositorio publico do zero
     e verifica que um juiz consegue mesmo usa-lo.
--------------------------------------------------------------------
""")
'''

if __name__ == "__main__":
    print(__doc__)
    for nome, celula in [("1 dependencias", INSTALL), ("2 treino", TREINO),
                         ("3 fundir", FUNDIR), ("4 avaliar", AVALIAR), ("5 gguf", GGUF)]:
        print("\n" + "=" * 78)
        print(f"  CELULA {nome}")
        print("=" * 78)
        print(celula)
