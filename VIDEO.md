# Guião do vídeo — 2 minutos, nem um segundo a mais

**Limite rígido: 120 segundos.** Passar disso pode invalidar. Cronometra.

---

## Decisões antes de gravares

**Grava o ecrã do PC, não com o telemóvel.** O telemóvel serve para um único plano: a mão a
desligar o cabo de rede. Todo o resto tem de ser captura de ecrã, senão o texto não se lê e a
telemetria — que é a nossa prova — perde-se.

Para gravar o ecrã em Windows: **`Win + Alt + R`** (a barra de jogo, já vem instalada). Grava em
1080p. Alternativa melhor se quiseres editar: OBS Studio.

**Fala em inglês.** Os jurados são pan-africanos e o FAQ diz que a língua de avaliação é o inglês.
O português aparece no ecrã, na demonstração — isso é mais forte do que dizê-lo. Se não estiveres
confortável a falar inglês, fala português e mete legendas em inglês, mas não deixes o vídeo sem
uma das duas.

**Prepara antes:**
1. `llama-server` a correr com `ondjila-Q4_K_M.gguf`
2. O lançador aberto em `http://127.0.0.1:8760`, no módulo **Arrendamento**
3. Uma janela de terminal com `htop` ou o Gestor de Tarefas visível, para se ver a RAM
4. Fecha o Chrome e o VS Code — a máquina precisa da memória

---

## O guião, com tempos

### 0:00 – 0:12 · O problema
**Mostra:** o teu ecrã com o site do Governo angolano que não abre (`portaldocidadao.gov.ao`).

> "In Angola there is a phrase you hear at every government counter: *falta de sistema*.
> The system is down. Come back tomorrow. For three months this year, that was literal —
> Luanda's entire civil registry was offline."

### 0:12 – 0:22 · A escala
**Mostra:** o hero do Ondjila, com os números.

> "Thirteen and a half million Angolans have no birth certificate. Fifteen million have no ID.
> The scarcity is not of documents. It is of knowing what to bring."

### 0:22 – 0:32 · Desliga a rede — **este plano é do telemóvel**
**Mostra:** a tua mão a desligar o cabo de rede, ou a desligar o wi-fi no ecrã. Sem cortes.

> "So everything you are about to see runs with no internet at all. Watch."

### 0:32 – 1:05 · A demonstração
**Mostra:** clicas na pergunta *"O meu senhorio subiu a renda de um mês para o outro"*.
Deixa ver o bloco dourado da lei a aparecer **antes** do primeiro token.

> "Before the model says a word, deterministic code selects the applicable law — Angolan Law
> twenty-six of fifteen, article forty — and the model is constrained to answer only from it."

Deixa correr o streaming. Não cortes. Que se vejam os tokens a nascer.

> "Without this, the same model on the same machine answered *yes, he can* — which is wrong.
> A two-billion-parameter model does not know Angolan law. It does not need to. It needs to read it."

### 1:05 – 1:25 · Os números
**Mostra:** a barra de telemetria — modelo, quantização, tokens, tok/s. E o htop com a RAM.

> "Two billion parameters, Q4_K_M, one point three five gigabytes of a seven gigabyte ceiling.
> CPU only. No GPU. No network. This is a twenty-fourteen-dollar laptop."

### 1:25 – 1:45 · O ecossistema
**Mostra:** voltas aos módulos, passas o rato pelos doze cartões.

> "Twelve domains — identity, work, housing, domestic violence, land, school — one engine,
> one model in memory. The engine has no jurisdiction inside it. Angola is the first."

### 1:45 – 2:00 · O fecho
**Mostra:** o mapa de África com Angola destacada.

> "There is no generative model on Earth that speaks any Angolan language. Kimbundu has zero
> models. Kikongo, zero. The entire clean web presence of Umbundu — six million speakers —
> is two megabytes.
> *Ondjila* means *the path*. It is the path that still works when the system is down."

---

## O que NÃO fazer

Não mostres slides. Não leias do papel com voz de leitura. Não aceleres o streaming em
pós-produção — a lentidão é honesta e o júri sabe que é um CPU sem GPU. Não digas que está
pronto para as pessoas usarem, porque não está.

Não uses música por cima da voz. Não metas emojis. Não mostres o VS Code com código a passar —
é o cliché de todos os vídeos de hackathon e não prova nada.

## Onde alojar

YouTube **não listado** ou Vimeo. As regras do ADTC não especificam plataforma, mas o campo do
Devpost aceita YouTube, Facebook Video, Vimeo ou Youku. Não listado é suficiente — não precisa de
ser público.

## Antes de submeteres o link

- [ ] Dura **menos de 120 segundos**
- [ ] Ouve-se a voz com clareza
- [ ] Lê-se o texto no ecrã em tela cheia
- [ ] O momento de desligar a rede está lá e é inequívoco
- [ ] A telemetria aparece com números a mexer
