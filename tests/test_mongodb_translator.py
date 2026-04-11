import pytest
from jubapi.querylang.v2.parser import QueryAST
from jubapi.querylang.v2.translator import ASTToMongoTranslator

# ==========================================
# 1. SPATIAL VARIABLE (VS) TESTS
# ==========================================

def test_translate_spatial_single():
    """Test translating a single exact spatial match."""
    ast = QueryAST.parse("jub.v1.VS(MX)")
    mongo_query = ASTToMongoTranslator.translate(ast)
    
    assert mongo_query == {"spatial_id": "MX"}

def test_translate_spatial_or():
    """Test translating multiple spatial locations with OR."""
    ast = QueryAST.parse("jub.v1.VS(MX OR TAM)")
    mongo_query = ASTToMongoTranslator.translate(ast)
    print(mongo_query)
    assert mongo_query == {"spatial_id": {"$in": ["MX", "TAM"]}}


# ==========================================
# 2. TEMPORAL VARIABLE (VT) TESTS
# ==========================================
def test_translate_temporal_exact():
    """Test translating an exact year match."""
    ast = QueryAST.parse("jub.v1.VT(2025)")
    mongo_query = ASTToMongoTranslator.translate(ast)
    
    # Assuming your parser standardized "2025" to "2025-01-01T00:00:00Z"
    assert mongo_query == {"temporal_id": "2025-01-01T00:00:00Z"}

def test_translate_temporal_range():
    """Test translating a date range with greater than and less than."""
    ast = QueryAST.parse("jub.v1.VT(>= 2000 AND <= 2025)")
    mongo_query = ASTToMongoTranslator.translate(ast)
    
    assert "temporal_id" in mongo_query
    assert mongo_query["temporal_id"] == {
        "$gte": "2000-01-01T00:00:00Z",
        "$lte": "2025-01-01T00:00:00Z"
    }


# ==========================================
# 3. INTEREST VARIABLE (VI) TESTS
# ==========================================

def test_translate_interest_single():
    """Test translating a single interest variable."""
    # Assuming the parser splits "SEX.MALE" to catalog_value="SEX", item_path=["MALE"]
    # and the translator formats it to "SEX_MALE"
    ast = QueryAST.parse("jub.v1.VI(SEX.MALE)")
    mongo_query = ASTToMongoTranslator.translate(ast)
    
    assert mongo_query == {"interest_ids": "SEX_MALE"}

def test_translate_interest_and():
    """Test translating multiple interest variables that MUST co-exist (AND)."""
    ast = QueryAST.parse("jub.v1.VI(SEX.MALE AND CIE10.C50)")
    mongo_query = ASTToMongoTranslator.translate(ast)
    
    # AND logic should use the MongoDB $all operator
    assert mongo_query == {"interest_ids": {"$all": ["SEX_MALE", "CIE10_C50"]}}

def test_translate_interest_or():
    """Test translating interest variables where ANY can match (OR)."""
    ast = QueryAST.parse("jub.v1.VI(CIE10.C50 OR CIE10.C51)")
    mongo_query = ASTToMongoTranslator.translate(ast)
    
    # OR logic should use the MongoDB $in operator
    assert mongo_query == {"interest_ids": {"$in": ["CIE10_C50", "CIE10_C51"]}}


# ==========================================
# 4. COMBINED QUERY TEST
# ==========================================

def test_translate_complex_combined_query():
    """Test a full query combining Spatial, Temporal, and Interest variables."""
    query_string = "jub.v1.VS(MX).VT(>= 2020 AND <= 2026).VI(SEX.MALE AND CIE10.C50)"
    ast = QueryAST.parse(query_string)
    mongo_query = ASTToMongoTranslator.translate(ast)
    
    expected_query = {
        "spatial_id": "MX",
        "temporal_id": {
            "$gte": "2020-01-01T00:00:00Z",
            "$lte": "2026-01-01T00:00:00Z"
        },
        "interest_ids": {
            "$all": ["SEX_MALE", "CIE10_C50"]
        }
    }
    
    assert mongo_query == expected_query