# Technical Report — Ondjila

**Team ID:** ondjila
**Domain:** autonomous_ai_agents
**Model:** Qwen3.5-2B-Q4_K_M
**Author:** Augusto Bernardo Lopes (Angola)

---

## Problem

In Angola there is a phrase you hear at every government counter: *"falta de sistema."* The system is
down. Come back tomorrow. For most of 2026 it was literal — Luanda's civil registry and
identification posts were offline for nearly three months over a payment dispute with a supplier.

Behind that phrase, from the 2024 Census: **13.53 million Angolans have no birth registration, and
14.98 million have no ID card.** Registration is worst among the youngest — only 39.2% of children
under five are registered. There is a circular trap: registering a child requires the parents'
documents, which roughly 15 million adults do not have. 47.7% of people who sought a document in the
past year paid a bribe — not because the fee is high (registration has been free since 2013) but
because information is scarce and the queue is long.

Parliament is moving to make the ID card the only valid voting document for the 2027 elections. Rural
ID coverage is 30.9%.

**The scarcity is not of documents. It is of knowing what to bring.** Ondjila exists for the single
most valuable moment in the process: before a journey a person can only afford to make once.

**Why offline is load-bearing, not decorative.** 287 of Angola's 536 communes — 54% — have no mobile
broadband. Only 5.7% of rural households have grid electricity. And the state's own services are
frequently unreachable: while researching this project we probed the government domains and found
`portaldocidadao.gov.ao` with no DNS record, the Ministry of Education's site refusing connections,
and `gov.ao` serving a file server with a long-expired certificate.

## Design Decisions

- **Base model:** Qwen3.5-2B. Measured on four candidates under identical conditions (below).
- **Quantization:** GGUF Q4_K_M. Downstream task accuracy is flat from Q4_K_S upward; perplexity keeps
  improving above it but task accuracy does not. Q6_K and Q8_0 buy nothing and cost RAM.
- **Alternatives considered and rejected:**
  - *Qwen3.5-4B* — measured 1.91 tok/s and 2.78 GB peak on our reference machine. It misses the
    throughput reference and loses roughly 6 points to the smaller models, which its ~6.7-point BFCL
    advantage does not recover.
  - *IQ4_XS* — llama.cpp's CPU repack path covers Q4_0/Q4_K/Q5_K/Q6_K/Q8_0/Q2_K/IQ4_NL/MXFP4. IQ4_XS
    is absent, so it trades ~9% file size for a decode penalty on a machine that is already speed-starved.
  - *q4_0 KV cache* — measured output similarity against f16 is 8.3%, and llama.cpp's own function-calling
    docs warn it substantially degrades tool calling. We use q8_0.
  - *Draft-model speculative decoding* — no RAM headroom, and we could not find a single published
    CPU-only measurement. Left out rather than assumed.
  - *OpenBLAS* — `GGML_BLAS` takes precedence over `GGML_LLAMAFILE` and disables the tinyBLAS kernels,
    which measure roughly 2.7× faster than Intel MKL on L2-resident matrices. Built with the defaults instead.

### The architecture, and why it is the point

Published benchmarks put a 1.7B model at ~80% valid tool-call syntax but only **~17% completion on
multi-turn agentic tasks**. The failure compounds: with per-step accuracy *p* over *m* steps, success
is *p^m*, and the per-step error rate rises as the trajectory grows because the model conditions on
its own earlier mistakes. Under a 7 GB CPU ceiling, "use a bigger model" is not available.

So Ondjila takes the decision away from the model:

1. **Retrieve** — deterministic code selects the applicable law from a cited corpus, *before*
   generation begins.
2. **Ground** — the model receives those extracts and is constrained to answer only from them.
3. **Commit** — actions are emitted under a **GBNF grammar compiled from the current state's schema**,
   so the model is physically incapable of producing an illegal transition.
4. **Decide and verify** — deadlines, amounts, eligibility and document lists are evaluated by code.

