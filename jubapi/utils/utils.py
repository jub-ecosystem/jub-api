# from ast import List
from typing import List, Dict, Any

import datetime as DT
class Utils:
    @staticmethod
    def check_string(x:str,low:int = 8, high:int = 32):
        s_len = len(x)
        return x.isalnum() and (s_len >=low and s_len <=high)
    
    @staticmethod
    def from_string_any_to_string_to_string_dict(d:Dict[str, Any]) -> Dict[str, str]:
        return {k:str(v) for k,v in d.items()}
    @staticmethod
    def from_string_to_datetime(date_str):
        return DT.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    
    @staticmethod
    def format_for_echarts(mongo_results: List[Dict[str, Any]], chart_type: str = "line") -> Dict[str, Any]:
        """Transforms MongoDB aggregation results into a ready-to-use ECharts option object."""

        _EMPTY = {
            "tooltip": {"trigger": "axis"},
            "legend": {"data": []},
            "xAxis": {"type": "category", "data": []},
            "yAxis": {"type": "value"},
            "series": []
        }

        if not mongo_results:
            return _EMPTY

        # Global metric: no BY() clause → _id is None
        if len(mongo_results) == 1 and mongo_results[0].get("_id") is None:
            val = mongo_results[0].get("metric_value", 0)
            return {
                "tooltip": {"trigger": "item"},
                "legend": {"data": ["Total"]},
                "xAxis": {"type": "category", "data": ["Total"]},
                "yAxis": {"type": "value"},
                "series": [{
                    "name": "Total",
                    "type": "bar",
                    "data": [val],
                    "itemStyle": {"borderRadius": [4, 4, 0, 0]}
                }]
            }

        # BY() results — each row has _id: {x_axis: <label>, hue?: <label>}
        # Collect x_axis values; skip rows with missing/None _id
        valid = [r for r in mongo_results if isinstance(r.get("_id"), dict) and r["_id"].get("x_axis") is not None]
        if not valid:
            return _EMPTY

        x_axis_set = sorted({str(r["_id"]["x_axis"]) for r in valid})

        series_dict: Dict[str, Dict[str, Any]] = {}
        for row in valid:
            _id       = row["_id"]
            x_val     = str(_id["x_axis"])
            hue_val   = _id.get("hue")
            series_nm = str(hue_val) if hue_val is not None else "Total"
            y_val     = row.get("metric_value", 0)

            if series_nm not in series_dict:
                series_dict[series_nm] = {x: 0 for x in x_axis_set}
            series_dict[series_nm][x_val] = y_val

        series_array = [
            {
                "name": nm,
                "type": chart_type,
                "data": [pts[x] for x in x_axis_set],
                "smooth": chart_type == "line",
            }
            for nm, pts in series_dict.items()
        ]

        return {
            "tooltip": {"trigger": "axis"},
            "legend": {"data": list(series_dict.keys())},
            "xAxis": {"type": "category", "data": x_axis_set},
            "yAxis": {"type": "value"},
            "series": series_array,
        }