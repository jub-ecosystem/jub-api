import re
from typing import List, Union
from pydantic import BaseModel
from enum import Enum

# --- AST Models ---
SPATIAL_VARIABLE    = "VS"
TEMPORAL_VARIABLE   = "VT"
INTEREST_VARIABLE   = "VI"
OBSERVABLE_VARIABLE = "VO"

class ConditionOperators(str, Enum):
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    NOT_EQUAL = "!="
    EQUAL = "="
    WILDCARD = "WILDCARD"
    EXACT = "EXACT"
    
class Condition(BaseModel):
    operator: str
    catalog_value: str
    item_path: Union[str, List[str]] 

class ConditionGroup(BaseModel):
    logic: str  # "AND", "OR", or "SINGLE"
    conditions: List[Condition]

class CatalogQuery(BaseModel):
    catalog_prefix: str  # e.g., "VS", "VT", "VI"
    group: ConditionGroup

class QueryAST(BaseModel):
    version: str
    queries: List[CatalogQuery]

    @staticmethod
    def _standardize_date(date_str: str) -> str:
        """
        Takes a partial date string and pads it to a full ISO-8601 datetime string.
        Defaults missing months to January (01) and missing days to the 1st (01).
        """
        date_str = date_str.strip()
        
        # Match YYYY (e.g., "2020")
        if re.fullmatch(r'\d{4}', date_str):
            return f"{date_str}-01-01T00:00:00Z"
            
        # Match YYYY-MM (e.g., "2020-05")
        elif re.fullmatch(r'\d{4}-\d{2}', date_str):
            return f"{date_str}-01T00:00:00Z"
            
        # Match YYYY-MM-DD (e.g., "2020-05-15")
        elif re.fullmatch(r'\d{4}-\d{2}-\d{2}', date_str):
            return f"{date_str}T00:00:00Z"
            
        # Match full ISO string (return as-is)
        elif "T" in date_str:
            return date_str
            
        # Fallback if they type something completely weird
        return date_str
    
    @staticmethod
    def _parse_single_condition(cond_str: str, prefix: str) -> Condition:
        """Helper to parse an individual condition string."""
        cond_str = cond_str.strip()
        
        # Set default catalog names for standard variables
        if prefix == SPATIAL_VARIABLE:
            default_catalog = "SPATIAL"
        elif prefix == TEMPORAL_VARIABLE:
            default_catalog = "TEMPORAL"
        elif prefix == INTEREST_VARIABLE:
            default_catalog = "INTEREST"
        elif prefix == OBSERVABLE_VARIABLE:
            default_catalog = "OBSERVABLE"
        else: 
            default_catalog = None

        # 1. Check for Full Expressions (e.g., "AGE >= 20" or "CIE10 == 50")
        full_expr_match = re.match(r'^([A-Za-z0-9_]+)\s*(>=|<=|>|<|!=|==|=)\s*(.*)$', cond_str)
        if full_expr_match:
            parsed_catalog = full_expr_match.group(1).strip()
            operator = full_expr_match.group(2)
            raw_val = full_expr_match.group(3).strip()
            
            # Normalize double equals to single equals
            if operator == "==":
                operator = "="
                
            formmated_val = QueryAST._standardize_date(raw_val) if prefix == TEMPORAL_VARIABLE else raw_val
            
            return Condition(
                operator=operator,
                catalog_value=parsed_catalog, # Will be "AGE"
                item_path=[formmated_val]     # Will be ["20"]
            )

        # 2. Check for Prefix Math Operators (e.g., "> 2000" inside VT)
        math_match = re.match(r'^(>=|<=|>|<|!=|==|=)\s*(.*)$', cond_str)
        if math_match:
            operator = math_match.group(1)
            raw_val = math_match.group(2).strip()
            
            if operator == "==":
                operator = "="
                
            formmated_val = QueryAST._standardize_date(raw_val) if prefix == TEMPORAL_VARIABLE else raw_val
            
            return Condition(
                operator=operator,
                catalog_value=default_catalog,
                item_path=[formmated_val]
            )
            
        # 3. Check for Hierarchy Wildcards (e.g., "MX.*" or "*")
        elif '*' in cond_str:
            parts = [p for p in cond_str.split('.') if p != '*']
            if prefix == INTEREST_VARIABLE:
                if len(parts) == 0:
                    return Condition(operator="WILDCARD", catalog_value="*", item_path=[])
                else:
                    return Condition(operator="WILDCARD", catalog_value=parts[0], item_path=parts[1:])
            else:
                return Condition(operator="WILDCARD", catalog_value=default_catalog, item_path=parts)
                
        # 4. Exact match / Hierarchy Path / Root Match (e.g., "CIE10.C10" or "AGE")
        else:
            parts = cond_str.split('.')
            if prefix == TEMPORAL_VARIABLE:
                item_path = [QueryAST._standardize_date(cond_str)]
                return Condition(operator="EXACT", catalog_value=default_catalog, item_path=item_path)
            
            elif prefix == INTEREST_VARIABLE:
                # If query is VI(AGE), parts[0] is "AGE", and parts[1:] is an empty list []
                return Condition(operator="EXACT", catalog_value=parts[0], item_path=parts[1:])
            
            else:
                return Condition(operator="EXACT", catalog_value=default_catalog, item_path=parts)
    @staticmethod
    def parse(query_str: str) -> "QueryAST":
        """
        Parses a complex Jub query string into an AST with AND/OR logic.
        """
        if not query_str.startswith("jub.v1."):
            raise ValueError("Invalid query format. Must start with 'jub.v1.'")
        
        core_query = query_str[7:]
        
        # Match patterns like VS(...) or VT(...)
        pattern = r'([A-Z]{2})\(([^)]+)\)'
        matches = re.findall(pattern, core_query)
        
        parsed_queries = []
        for prefix, argument in matches:
            argument = argument.strip()
            # Determine the logical grouping inside the parentheses
            if ' OR ' in argument:
                logic = "OR"
                raw_conds = argument.split(' OR ')
            elif ' AND ' in argument:
                logic = "AND"
                raw_conds = argument.split(' AND ')
            else:
                logic = "SINGLE"
                raw_conds = [argument]
            # Parse each split condition
            conditions = [QueryAST._parse_single_condition(c, prefix) for c in raw_conds]
            
            # Add the logical group to the query list
            group = ConditionGroup(logic=logic, conditions=conditions)
            parsed_queries.append(CatalogQuery(catalog_prefix=prefix, group=group))
            
        return QueryAST(version="v1", queries=parsed_queries)