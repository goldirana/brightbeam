# BrightBeam — AI-Powered Call Summarisation Tool

Generates structured summaries from insurance call transcripts using a pipeline architecture combining traditional ML feature extraction with LLM-based summarisation and validation.

---

## How It Works

### Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                         CLI (src/cli.py)                          │
│            Single entry point, incremental save, resume           │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                   Orchestrator (src/orchestrator.py)              │
│              Coordinates pipeline stages in sequence              │
└───┬──────────────┬──────────────────┬────────────────┬───────────┘
    │              │                  │                │
    ▼              ▼                  ▼                ▼
┌────────┐  ┌───────────┐  ┌──────────────┐  ┌──────────────┐
│Feature │  │ Clustering│  │Summarisation │  │ Validation   │
│Extract │  │ (routing) │  │   (LLM)      │  │ (3 layers)   │
└────────┘  └───────────┘  └──────────────┘  └──────────────┘
```

### Pipeline Stages

**1. Feature Extraction** (Traditional ML — no LLM, no cost)

| Extractor | What It Does | Purpose |
|-----------|-------------|---------|
| NER (regex) | Finds £ amounts, dates, phone numbers, emails, IBANs, reference numbers | Ground truth for factual validation |
| Keywords (RAKE) | Extracts important multi-word phrases | Feeds clustering signals |
| Sentiment (VADER) | Scores each speaker turn positive/negative | Stored in results for analytics |
| Domain signals | Scores transcript against category keyword lists | Input to clustering |

**2. Clustering** (Category assignment)

- Computes how strongly a transcript matches each predefined category (liability, injury, vehicle damage, property, settlement, general enquiry)
- If pre-built centroids exist: uses cosine similarity against average vectors learned from training data
- Otherwise: picks the category with the highest keyword match score
- Output: a category label (e.g., `"vehicle_damage"`) used to select the right prompt

**3. Summarisation** (LLM via OpenRouter)

- Loads a category-specific prompt from `prompts/category/{category}.txt`
- Combines with base system prompt + output format template
- Calls the LLM (configurable in `config.yaml`) to generate the structured summary
- Includes follow-up detection: flags calls with potential business leads or escalation risks

**4. Validation** (3 layers)

| Layer | Method | What It Catches | LLM Cost |
|-------|--------|----------------|----------|
| Structural | Pydantic model + format rules | Missing sections, char limit >1500, wrong caller format | None |
| Factual | NER cross-check (transcript entities vs summary entities) | Hallucinated amounts, missing reference numbers, wrong dates | None |
| Quality (Judge) | Separate LLM call with scoring rubric | Wrong caller identification, misunderstood context, poor tone | 1 LLM call |

If validation fails → retry with targeted feedback (max 2 retries) → if still failing → flag for human review.

---

## Setup

```bash
# 1. Clone and enter project
cd brightbeam

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure API key
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY
```

---

## How to Run

### Single command (runs entire pipeline):
```bash
./run.sh
```

### Individual steps:
```bash
source .venv/bin/activate

# Step 1: Build cluster centroids from training examples
python -m src.cli discover-clusters

# Step 2: Summarise test transcripts
python -m src.cli summarise

# Step 3: Generate HTML dashboard
python -m src.cli dashboard
```

### Options:
```bash
# Process an entire folder of transcripts
python -m src.cli process-folder data/raw/bb-hiring-call-summary/to-summarise

# Process folder with custom glob pattern and output directory
python -m src.cli process-folder ./my-transcripts --pattern "*.txt" --output-dir ./my-output

# Process a single file
python -m src.cli summarise --input-file data/raw/bb-hiring-call-summary/to-summarise/3-transcript.txt

# Reprocess everything (ignore previous results)
python -m src.cli summarise --no-resume

# Custom output directory
python -m src.cli summarise --output-dir ./my-output
```

---

## Configuration

Everything is controlled from two files:

| File | What It Controls |
|------|-----------------|
| `config.yaml` | Models, categories, keywords, NER patterns, stop words, paths, thresholds |
| `.env` | API keys (secrets, gitignored) |

### To change the LLM model:
```yaml
# config.yaml
models:
  summarisation:
    model: "anthropic/claude-sonnet-4"  # ← change this one line
