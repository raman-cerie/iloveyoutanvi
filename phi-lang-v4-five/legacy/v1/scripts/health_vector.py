"""φ-lang v3 — Health Vector Engine
Each node emits a health vector: {metric: value}. 
Classifier assigns weights → overall score → s7/s2/s6 tag.
Zero LLM. Pure arithmetic with configurable weights.
"""

import json, os

class HealthVector:
    """A node's health snapshot as a weighted vector."""
    
    # Default weights — tunable per node in ~/.hermes/phi_weights.json
    WEIGHTS = {
        "load": 0.35,
        "mem_pct": 0.25,
        "disk_pct": 0.20,
        "beacon_miss": 0.10,
        "cert_days": 0.07,
        "git_changes": 0.03,
    }
    
    # Per-metric tag thresholds
    THRESHOLDS = {
        "load":        {"s7": 3.0,  "s2": 7.0},   # 1m load avg
        "mem_pct":     {"s7": 60.0, "s2": 80.0},   # % used
        "disk_pct":    {"s7": 70.0, "s2": 85.0},   # % used
        "beacon_miss": {"s7": 0,    "s2": 2},      # consecutive
        "cert_days":   {"s7": 30.0, "s2": 7.0},    # days remaining (inverted: s2 if below, not above)
        "git_changes": {"s7": 0,    "s2": 5},       # uncommitted files
    }
    
    # Inverted metrics: lower = worse (not lower = better)
    INVERTED = {"cert_days"}
    
    def __init__(self, node_id: str, metrics: dict):
        self.node_id = node_id
        self.metrics = metrics
        self._load_weights()
    
    def _load_weights(self):
        """Load per-node weight overrides from ~/.hermes/phi_weights.json"""
        path = os.path.expanduser("~/.hermes/phi_weights.json")
        try:
            with open(path) as f:
                overrides = json.load(f).get(self.node_id, {})
                self.WEIGHTS.update(overrides)
        except:
            pass
    
    def classify_metric(self, metric: str, value: float) -> str:
        """Classify single metric → s7/s2/s6."""
        t = self.THRESHOLDS.get(metric)
        if not t:
            return "s7"
        
        if metric in self.INVERTED:
            if value >= t["s7"]:
                return "s7"
            elif value >= t["s2"]:
                return "s2"
            return "s6"
        else:
            if value <= t["s7"]:
                return "s7"
            elif value <= t["s2"]:
                return "s2"
            return "s6"
    
    def score_metric(self, metric: str, value: float) -> float:
        """Score a metric 0.0-1.0 (0=perfect, 1=critical)."""
        t = self.THRESHOLDS.get(metric)
        if not t:
            return 0.0
        
        s7 = t["s7"]
        s2 = t["s2"]
        
        if metric in self.INVERTED:
            # cert_days: 30+=0.0, 7=0.5, 0=1.0
            if value >= s7:
                return 0.0
            if value <= 0:
                return 1.0
            # Linear between s7 (0.0) and 0 (1.0)
            return max(0.0, min(1.0, (s7 - value) / s7))
        else:
            if value <= s7:
                return 0.0
            if value >= s2:
                return min(1.0, value / s2 * 0.5 + 0.5 if value > s2 * 2 else value / s2)
            # Linear between s7 (0.0) and s2 (0.5)
            return (value - s7) / (s2 - s7) * 0.5
    
    def compute(self) -> dict:
        """Compute the full health vector + scores + overall tag.
        
        Returns:
            {
                "node": "a0",
                "overall_score": 0.23,    # 0-1, weighted
                "overall_tag": "s2",      # worst across metrics or weighted
                "telegram": False,        # should TG alert fire?
                "metrics": {
                    "load": {"value": 8.83, "tag": "s6", "score": 0.63},
                    "mem_pct": {"value": 23.0, "tag": "s7", "score": 0.0},
                    ...
                }
            }
        """
        result = {
            "node": self.node_id,
            "metrics": {},
            "overall_score": 0.0,
            "overall_tag": "s7",
            "telegram": False
        }
        
        total_weight = 0.0
        worst_tag = "s7"
        tag_rank = {"s7": 0, "s2": 1, "s6": 2}
        
        for metric, raw_value in self.metrics.items():
            if metric not in self.THRESHOLDS:
                continue
            
            try:
                value = float(raw_value)
            except:
                continue
            
            tag = self.classify_metric(metric, value)
            score = self.score_metric(metric, value)
            weight = self.WEIGHTS.get(metric, 0.1)
            
            result["metrics"][metric] = {
                "value": value,
                "tag": tag,
                "score": round(score, 3),
                "weight": weight
            }
            
            result["overall_score"] += score * weight
            total_weight += weight
            
            if tag_rank[tag] > tag_rank[worst_tag]:
                worst_tag = tag
        
        # Normalize overall score
        if total_weight > 0:
            result["overall_score"] = round(result["overall_score"] / total_weight, 3)
        
        # Overall tag: weighted score > 0.5 = s6, > 0.2 = s2, else s7
        # But also: if ANY metric is s6, overall is at least s2
        score = result["overall_score"]
        if score > 0.5 or worst_tag == "s6":
            result["overall_tag"] = "s6"
        elif score > 0.2 or worst_tag == "s2":
            result["overall_tag"] = "s2"
        else:
            result["overall_tag"] = "s7"
        
        result["telegram"] = result["overall_tag"] == "s6"
        
        return result
    
    def phi_summary(self) -> str:
        """φ-code summary string for bus/beacon."""
        v = self.compute()
        metrics_str = ",".join(
            f"{m}={d['value']}={d['tag']}" 
            for m, d in v["metrics"].items()
        )
        return f"φn={self.node_id},score={v['overall_score']},{v['overall_tag']},{metrics_str}"