Existing work constrains decoding (Outlines, XGrammar, llama.cpp's JSON-schema mode) *or* control flow
(LangGraph, Burr). We compile a **different grammar per state from the workflow itself**, which
removes two failure classes by construction rather than by validate-and-retry.

Constrained decoding is effectively free on this hardware: mask computation costs ~50 µs, and at a few
tokens per second that is under 0.03% overhead. The published slowdowns come from GPU serving where a
token costs milliseconds.

**Why this matters for a language nobody serves.** Recent work on tool calling across Chinese, Hindi
and Igbo found multilingual degradation is driven by *execution-interface violations rather than
semantic misunderstanding* — models pick the right tool and produce sensible arguments, then fail the
strict surface form the executor demands. That is precisely the class grammar-constrained decoding
eliminates. The language work and the engineering work are the same work.

### The measurement that justifies the whole design

Same machine, same model, same question — *"my landlord raised the rent from one month to the next,
can he do that?"*

| | Answer |
|---|---|
| Model alone | **"Sim, pode."** (Yes, he can.) — wrong |
| With retrieval + grounding | **"Não pode."** followed by the 60-day written-notice rule and its source — correct |

Angolan Law 26/15, art. 40 requires 60 days' written notice. A 2B model does not know Angolan law and
invents fluently. It does not need to know it — it needs to read it.

## Constraints

- Target: 4 vCPU, 8 GB RAM, integrated graphics only, Ubuntu 22.04. **7 GB is a disqualification
  ceiling, not a penalty.**
- Zero network access during evaluation.
- llama.cpp with GGUF weights only.
- **Corpus licensing.** Angolan Law 15/14, art. 24 places statutes and administrative and judicial
  decisions *outside the scope of copyright entirely* — not licensed, never protected. We audited the
  alternatives and rejected a healthcare use case after finding UNICEF explicitly prohibits
  "compilation for CD-ROM or any other electronic media", and that the Portuguese mhGAP guide is
  licensed NoDerivs.
- **Language.** 71.3% of rural Angolans do not have Portuguese as a mother tongue; rural literacy is
  43.5%, and 32.9% among rural women.

## Benchmarks

Development machine: **Intel i5-3570S (2012), 4 cores, no AVX2/FMA**, WSL Ubuntu 22.04, 8 GB cap,
swap disabled. Command: `llama-bench -p 512 -n 128 -ngl 0 -t 4 -r 3 --load-mode mlock`.

| Model | File | pp512 (t/s) | tg128 (t/s) | Peak RSS |
|---|---|---|---|---|
| Qwen3-1.7B | 1.1 GB | 10.31 | 2.78 | 1.19 GB |
| **Qwen3.5-2B (chosen)** | 1.2 GB | **16.81** | 2.67 | **1.35 GB** |
| Granite-4.1-3B | 2.0 GB | 9.67 | 3.17 | 2.10 GB |
| Qwen3.5-4B | 2.6 GB | 9.62 | **1.91** | 2.78 GB |

Generation clusters between 2.67 and 3.17 t/s across the three small models because **on a CPU without
AVX2 generation is compute-bound on dequantization, not memory-bound** — so model size barely moves it.
What discriminates is prefill, where Qwen3.5-2B leads by 63% over the 1.7B and 74% over Granite. In an
agent loop prefill dominates, since the system prompt and tool schemas are re-sent every turn.

**These numbers are a floor, not an estimate.** The evaluation machine is a 10th–12th generation i5
*with* AVX2, which enables Q4_K runtime repacking (measured at +61% prefill elsewhere) and has roughly
twice the memory bandwidth. Self-reported profiler figures will be measured on a 4-vCPU instance
matching the target profile, not on this machine.

| Metric | Value |
|---|---|
| Machine | Intel i5-3570S, 4 cores, no AVX2, DDR3 |
| Peak RAM | **1.35 GB** of a 7 GB ceiling |
| Generation | 2.67 t/s (bench) · 3.05–4.08 t/s (server, live) |
| Thermal throttling | none observed |

### Two failures worth recording

**The model was silent.** Qwen3.5 is a reasoning model. By default it spent its entire token budget
thinking — *in English* — and returned empty `content` with `finish_reason: length`. Measured: with
reasoning, 90 tokens in 28.1 s and no answer; with `enable_thinking: false`, a complete answer in
11.5 s at 4.08 t/s. At 3 tok/s a reasoning model is unusable.

**The first benchmark was measuring the disk.** It reported 0.68 t/s for a 1.7B model and 2.34 t/s for
a 2B — the smaller model slower than the larger, which is physically impossible. The host had 0.26 GB
of free RAM and, with memory-mapped weights, the kernel was evicting the model and re-reading it from
SSD every pass. Pinning the weights with `--load-mode mlock` fixed it. Self-reporting those figures
would have failed the profiler's reconciliation step, which fails above 50% divergence from the audit
machine.

## Honest limitations

- The model is not yet fine-tuned. Umbundu capability is the next step and the basis of the African
  language claim. Today the system is a base model plus a grounded, deterministic harness.
- **There is no generative language model on Earth that speaks any Angolan language.** Kimbundu has
  zero models on Hugging Face; Kikongo has zero; Umbundu has three, all speech or translation, with 28
  downloads between them. Umbundu is absent from MADLAD-400 and OPUS returns zero Portuguese–Umbundu
  sentence pairs. The entire cleaned web presence of a language with ~6 million speakers is about
  **2 megabytes**. Cross-lingual transfer does not help: across 30 languages absent from continued
  pretraining, an adapted model scored 32.02 against a 32.33 baseline.
- What makes it tractable: **Angola's Constitutional Court publishes the Constitution in nine national
  languages**, a human-authored public-domain parallel corpus in exactly this project's domain.
- The legal corpus currently covers 15 rules across 7 modules. Retrieval is keyword-based — deliberately
  auditable and reproducible at this stage rather than subtle.
- This is not ready to be used by the people it is written for.
