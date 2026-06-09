"""CLI entry point - single command to run the full pipeline."""

import asyncio
import json
import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path

import click

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.manager import ConfigManager
from src.orchestrator import Orchestrator

# ─── Logging Setup ────────────────────────────────────────────
logger = logging.getLogger("brightbeam")


def _setup_logging(output_dir: Path):
    """Configure logging to both console and file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    log_file = output_dir / "pipeline.log"

    # File handler — detailed
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))

    # Console handler — concise
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info(f"─── Pipeline started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ───")
    logger.debug(f"Log file: {log_file}")


@click.group()
def cli():
    """BrightBeam Call Summarisation Tool."""
    pass


@cli.command()
@click.option("--input-dir", type=click.Path(exists=True), default=None, help="Directory with transcript files")
@click.option("--input-file", type=click.Path(exists=True), default=None, help="Single transcript file")
@click.option("--output-dir", type=click.Path(), default=None, help="Output directory for summaries")
@click.option("--skip-judge", is_flag=True, help="Skip LLM judge evaluation (faster, less validation)")
@click.option("--resume/--no-resume", default=True, help="Skip already-processed transcripts (default: resume)")
def summarise(input_dir, input_file, output_dir, skip_judge, resume):
    """Generate structured summaries from call transcripts."""
    cfg = ConfigManager.get()

    # Resolve paths
    if input_dir:
        transcript_dir = Path(input_dir)
    elif input_file:
        transcript_dir = None
    else:
        transcript_dir = cfg.test_dir

    out_dir = Path(output_dir) if output_dir else cfg.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # Setup logging
    _setup_logging(out_dir)

    # Collect transcripts
    transcripts: dict[str, str] = {}
    if transcript_dir:
        for f in sorted(transcript_dir.glob("*-transcript.txt")):
            tid = f.stem.replace("-transcript", "")
            transcripts[tid] = f.read_text(encoding="utf-8")
    elif input_file:
        f = Path(input_file)
        tid = f.stem.replace("-transcript", "")
        transcripts[tid] = f.read_text(encoding="utf-8")

    if not transcripts:
        logger.error("No transcripts found. Check --input-dir or --input-file path.")
        return

    # Resume: skip already-completed transcripts
    if resume:
        already_done = {f.stem.replace("-summary", "") for f in out_dir.glob("*-summary.txt")}
        skipped = set(transcripts.keys()) & already_done
        if skipped:
            logger.info(f"Resuming: skipping {len(skipped)} already-processed transcript(s): {sorted(skipped)}")
            transcripts = {k: v for k, v in transcripts.items() if k not in already_done}

    if not transcripts:
        logger.info("All transcripts already processed. Use --no-resume to reprocess.")
        return

    logger.info(f"Processing {len(transcripts)} transcript(s)...")

    # Validate API key
    if not cfg.openrouter_api_key:
        logger.error("OPENROUTER_API_KEY not set in .env file")
        return

    # Initialize orchestrator
    orchestrator = Orchestrator()
    logger.debug(f"LLM model: {cfg.summarisation_model.get('model')}")
    logger.debug(f"Judge model: {cfg.judge_model.get('model')}")

    # Run pipeline with incremental saving
    asyncio.run(_process_all_incremental(orchestrator, transcripts, out_dir))


async def _process_all_incremental(orchestrator: Orchestrator, transcripts: dict[str, str], out_dir: Path):
    """Process transcripts one by one, saving each immediately to disk."""
    results = []
    failed = []
    total = len(transcripts)

    for i, (tid, text) in enumerate(transcripts.items(), 1):
        logger.info(f"  [{i}/{total}] Processing {tid}...")

        try:
            result = await orchestrator.process_transcript(tid, text)

            # ─── SAVE IMMEDIATELY ─────────────────────────────
            summary_path = out_dir / f"{tid}-summary.txt"
            summary_path.write_text(result.rendered or result.summary.render(), encoding="utf-8")

            # Save individual result JSON
            result_json_path = out_dir / f"{tid}-result.json"
            result_json_path.write_text(
                json.dumps(result.model_dump(mode="json"), indent=2), encoding="utf-8"
            )

            results.append(result)

            status = "!! REVIEW" if result.needs_human_review else "PASS"
            logger.info(
                f"  [{i}/{total}] {tid}: category={result.category} "
                f"confidence={result.confidence:.2f} attempts={result.attempts} {status}"
            )
            logger.debug(f"  Saved: {summary_path}")

        except Exception as e:
            failed.append(tid)
            logger.error(f"  [{i}/{total}] {tid}: FAILED - {type(e).__name__}: {e}")
            logger.debug(f"  Traceback:\n{traceback.format_exc()}")
            # Continue to next transcript — don't lose progress
            continue

    # Write combined results.json (for dashboard) from all successful results
    if results:
        results_json = out_dir / "results.json"
        results_data = [r.model_dump(mode="json") for r in results]

        # Merge with any existing results (from resumed runs)
        if results_json.exists():
            existing = json.loads(results_json.read_text())
            existing_ids = {r["transcript_id"] for r in existing}
            for r in results_data:
                if r["transcript_id"] not in existing_ids:
                    existing.append(r)
            results_data = existing

        results_json.write_text(json.dumps(results_data, indent=2), encoding="utf-8")

    # Summary
    logger.info("")
    logger.info(f"─── Pipeline Complete ───")
    logger.info(f"  Processed: {len(results)}/{total}")
    logger.info(f"  Failed: {len(failed)}/{total}" + (f" ({failed})" if failed else ""))
    logger.info(f"  Output: {out_dir}/")
    if failed:
        logger.info(f"  To retry failed: run again with --resume (default)")


@cli.command("process-folder")
@click.argument("folder", type=click.Path(exists=True))
@click.option("--output-dir", type=click.Path(), default=None, help="Output directory for summaries")
@click.option("--pattern", default="*.txt", help="Glob pattern for transcript files (default: *.txt)")
@click.option("--skip-judge", is_flag=True, help="Skip LLM judge evaluation (faster, less validation)")
@click.option("--resume/--no-resume", default=True, help="Skip already-processed transcripts (default: resume)")
def process_folder(folder, output_dir, pattern, skip_judge, resume):
    """Process all transcript files in FOLDER."""
    cfg = ConfigManager.get()

    folder_path = Path(folder)
    out_dir = Path(output_dir) if output_dir else cfg.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    _setup_logging(out_dir)

    # Collect all matching files as transcripts
    transcripts: dict[str, str] = {}
    for f in sorted(folder_path.glob(pattern)):
        if f.is_file():
            tid = f.stem.replace("-transcript", "")
            transcripts[tid] = f.read_text(encoding="utf-8")

    if not transcripts:
        logger.error(f"No files matching '{pattern}' found in {folder_path}")
        return

    # Resume: skip already-completed transcripts
    if resume:
        already_done = {f.stem.replace("-summary", "") for f in out_dir.glob("*-summary.txt")}
        skipped = set(transcripts.keys()) & already_done
        if skipped:
            logger.info(f"Resuming: skipping {len(skipped)} already-processed transcript(s): {sorted(skipped)}")
            transcripts = {k: v for k, v in transcripts.items() if k not in already_done}

    if not transcripts:
        logger.info("All transcripts already processed. Use --no-resume to reprocess.")
        return

    logger.info(f"Processing {len(transcripts)} transcript(s) from {folder_path}...")

    if not cfg.openrouter_api_key:
        logger.error("OPENROUTER_API_KEY not set in .env file")
        return

    orchestrator = Orchestrator()
    if skip_judge:
        orchestrator.judge_llm = None

    asyncio.run(_process_all_incremental(orchestrator, transcripts, out_dir))


@cli.command()
@click.option("--output-dir", type=click.Path(), default=None, help="Directory with results.json")
def dashboard(output_dir):
    """Generate HTML dashboard from results."""
    cfg = ConfigManager.get()
    out_dir = Path(output_dir) if output_dir else cfg.output_dir

    results_path = out_dir / "results.json"
    if not results_path.exists():
        click.echo("No results.json found. Run 'summarise' first.")
        return

    from src.dashboard.generator import generate_dashboard

    html_path = generate_dashboard(results_path, out_dir)
    click.echo(f"Dashboard generated: {html_path}")


@cli.command()
def discover_clusters():
    """Build cluster centroids from training examples."""
    from src.scripts.discover_clusters import build_centroids

    cfg = ConfigManager.get()
    build_centroids(cfg)
    click.echo("Centroids built and saved.")


if __name__ == "__main__":
    cli()
