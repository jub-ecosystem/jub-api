import datetime as DT
class Utils:
    @staticmethod
    def check_string(x:str,low:int = 8, high:int = 32):
        s_len = len(x)
        return x.isalnum() and (s_len >=low and s_len <=high)
    
    @staticmethod
    def from_string_to_datetime(date_str):
        return DT.datetime.fromisoformat(date_str.replace("Z", "+00:00"))