```

### To add a new call category:
1. Add the category + keywords in `config.yaml` under `categories:`
2. Create a prompt file at `prompts/category/{new_category}.txt`
3. Re-run `python -m src.cli discover-clusters`

---

## Project Structure

```
brightbeam/
├── run.sh                    # One script to run everything
├── config.yaml               # Single source of truth (all settings)
├── .env                      # API keys (gitignored)
├── prompts/                  # LLM prompts as editable text files
│   ├── system/base.txt       # Core instructions
│   ├── system/output_format.txt  # Required output structure
│   ├── system/retry.txt      # Retry with feedback template
│   ├── category/*.txt        # Per-category guidance
│   └── judge/*.txt           # Validation judge prompts
├── src/
│   ├── cli.py                # Entry point (click CLI)
│   ├── orchestrator.py       # Pipeline coordinator
│   ├── config/manager.py     # Singleton config access
│   ├── models/               # Pydantic data contracts
│   ├── services/
│   │   ├── feature_extraction/   # ML: NER, keywords, sentiment
│   │   ├── clustering/           # Category assignment
│   │   ├── summarisation/        # LLM interaction + parsing
│   │   └── validation/           # 3-layer quality checks
│   ├── dashboard/            # HTML report generator
│   └── scripts/              # Cluster discovery
├── data/raw/                 # Training examples + test transcripts
└── output/                   # Generated summaries + dashboard
```

---

## Output Format

```
Caller: [Name], [relationship], [direction]

Subject:
[One-line description]

Executive Summary:
[What happened and why]
- [Key facts as bullet points]

Next Steps:
COMPANY: [Action required]
Other: [Action by other parties, or "None"]

Follow-Up Required: [Yes/No]
Reason: [If yes, business justification]

[Conditional sections only if discussed: Liability, Negotiation, Vehicle Damage, Injury, Property]
```

---

## What Could Be Improved

Given more time, these are the improvements I would prioritise:

### 1. Structured Output via Pydantic (LLM response format)
Currently the LLM returns free-text that gets parsed with regex into a Pydantic model. A better approach would be to use **function calling / structured output** (e.g., OpenAI's `response_format` or Anthropic's tool use) to force the LLM to return valid JSON matching the `CallSummary` Pydantic schema directly. This eliminates parsing errors entirely.

### 2. Test Suite
No automated tests are currently implemented. Priority tests would be:
- Unit tests for each extractor (NER, keywords, sentiment)
- Integration tests for the full pipeline on known-good examples
- Regression tests comparing output against the 10 "good" training summaries
- Mock LLM responses for fast CI runs without API costs

### 3. Production Deployment — Separate Scalable Pipelines
In production, the monolithic pipeline should be split into independently deployable microservices:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Feature    │    │  Clustering │    │Summarisation│    │ Validation  │
│  Extraction │───►│   Service   │───►│   Service   │───►│   Service   │
│  (CPU-only) │    │  (CPU-only) │    │ (LLM calls) │    │ (LLM calls) │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
   Scale: low         Scale: low        Scale: HIGH        Scale: medium
```

- Feature extraction and clustering are CPU-bound and cheap — they don't need scaling
- Summarisation is the bottleneck (LLM API latency) — scale this independently
- Message queue (RabbitMQ/SQS) between stages for decoupling and back-pressure (I am not sure about it to be honest - More specific these tools but aware about the concept )
- Each service can be deployed, monitored, and scaled independently: Use Grafana and prometheus but looking at the complexity not required

### 4. Sentiment Utilisation
Currently sentiment is extracted but **not surfaced in the summary output** or used for routing decisions. Improvements:
- Include sentiment score in the dashboard per-transcript view (already partially done)
- Use negative sentiment trajectory to auto-flag escalation-risk calls
- Feed sentiment to the summariser as context: "Customer was frustrated (sentiment: -0.6)" so the summary reflects tone
- Route highly negative calls to a specialised "complaint handling" prompt

### 5. Prompt Optimisation
- A/B test different prompt variants using the judge quality scores as metrics
- Use the "good" training examples as few-shot examples in the prompt
- Implement prompt versioning to track which prompt version produced which results

### 6. Parallel Processing
- Process multiple transcripts concurrently (async gather) for faster batch runs
- Rate limiting to stay within API quotas
- Priority queue: follow-up-required calls processed first

### 7. Caching & Cost Reduction
- Cache embeddings and cluster assignments for repeated transcripts
- Use a cheaper/faster model for the judge (e.g., GPT-4o-mini) since it only scores
- Fine-tune a smaller model on the good examples to replace the expensive LLM

### 8. Observability
- Structured logging with correlation IDs per transcript
- Metrics: latency per stage, token usage, retry rate, quality score distribution
- Alerting on quality score degradation (model drift detection)

---

## Production Deployment

Demonstration infrastructure lives in `infra/`:

| Path | Purpose |
|------|---------|
| `infra/docker/Dockerfile` | Container image for the pipeline |
| `infra/docker/docker-compose.yml` | Local multi-service simulation (3 replicas) |
| `infra/terraform/main.tf` | AWS infrastructure — ECS Fargate, SQS queues, S3, ECR, auto-scaling |

The production design scales the summarisation stage independently via queue-depth-based auto-scaling. See [`infra/README.md`](infra/README.md) for the full architecture diagram.
