from jubapi.querylang.v2.parser import QueryAST, ConditionGroup,SPATIAL_VARIABLE, TEMPORAL_VARIABLE, INTEREST_VARIABLE, OBSERVABLE_VARIABLE
from typing import Dict, Any
from jubapi.utils import Utils

class ASTToMongoTranslator:
    """
    Translates a parsed Jub QueryAST into a MongoDB query dictionary
    specifically designed for the DataRecordX schema.
    """
    
    # Map your DSL operators to MongoDB operators
    MONGO_OPS = {
        ">": "$gt",
        "<": "$lt",
        ">=": "$gte",
        "<=": "$lte",
        "!=": "$ne",
        "=": "$eq"
    }

    @classmethod
    def translate(cls, ast: 'QueryAST') -> Dict[str, Any]:
        mongo_query = {}
        
        for query in ast.queries:
            prefix = query.catalog_prefix
            group = query.group
            
            if prefix == SPATIAL_VARIABLE:
                mongo_query.update(cls._build_spatial(group))
            elif prefix == TEMPORAL_VARIABLE:
                mongo_query.update(cls._build_temporal(group))
            elif prefix == INTEREST_VARIABLE:
                mongo_query.update(cls._build_interest(group))
                
        return mongo_query

    @classmethod
    def _format_id(cls, catalog_value: str, item_path: list) -> str:
        """
        Helper to reconstruct the database ID.
        Example: catalog="CIE10", item_path=["II", "C", "50"] -> "CIE10_II_C_50"
        (Adjust this to match exactly how you store interest_ids in DataRecordX)
        """
        if not item_path:
            return catalog_value
        path_str = "_".join(item_path)
        return f"{catalog_value}_{path_str}"

    @classmethod
    def _build_spatial(cls, group: 'ConditionGroup') -> dict:
        """Handles VS(...) - Maps to spatial_id"""
        
        # 1. Trap the impossible logic to prevent returning {}
        if group.logic == "AND":
            raise ValueError(
                "Logical AND is not allowed in Spatial (VS) variables. "
                "A record can only have one location. Did you mean OR?"
            )
            
        # 2. Handle SINGLE logic (Exact and Wildcard)
        if group.logic == "SINGLE":
            cond = group.conditions[0]
            
            if cond.operator == "EXACT":
                raw_val = cond.item_path[0] if isinstance(cond.item_path, list) else cond.item_path
                return {"spatial_id": raw_val}
                
            elif cond.operator == "WILDCARD":
                # If it's a global wildcard VS(*), apply no filter
                if not cond.item_path or len(cond.item_path) == 0:
                    return {} 
                    
                # If it's VS(MX.*), match "MX" exactly OR anything starting with "MX_"
                root_val = cond.item_path[0]
                return {"spatial_id": {"$regex": f"^{root_val}$|^{root_val}_"}}

        # 3. Handle OR logic (Can mix Exact and Wildcards!)
        elif group.logic == "OR":
            exact_ids = []
            regex_patterns = []
            
            for cond in group.conditions:
                if cond.operator == "EXACT":
                    val = cond.item_path[0] if isinstance(cond.item_path, list) else cond.item_path
                    exact_ids.append(val)
                    
                elif cond.operator == "WILDCARD":
                    if not cond.item_path or len(cond.item_path) == 0:
                        # If a global wildcard is in an OR group e.g., VS(MX OR *), it cancels all filters
                        return {}
                    root_val = cond.item_path[0]
                    regex_patterns.append(f"^{root_val}$|^{root_val}_")
            
            # Build the MongoDB $or array
            or_conditions = []
            if exact_ids:
                or_conditions.append({"spatial_id": {"$in": exact_ids}})
            for pattern in regex_patterns:
                or_conditions.append({"spatial_id": {"$regex": pattern}})
                
            if len(or_conditions) == 1:
                return or_conditions[0]
            elif len(or_conditions) > 1:
                return {"$or": or_conditions}
            
        return {}

    @classmethod
    def _build_temporal(cls, group: 'ConditionGroup') -> dict:
        """Handles VT(...) - Maps to temporal_id"""
        
        # 1. Handle OR logic for exact dates (e.g., VT(2025 OR 2026))
        if group.logic == "OR":
            exact_dates = []
            for cond in group.conditions:
                if cond.operator == "EXACT":
                    # Extract single value safely
                    raw_val = cond.item_path[0] if isinstance(cond.item_path, list) else cond.item_path
                    exact_dates.append(Utils.from_string_to_datetime(raw_val))
            if exact_dates:
                return {"temporal_id": {"$in": exact_dates}}

        # 2. Handle SINGLE and AND logic (Ranges like >= 2020 AND <= 2025)
        temporal_query = {}
        
        for cond in group.conditions:
            # Extract the raw value safely whether the parser gave us a list or string
            raw_val = cond.item_path[0] if isinstance(cond.item_path, list) else cond.item_path
            
            # Parse it to a native datetime object for MongoDB
            parsed_date = Utils.from_string_to_datetime(raw_val)

            if cond.operator in cls.MONGO_OPS:
                mongo_op = cls.MONGO_OPS[cond.operator]
                temporal_query[mongo_op] = parsed_date
                
            elif cond.operator == "EXACT":
                # If it's a single exact match, return the parsed date directly
                return {"temporal_id": parsed_date}
                
        # 3. Return the accumulated range query, or empty dict if nothing matched
        return {"temporal_id": temporal_query} if temporal_query else {}
    @classmethod
    def _build_interest(cls, group: 'ConditionGroup') -> dict:
        """Handles VI(...) - Maps to the interest_ids array"""
        ids = [cls._format_id(c.catalog_value, c.item_path) for c in group.conditions]
        
        if group.logic == "SINGLE":
            return {"interest_ids": ids[0]}
            
        elif group.logic == "AND":
            # Must contain ALL specified interests
            # e.g., VI(MALE AND CIE10.C50) -> {"$all": ["SEX_MALE", "CIE10_C50"]}
            return {"interest_ids": {"$all": ids}}
            
        elif group.logic == "OR":
            # Must contain ANY of the specified interests
            return {"interest_ids": {"$in": ids}}
            
        return {}