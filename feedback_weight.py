
import math
from datetime import datetime

def calculate_feedback_weight(base_weight=1.0, timestamp_str=None, half_life_days=90):
    """
    Calculates the decayed weight of feedback based on its age.
    Formula: weight = base * exp(-days_ago / half_life)
    
    Args:
        base_weight (float): The initial weight (e.g. 1.0 for Like, -1.0 for Dislike).
        timestamp_str (str): Timestamp string (e.g. "2023-10-27 10:00:00").
        half_life_days (int): Days after which the weight becomes ~36% (1/e) of original.
    
    Returns:
        float: Decayed weight.
    """
    if not timestamp_str:
        return base_weight
        
    try:
        # Parse timestamp (Assuming format from feedback_log.json: "%Y-%m-%d %H:%M:%S")
        feedback_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        
        delta = now - feedback_time
        days_ago = delta.days + (delta.seconds / 86400.0)
        
        if days_ago < 0: days_ago = 0
        
        # Exponential Decay
        # If days_ago == 90, result is e^-1 ~= 0.36
        decay_factor = math.exp(-days_ago / half_life_days)
        
        return base_weight * decay_factor
        
    except Exception as e:
        # If parsing fails, return full weight (or 0? Safer to return full to respect recent if error is weird)
        # But let's log it and return base.
        print(f"Warning: Date parse error in feedback decay: {e}")
        return base_weight
