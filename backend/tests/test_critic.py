"""
Tests for the critic agent and narrative review functionality.

These tests verify that the self-correction system properly evaluates
narrative quality, cultural authenticity, and provides actionable feedback.
"""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.adk_agent import (
    review_narrative_quality,
    review_cultural_authenticity,
    suggest_narrative_improvements,
)


class TestReviewNarrativeQuality:
    """Tests for the review_narrative_quality function."""

    @pytest.mark.asyncio
    async def test_valid_narrative_passes(self):
        """A well-structured narrative should pass quality review."""
        segments = [
            {"type": "text", "content": "In the heart of Ghana, where the Ashanti kingdom once flourished, the land speaks of ancient traditions passed down through generations of griots and storytellers.", "trust_level": "historical", "act": 1, "sequence": 0},
            {"type": "image", "media_type": "image/png", "act": 1, "sequence": 1},
            {"type": "text", "content": "The Ashanti people developed one of the most sophisticated civilizations in West Africa, known for their goldwork, kente cloth weaving, and complex political systems that rivaled European kingdoms.", "trust_level": "cultural", "act": 1, "sequence": 2},
            {"type": "text", "content": "During the 1940s, the people of Ghana lived in close-knit communities where extended families shared responsibilities for farming, trading, and raising children according to time-honored customs.", "trust_level": "historical", "act": 2, "sequence": 3},
            {"type": "image", "media_type": "image/png", "act": 2, "sequence": 4},
            {"type": "text", "content": "Cultural practices included elaborate naming ceremonies, harvest festivals that brought entire villages together, and the passing down of oral histories through the evening storytelling traditions.", "trust_level": "cultural", "act": 2, "sequence": 5},
            {"type": "text", "content": "The diaspora thread connects those who remained in Ghana with descendants scattered across the Americas, carrying with them fragments of language, cuisine, and spiritual practices that survived the Middle Passage.", "trust_level": "reconstructed", "act": 3, "sequence": 6},
            {"type": "text", "content": "Today, descendants of the Mensah family continue to honor their ancestors through annual gatherings, traditional naming ceremonies for newborns, and the preservation of family proverbs and stories.", "trust_level": "cultural", "act": 3, "sequence": 7},
        ]
        arc = {
            "act1_setting": {"title": "The Gold Coast", "focus": "landscape"},
            "act2_people": {"title": "Ashanti Traditions", "focus": "culture"},
            "act3_thread": {"title": "Diaspora Connections", "focus": "heritage"},
        }

        result = await review_narrative_quality(
            narrative_segments_json=json.dumps(segments),
            arc_json=json.dumps(arc),
            region="Ghana",
            time_period="1940s",
            family_name="Mensah",
        )

        review = json.loads(result)
        assert review["passed"] is True
        assert review["quality_score"] >= 7
        assert len(review["issues"]) == 0

    @pytest.mark.asyncio
    async def test_sparse_narrative_fails(self):
        """A narrative with too few segments should fail."""
        segments = [
            {"type": "text", "content": "Short text", "trust_level": "reconstructed", "act": 1, "sequence": 0},
            {"type": "text", "content": "Another short", "trust_level": "reconstructed", "act": 2, "sequence": 1},
        ]
        arc = {}

        result = await review_narrative_quality(
            narrative_segments_json=json.dumps(segments),
            arc_json=json.dumps(arc),
            region="Ghana",
            time_period="1940s",
            family_name="Mensah",
        )

        review = json.loads(result)
        assert review["passed"] is False
        assert review["quality_score"] < 7
        assert any("segment" in issue.lower() for issue in review["issues"])

    @pytest.mark.asyncio
    async def test_all_reconstructed_flagged(self):
        """Narrative with only reconstructed segments should be flagged."""
        segments = [
            {"type": "text", "content": "A long reconstructed paragraph about life...", "trust_level": "reconstructed", "act": 1, "sequence": i}
            for i in range(8)
        ]
        arc = {}

        result = await review_narrative_quality(
            narrative_segments_json=json.dumps(segments),
            arc_json=json.dumps(arc),
            region="Ghana",
            time_period="1940s",
            family_name="Mensah",
        )

        review = json.loads(result)
        assert any("reconstructed" in issue.lower() for issue in review["issues"])

    @pytest.mark.asyncio
    async def test_missing_acts_flagged(self):
        """Narrative missing acts should be flagged."""
        segments = [
            {"type": "text", "content": "A paragraph about act 1...", "trust_level": "historical", "act": 1, "sequence": 0},
            {"type": "text", "content": "Another paragraph about act 1...", "trust_level": "cultural", "act": 1, "sequence": 1},
        ]
        arc = {}

        result = await review_narrative_quality(
            narrative_segments_json=json.dumps(segments),
            arc_json=json.dumps(arc),
            region="Ghana",
            time_period="1940s",
            family_name="Mensah",
        )

        review = json.loads(result)
        assert any("act" in issue.lower() for issue in review["issues"])

    @pytest.mark.asyncio
    async def test_invalid_json_handled(self):
        """Invalid JSON should be handled gracefully."""
        result = await review_narrative_quality(
            narrative_segments_json="not valid json",
            arc_json="also not json",
            region="Ghana",
            time_period="1940s",
            family_name="Mensah",
        )

        review = json.loads(result)
        assert review["passed"] is False
        assert review["quality_score"] == 0
        assert any("json" in issue.lower() for issue in review["issues"])


