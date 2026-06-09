"""Orchestrator: coordinates the full summarisation pipeline."""

from src.config.manager import ConfigManager
from src.models.clustering import ClusterAssignment
from src.models.features import ExtractedFeatures, SentimentProfile
from src.models.validation import SummaryResult
from src.services.clustering.category_store import compute_domain_signals
from src.services.clustering.cluster_service import ClusterService
from src.services.feature_extraction.keyword_extractor import extract_keywords_rake
from src.services.feature_extraction.ner_extractor import extract_entities_regex
from src.services.feature_extraction.sentiment_extractor import extract_sentiment
from src.services.summarisation.base import BaseLLMProvider
from src.services.summarisation.prompt_registry import get_prompt, get_retry_prompt
from src.services.validation.factual_validator import validate_facts
from src.services.validation.quality_scorer import evaluate_quality
from src.services.validation.structural_validator import validate_structure
from src.models.summary import CallSummary


class Orchestrator:
    """Coordinates the full pipeline: extract -> cluster -> summarise -> validate."""

    def __init__(self, llm: BaseLLMProvider | None = None, judge_llm: BaseLLMProvider | None = None):
        self.cfg = ConfigManager.get()

        # Use provided LLMs or create from config (singleton model swap)
        self.llm = llm or self.cfg.create_llm("summarisation")
        self.judge_llm = judge_llm or self.cfg.create_llm("judge")
        self.cluster_service = ClusterService(self.cfg.centroids_path)

    def extract_features(self, transcript_id: str, transcript: str) -> ExtractedFeatures:
        """Step 1: Extract features using traditional ML."""
        keywords = extract_keywords_rake(transcript)
        entities = extract_entities_regex(transcript)
        overall, per_speaker = extract_sentiment(transcript)
        domain_signals = compute_domain_signals(transcript)

        sentiment = SentimentProfile(
            overall=overall,
            per_speaker=per_speaker,
        )

        return ExtractedFeatures(
            transcript_id=transcript_id,
            keywords=keywords,
            entities=entities,
            sentiment=sentiment,
            domain_signals=domain_signals,
        )

    def classify(self, features: ExtractedFeatures) -> ClusterAssignment:
        """Step 2: Assign category based on features."""
        if self.cluster_service.centroids:
            vector = list(features.domain_signals.values())
            return self.cluster_service.assign(features.transcript_id, vector)
        else:
            if features.domain_signals:
                best_category = max(features.domain_signals, key=features.domain_signals.get)
                confidence = features.domain_signals[best_category]
            else:
                best_category = "general_enquiry"
                confidence = 0.5

            return ClusterAssignment(
                transcript_id=features.transcript_id,
                category=best_category,
                confidence=confidence,
            )

    async def summarise(self, transcript: str, category: str) -> str:
        """Step 3: Generate summary using LLM with category-specific prompt."""
        system_prompt, user_prompt = get_prompt(category, transcript)
        return await self.llm.generate(user_prompt, system_prompt)

    async def validate_and_retry(
        self,
        transcript_id: str,
        transcript: str,
        summary_text: str,
        features: ExtractedFeatures,
        category: str,
    ) -> SummaryResult:
        """Steps 4-5: Validate and retry if needed."""
        best_summary_text = summary_text
        attempts = 1
        factual = None
        quality = None

        for attempt in range(self.cfg.max_retries + 1):
            # Layer 2: Factual check
            factual = validate_facts(
                transcript_id,
                features.entities,
                best_summary_text,
            )

            # Layer 3: LLM judge
            entity_texts = [e.text for e in features.entities]
            quality = await evaluate_quality(
                transcript_id, transcript, best_summary_text, entity_texts, self.judge_llm
            )

            # Check if passing
            if quality.overall_score >= self.cfg.pass_threshold and factual.factual_score >= 0.8:
                break

            # Retry with feedback if not last attempt
            if attempt < self.cfg.max_retries:
                feedback = self._build_feedback(factual, quality)
                system_prompt, user_prompt = get_retry_prompt(transcript, best_summary_text, feedback)
                best_summary_text = await self.llm.generate(user_prompt, system_prompt)
                attempts += 1

        # Parse into structured model
        summary_model = self._parse_summary(best_summary_text)
        structural_valid, structural_issues = validate_structure(summary_model)

        return SummaryResult(
            transcript_id=transcript_id,
            category=category,
            summary=summary_model,
            rendered=best_summary_text,
            structural_valid=structural_valid,
            factual_check=factual,
            quality_score=quality,
            attempts=attempts,
            needs_human_review=quality.overall_score < self.cfg.pass_threshold if quality else True,
        )

    async def process_transcript(self, transcript_id: str, transcript: str) -> SummaryResult:
        """Full pipeline: extract -> cluster -> summarise -> validate."""
        features = self.extract_features(transcript_id, transcript)
        cluster = self.classify(features)
        summary_text = await self.summarise(transcript, cluster.category)
        result = await self.validate_and_retry(
            transcript_id, transcript, summary_text, features, cluster.category
        )
        return result

    def _build_feedback(self, factual, quality) -> str:
        """Build correction instructions from validation results."""
        lines = []

        if factual and factual.hallucinated_entities:
            lines.append("HALLUCINATED FACTS (not found in transcript):")
            for e in factual.hallucinated_entities:
                lines.append(f"  - {e.label}: '{e.text}' -- remove or correct this")

        if factual and factual.missing_critical_entities:
            lines.append("MISSING CRITICAL DETAILS (found in transcript but not in summary):")
            for e in factual.missing_critical_entities:
                lines.append(f"  - {e.label}: '{e.text}' -- include this")

        if quality and quality.issues_found:
            lines.append("QUALITY ISSUES:")
            for issue in quality.issues_found:
                lines.append(f"  - [{issue.severity.upper()}] {issue.description}")
                if issue.suggestion:
                    lines.append(f"    Fix: {issue.suggestion}")

        return "\n".join(lines) if lines else "Minor quality issues. Improve clarity and conciseness."

    def _parse_summary(self, text: str) -> CallSummary:
        """Parse raw LLM output text into a structured CallSummary model."""
        from src.services.summarisation.parser import parse_summary_text
        return parse_summary_text(text)
