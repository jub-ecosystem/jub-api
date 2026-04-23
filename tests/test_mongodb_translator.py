"""
Unit tests for ASTToMongoTranslator.

The translator returns a MongoDB aggregation pipeline (list of stage dicts).
Filter conditions live in pipeline[0]["$match"].
"""

import pytest
from jubapi.querylang.v2.parser import QueryAST
from jubapi.querylang.v2.translator import ASTToMongoTranslator
from jubapi.utils import Utils


def match(dsl: str) -> dict:
    """Parse DSL and return the $match stage dict."""
    pipeline = ASTToMongoTranslator.translate(QueryAST.parse(dsl))
    assert isinstance(pipeline, list), "translate() must return a list"
    assert pipeline, "Pipeline must not be empty"
    assert "$match" in pipeline[0], f"First stage must be $match, got: {list(pipeline[0].keys())}"
    return pipeline[0]["$match"]


# ==========================================
# 1. SPATIAL VARIABLE (VS) TESTS
# ==========================================

def test_translate_spatial_single():
    result = match("jub.v1.VS(MX)")
    assert result == {"spatial_id": "MX"}


def test_translate_spatial_or():
    result = match("jub.v1.VS(MX OR TAM)")
    assert result == {"spatial_id": {"$in": ["MX", "TAM"]}}


def test_translate_spatial_and_raises():
    """AND logic inside VS is semantically impossible and must raise ValueError."""
    ast = QueryAST.parse("jub.v1.VS(MX AND TAM)")
    with pytest.raises(ValueError, match="AND is not allowed in Spatial"):
        ASTToMongoTranslator.translate(ast)


# ==========================================
# 2. TEMPORAL VARIABLE (VT) TESTS
# ==========================================

def test_translate_temporal_exact():
    result = match("jub.v1.VT(2025)")
    expected = Utils.from_string_to_datetime("2025-01-01T00:00:00Z")
    assert result == {"temporal_id": expected}


def test_translate_temporal_range():
    result = match("jub.v1.VT(>= 2000 AND <= 2025)")
    assert "temporal_id" in result
    assert result["temporal_id"] == {
        "$gte": Utils.from_string_to_datetime("2000-01-01T00:00:00Z"),
        "$lte": Utils.from_string_to_datetime("2025-01-01T00:00:00Z"),
    }


def test_translate_temporal_greater_than():
    result = match("jub.v1.VT(> 2020)")
    assert result["temporal_id"] == {"$gt": Utils.from_string_to_datetime("2020-01-01T00:00:00Z")}


def test_translate_temporal_or_exact():
    result = match("jub.v1.VT(2024 OR 2025)")
    assert result == {
        "temporal_id": {
            "$in": [
                Utils.from_string_to_datetime("2024-01-01T00:00:00Z"),
                Utils.from_string_to_datetime("2025-01-01T00:00:00Z"),
            ]
        }
    }


# ==========================================
# 3. INTEREST VARIABLE (VI) TESTS
# ==========================================

def test_translate_interest_single():
    result = match("jub.v1.VI(SEX.MALE)")
    assert result == {"interest_ids": "SEX_MALE"}


def test_translate_interest_and():
    result = match("jub.v1.VI(SEX.MALE AND CIE10.C50)")
    assert result == {"interest_ids": {"$all": ["SEX_MALE", "CIE10_C50"]}}


def test_translate_interest_or():
    result = match("jub.v1.VI(CIE10.C50 OR CIE10.C51)")
    assert result == {"interest_ids": {"$in": ["CIE10_C50", "CIE10_C51"]}}


# ==========================================
# 4. PIPELINE STRUCTURE TESTS
# ==========================================

def test_pipeline_always_has_group_stage():
    """The pipeline must always end with a $group stage."""
    pipeline = ASTToMongoTranslator.translate(QueryAST.parse("jub.v1.VS(MX)"))
    stage_keys = [list(s.keys())[0] for s in pipeline]
    assert "$group" in stage_keys


def test_pipeline_no_match_when_no_filter():
    """A query with only VO() and BY() should not add a $match stage."""
    pipeline = ASTToMongoTranslator.translate(QueryAST.parse("jub.v1.VO(COUNT).BY(TEMPORAL)"))
    has_match = any("$match" in stage for stage in pipeline)
    assert not has_match, "No filters → no $match stage expected"


def test_observable_sum():
    pipeline = ASTToMongoTranslator.translate(QueryAST.parse("jub.v1.VO(SUM(AGE))"))
    group_stage = next(s["$group"] for s in pipeline if "$group" in s)
    assert group_stage["metric_value"] == {"$sum": "$numerical_interest_ids.AGE"}


def test_observable_avg():
    pipeline = ASTToMongoTranslator.translate(QueryAST.parse("jub.v1.VO(AVG(COST))"))
    group_stage = next(s["$group"] for s in pipeline if "$group" in s)
    assert group_stage["metric_value"] == {"$avg": "$numerical_interest_ids.COST"}


def test_grouping_by_temporal():
    pipeline = ASTToMongoTranslator.translate(QueryAST.parse("jub.v1.BY(TEMPORAL)"))
    group_stage = next(s["$group"] for s in pipeline if "$group" in s)
    assert group_stage["_id"]["x_axis"] == "$temporal_id"


def test_grouping_by_spatial():
    pipeline = ASTToMongoTranslator.translate(QueryAST.parse("jub.v1.BY(SPATIAL)"))
    group_stage = next(s["$group"] for s in pipeline if "$group" in s)
    assert group_stage["_id"]["x_axis"] == "$spatial_id"


# ==========================================
# 5. COMBINED QUERY TESTS
# ==========================================

def test_translate_complex_combined_query():
    query_string = "jub.v1.VS(MX).VT(>= 2020 AND <= 2026).VI(SEX.MALE AND CIE10.C50)"
    result = match(query_string)
    assert result == {
        "spatial_id": "MX",
        "temporal_id": {
            "$gte": Utils.from_string_to_datetime("2020-01-01T00:00:00Z"),
            "$lte": Utils.from_string_to_datetime("2026-01-01T00:00:00Z"),
        },
        "interest_ids": {"$all": ["SEX_MALE", "CIE10_C50"]},
    }


def test_translate_spatial_and_temporal_combined():
    result = match("jub.v1.VS(TAM).VT(2025)")
    assert result == {
        "spatial_id": "TAM",
        "temporal_id": Utils.from_string_to_datetime("2025-01-01T00:00:00Z"),
    }