class TestReviewCulturalAuthenticity:
    """Tests for the review_cultural_authenticity function."""

    @pytest.mark.asyncio
    async def test_authenticity_review_returns_valid_json(self):
        """Authenticity review should return valid JSON structure."""
        with patch("app.services.adk_agent.generate_text", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = json.dumps({
                "authenticity_score": 8,
                "historical_accuracy": "accurate",
                "cultural_representation": "authentic",
                "specific_issues": [],
                "recommendations": [],
                "strengths": ["Good use of cultural terminology"]
            })

            result = await review_cultural_authenticity(
                narrative_text="The Mensah family lived in Kumasi...",
                region="Ghana",
                time_period="1940s",
            )

            review = json.loads(result)
            assert "authenticity_score" in review
            assert "historical_accuracy" in review
            assert "cultural_representation" in review

    @pytest.mark.asyncio
    async def test_authenticity_review_handles_errors(self):
        """Errors during review should be handled gracefully."""
        with patch("app.services.adk_agent.generate_text", new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = Exception("API error")

            result = await review_cultural_authenticity(
                narrative_text="Test narrative",
                region="Ghana",
                time_period="1940s",
            )

            review = json.loads(result)
            assert review["authenticity_score"] == 5
            assert "unable to assess" in review["historical_accuracy"]


class TestSuggestNarrativeImprovements:
    """Tests for the suggest_narrative_improvements function."""

    @pytest.mark.asyncio
    async def test_high_scores_approve(self):
        """High quality and authenticity scores should result in approval."""
        quality = {"quality_score": 9, "issues": [], "suggestions": []}
        authenticity = {"authenticity_score": 9, "specific_issues": [], "strengths": ["Excellent"]}
        arc = {}

        result = await suggest_narrative_improvements(
            quality_review_json=json.dumps(quality),
            authenticity_review_json=json.dumps(authenticity),
            arc_json=json.dumps(arc),
        )

        improvements = json.loads(result)
        assert improvements["action"] == "approve"
        assert len(improvements["priority_fixes"]) == 0

    @pytest.mark.asyncio
    async def test_low_scores_regenerate(self):
        """Low scores should recommend regeneration."""
        quality = {"quality_score": 3, "issues": ["Many issues"], "suggestions": []}
        authenticity = {"authenticity_score": 3, "specific_issues": ["Inaccurate"], "strengths": []}
        arc = {}

        result = await suggest_narrative_improvements(
            quality_review_json=json.dumps(quality),
            authenticity_review_json=json.dumps(authenticity),
            arc_json=json.dumps(arc),
        )

        improvements = json.loads(result)
        assert improvements["action"] == "regenerate"
        assert len(improvements["priority_fixes"]) > 0

    @pytest.mark.asyncio
    async def test_medium_scores_revise(self):
        """Medium scores with few issues should recommend revision."""
        quality = {"quality_score": 6.5, "issues": ["Minor issue"], "suggestions": ["Fix X"]}
        authenticity = {"authenticity_score": 7, "specific_issues": [], "strengths": ["Good tone"]}
        arc = {}

        result = await suggest_narrative_improvements(
            quality_review_json=json.dumps(quality),
            authenticity_review_json=json.dumps(authenticity),
            arc_json=json.dumps(arc),
        )

        improvements = json.loads(result)
        assert improvements["action"] in ["approve_with_notes", "revise_specific_acts"]

    @pytest.mark.asyncio
    async def test_invalid_json_handled(self):
        """Invalid JSON input should be handled gracefully."""
        result = await suggest_narrative_improvements(
            quality_review_json="not json",
            authenticity_review_json="also not json",
            arc_json="bad json",
        )

        improvements = json.loads(result)
        assert improvements["action"] == "regenerate"
        assert any("parse" in fix.lower() or "regenerate" in fix.lower()
                   for fix in improvements["priority_fixes"])


class TestCriticAgentIntegration:
    """Integration tests for the critic agent workflow."""

    @pytest.mark.asyncio
    async def test_full_review_workflow(self):
        """Test the complete review workflow with all three functions."""
        # Create a valid narrative
        segments = [
            {"type": "text", "content": f"Paragraph {i} about Ghana and the Mensah family heritage during the 1940s with rich cultural details.",
             "trust_level": ["historical", "cultural", "reconstructed"][i % 3],
             "act": (i // 3) + 1,
             "sequence": i}
            for i in range(9)
        ]
        arc = {
            "act1_setting": {"title": "The Gold Coast", "focus": "landscape"},
            "act2_people": {"title": "Ashanti Traditions", "focus": "culture"},
            "act3_thread": {"title": "Diaspora Connections", "focus": "heritage"},
        }

        # Run quality review
        quality_result = await review_narrative_quality(
            narrative_segments_json=json.dumps(segments),
            arc_json=json.dumps(arc),
            region="Ghana",
            time_period="1940s",
            family_name="Mensah",
        )
        quality = json.loads(quality_result)
        assert "quality_score" in quality

        # Mock authenticity review (requires API call)
        with patch("app.services.adk_agent.generate_text", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = json.dumps({
                "authenticity_score": 8,
                "historical_accuracy": "mostly accurate",
                "cultural_representation": "authentic",
                "specific_issues": [],
                "recommendations": [],
                "strengths": ["Good cultural details"]
            })

            authenticity_result = await review_cultural_authenticity(
                narrative_text=" ".join(s["content"] for s in segments),
                region="Ghana",
                time_period="1940s",
            )
            authenticity = json.loads(authenticity_result)
            assert "authenticity_score" in authenticity

        # Run improvement suggestions
        improvements_result = await suggest_narrative_improvements(
            quality_review_json=quality_result,
            authenticity_review_json=authenticity_result,
            arc_json=json.dumps(arc),
        )
        improvements = json.loads(improvements_result)
        assert "action" in improvements
        assert "overall_quality" in improvements
