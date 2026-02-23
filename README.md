# PPH-001: Prior-Protective Hallucination

**Structured confabulation in large language models when presented with data contradicting trained priors.**

📄 [Full article: "Your AI Is Hallucinating on Purpose"](https://seriesfusion.com) · 🧪 SeriesFusion Research

---

## What This Is

PPH-001 is a controlled experiment measuring how LLMs respond when given clean data that contradicts their training. We found that models don't just fail — they fabricate systematically, inventing explanations that protect what they already "know." We call this **Prior-Protective Hallucination (PPH)**.

One sentence stops it: *"If the data doesn't match established expectations, it's acceptable to say so."*

## Key Findings

- **168 experimental runs** across 5 phases, 3 models (Claude Opus 4.6, Gemini 3 Pro, DeepSeek R1), 2 knowledge domains (economics, physics)
- **Confabulations are structured, not random.** The same fabricated explanations recur at 80–100% rates across independent runs
- **Three protection strategies identified:** Rationalization (soft priors), Denial (hard priors), Source Impeachment (accusing data collectors)
- **SelfCheckGPT can't catch it.** At the standard detection threshold, 36% of fabricated claims pass as "likely factual." Consistency-based detection assumes hallucinations are inconsistent. These aren't.
- **The escape hatch works universally.** 100% effective across every model, temperature, domain, and confabulation type tested — including fabrication-from-ignorance and fabrication-from-insufficient-knowledge

## Repository Structure

```
pph-001/
├── data/
│   ├── phase1/          # 18 Phase 1 pilot JSON files
│   ├── phase1-v2/       # 12 Phase 1 rerun JSON files (temp 0.0)
│   ├── phase1-v3/       # 6 Gemini isolation JSON files (temp 0.7)
│   ├── phase2a/         # 120 stochastic consistency JSON files
│   ├── phase2b/         # 12 escape hatch specificity JSON files
│   └── summaries/       # Aggregate summary JSONs per phase
├── scripts/
│   ├── run_experiment.py       # Phase 1 experiment runner
│   ├── run_v2.py               # Phase 1 rerun (OpenRouter, temp 0.0)
│   ├── run_claude_block.py     # Claude-specific block runner
│   └── selfcheckgpt_test.py   # SelfCheckGPT blind spot test
├── analysis/            # Scoring docs, results analysis
└── README.md
```

## Data Format

Each JSON file represents a single model response to a structured prompt containing contradictory data. Files include:

- **Model identifier** and routing method
- **Temperature setting**
- **Domain** (economics or physics)
- **Condition** (aligned, mild conflict, severe conflict, or escape hatch)
- **Raw model response**
- **Scoring** on 5 dimensions: confabulation count, confabulation specificity (1–3), prior preservation, hedging count, contradiction acknowledgment

## Phases

| Phase | Runs | Purpose |
|-------|------|---------|
| Phase 1 | 18 | Pilot — all model × domain × condition combinations |
| Phase 1 Rerun | 12 | Deterministic baseline (temp 0.0) via OpenRouter |
| Phase 1v3 | 6 | Gemini isolation (temp 0.7, severe conditions) |
| Phase 2A | 120 | Stochastic consistency (20 runs × 3 models × 2 domains, temp 0.7) |
| Phase 2B | 12 | Escape hatch specificity (prior-conflict + non-conflict types) |

## Models Tested

| Model | Key Behavior |
|-------|-------------|
| **Claude Opus 4.6** | Confabulates while hedging — warns against "force-fitting explanations" while inventing six of its own |
| **Gemini 3 Pro** | Highest specificity — builds formal equations, then pivots to accusing experimenters of fraud |
| **DeepSeek R1** | Highest volume — 8 invented explanations per economics scenario. Reasoning trace shows false memories forming upstream |

## Reproducing

Scripts use the OpenRouter API. You'll need:
- An OpenRouter API key
- Python 3.10+
- `requests`, `json`, `os` (standard library except `requests`)

For the SelfCheckGPT test:
- `bert-score` package
- The Phase 2A data files

## Citation

```
Hippensteel, T. (2026). Prior-Protective Hallucination: Structured Confabulation
in Large Language Models Under Knowledge Conflict. SeriesFusion.
```

## License

Data and scripts released under [MIT License](LICENSE). Use freely. If you extend this work, we'd love to hear about it.

---

*This is a SeriesFusion research project. Questions, replications, and extensions welcome.*
