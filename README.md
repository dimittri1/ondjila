# Ondjila

**An offline agent runtime for places where the system is down.**

`onjila` — path, road (Umbundu)

---

Ondjila runs a complete autonomous agent on a low-cost laptop with **no internet connection, no
cloud, and no GPU**, inside a **7 GB memory ceiling**. It is built for the two thirds of the world
where connectivity is intermittent, expensive, or simply absent — and where the information people
need most is locked behind a counter that is closed.

It is one engine and many modules. The engine is universal. The modules are local.

## The problem this exists to solve

Small language models are unreliable agents, and the failure is structural rather than cosmetic. A
1.7B model emits syntactically valid tool calls roughly 80% of the time but completes only about
**17% of multi-turn agentic tasks**. The arithmetic is unforgiving: with per-step accuracy *p* across
*m* steps, end-to-end success is *p^m*, and the per-step error rate *rises* as the trajectory grows
because the model conditions on its own earlier mistakes.

The usual response is a bigger model. That option does not exist under a 7 GB ceiling on a CPU.

**So Ondjila removes the decision from the model.** At every step the model can physically only emit
a legal transition for the state it is in, because the engine compiles a **GBNF grammar from that
state's schema** and constrains decoding to it. Rules, arithmetic, eligibility and deadlines are
evaluated by deterministic code that cannot hallucinate. The model does the one thing it is good at —
understanding what a person meant, and saying something back in their language.

The model proposes. Code disposes.

## Why this matters for languages nobody serves

Recent work on tool calling across Chinese, Hindi and Igbo found that multilingual degradation is
driven by **execution-interface violations rather than semantic misunderstanding**: models select the
correct tool and generate sensible arguments, then fail the strict surface form the executor demands.

That is exactly the failure class grammar-constrained decoding eliminates by construction. Which is
why, in this project, the language work and the engineering work are the same work.

## Architecture

```
                   ┌─────────────────────────────────────────┐
   free text  ───► │  UNDERSTAND    model, unconstrained     │
   (any language)  │                reasons in the open      │
                   ├─────────────────────────────────────────┤
                   │  COMMIT        model, GBNF-constrained  │
                   │                to this state's schema   │
                   ├─────────────────────────────────────────┤
                   │  DECIDE        deterministic code       │  ◄── no model
                   │                rules, dates, amounts    │
                   ├─────────────────────────────────────────┤
                   │  VERIFY        deterministic checks     │  ◄── no model
                   │                one repair attempt max   │
                   └─────────────────────────────────────────┘
                                     │
                                     ▼
                        next state, or a cited answer
```

Two-stage generation is deliberate. Forcing a small model to *reason* inside a rigid schema costs
accuracy — measured at 0.5–1.7B, hard schema decoding raised output validity from 61.5% to 100% while
answer accuracy *fell* from 19.7% to 11.0%. Constraints turn loud failures into silent ones. Letting
the model think in the open and only constraining the committed action recovers most of that loss
(+24 points on GSM8K at 1B).

Constrained decoding is effectively free here: mask computation costs about 50 µs, and on a CPU
generating a few tokens per second that is under 0.03% overhead. The published slowdowns come from
GPU serving, where a token costs milliseconds rather than hundreds of them.

## Repository layout

```
ondjila/
├── engine/          the runtime — universal, no jurisdiction inside it
│   ├── grammar.py   compiles a GBNF grammar from a state schema
│   ├── fsm.py       state machine executor
│   ├── decide.py    deterministic rule evaluation
│   ├── verify.py    validators and the single repair attempt
│   └── llm.py       llama.cpp interface
├── modules/         one folder per jurisdiction
│   └── ao/          Angola — the first and deepest instantiation
├── corpus/          source texts, with provenance and licence per file
├── launcher/        the screen where a person chooses what they need
├── eval/            evaluation sets, including Umbundu
├── metadata.json    ADTC 2026 submission descriptor
├── download_model.sh
└── REPORT.md
```

## Modules

A module is not an application. It is a declaration: a state machine, a set of deterministic rules, a
slice of source corpus, and the phrasings used to talk to a person. Every module shares the same
model in memory and the same engine.

That is what makes an ecosystem affordable under a 7 GB ceiling — and what lets someone in another
country add their own jurisdiction without touching the engine.

## Angola: the first instantiation

Angola is where this starts, because it is the hardest case we have direct knowledge of.

**13.53 million people have no birth registration. 14.98 million have no ID card.** Only 39.2% of
children under five are registered. There is a circular trap — registering a child requires the
parents' documents, which roughly 15 million adults do not have. 47.7% of people who sought a
document in the past year paid a bribe, not because the fee is high (it has been free since 2013) but
because information is scarce and the queue is long.

**54% of Angola's communes have no mobile broadband. 5.7% of rural households have grid electricity.
71.3% of rural Angolans do not have Portuguese as a mother tongue.** Rural literacy is 43.5%, and
32.9% among rural women.

There is also a phrase you hear at every counter: *"falta de sistema."* The system is down. In 2026
that was literal — Luanda's civil registry and identification posts were offline for nearly three
months over a payment dispute with a supplier.

## Language

Portuguese first, with Umbundu as the first minority language.

There is no generative language model on Earth that speaks any Angolan language. On Hugging Face,
Kimbundu has zero models of any kind; Kikongo has zero; Umbundu has three, all speech or translation,
with 28 downloads between them. Umbundu is entirely absent from MADLAD-400, and OPUS returns zero
Portuguese–Umbundu sentence pairs. The entire cleaned web presence of a language with roughly six
million speakers is about **two megabytes**.

Cross-lingual transfer does not rescue this: across 30 languages absent from continued pretraining, an
adapted model scored 32.02 against a 32.33 baseline. You cannot reach Umbundu through Swahili.

What made this tractable is that **Angola's Constitutional Court publishes the Constitution in nine
national languages** — a human-authored, public-domain parallel corpus, in precisely this project's
domain.

## Licensing of source material

Article 24 of Angolan Law 15/14 places statutes and administrative and judicial decisions **outside
the scope of copyright entirely** — not licensed, never protected. Every corpus file carries its
provenance and licence in `corpus/`, and the ingest pipeline refuses anything it cannot account for.

## Status

Under active development for the Africa Deep Tech Challenge 2026. Not yet ready for use by the people
it is written for.
