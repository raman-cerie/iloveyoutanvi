"""φ-lang v3 — Tag Classification Engine
Determines s7/s2/s6 tags based on defined thresholds.
Called by cloud_chat and guard daemons.
Zero LLM — pure arithmetic comparison.
"""

class Classifier:
    """Three-tier classification: stable (s7), warning (s2), critical (s6)."""
    
    THRESHOLDS = {
        # load (1m avg from uptime)
        "load":       {"s7_max": 3.0,  "s2_max": 7.0},
        # memory usage percentage
        "mem_pct":    {"s7_max": 60.0, "s2_max": 80.0},
        # disk usage percentage  
        "disk_pct":   {"s7_max": 70.0, "s2_max": 85.0},
        # CPU temperature (Celsius, macOS only)
        "cpu_temp":   {"s7_max": 70.0, "s2_max": 85.0},
        # beacon misses (consecutive)
        "beacon_miss": {"s7_max": 0,    "s2_max": 2},
        # SSL cert days remaining
        "cert_days":  {"s7_min": 30.0, "s2_min": 7.0},
        # git uncommitted changes count
        "git_changes": {"s7_max": 0,    "s2_max": 5},
    }

    @classmethod
    def classify(cls, metric: str, value: float, lower_is_better: bool = True) -> str:
        """Classify a metric value into s7/s2/s6.
        
        Args:
            metric: key from THRESHOLDS
            value: current value
            lower_is_better: True for load/mem (lower=better), False for cert_days (higher=better)
        
        Returns:
            's7' = stable, 's2' = warning, 's6' = critical
        """
        thresholds = cls.THRESHOLDS.get(metric)
        if not thresholds:
            return "s7"

        if lower_is_better:
            s7_thresh = thresholds.get("s7_max", float("inf"))
            s2_thresh = thresholds.get("s2_max", float("inf"))
            
            if value <= s7_thresh:
                return "s7"
            elif value <= s2_thresh:
                return "s2"
            else:
                return "s6"
        else:
            s7_thresh = thresholds.get("s7_min", 0)
            s2_thresh = thresholds.get("s2_min", 0)
            
            if value >= s7_thresh:
                return "s7"
            elif value >= s2_thresh:
                return "s2"
            else:
                return "s6"

    @classmethod
    def should_alert_telegram(cls, tags: dict) -> bool:
        """Check if any metric warrants a Telegram alert.
        
        Args:
            tags: dict of {metric_name: tag} e.g. {"load": "s6", "mem_pct": "s7"}
        
        Returns:
            True if ANY metric is s6 (critical)
        """
        return any(tag == "s6" for tag in tags.values())

    @classmethod
    def assess(cls, stats: dict) -> tuple:
        """Full assessment of a node's health.
        
        Args:
            stats: dict of {metric_name: value}
                   e.g. {"load": 2.1, "mem_pct": 45, "disk_pct": 43}
        
        Returns:
            (overall_tag, alerts_dict, tg_needed)
            overall_tag: s7/s2/s6 — worst tag across all metrics
            alerts_dict: {metric: tag} for each metric
            tg_needed: True if Telegram alert should fire
        """
        alerts = {}
        is_inverted = {"cert_days"}  # higher = better
        
        for metric, value in stats.items():
            if metric not in cls.THRESHOLDS:
                continue
            lower_better = metric not in is_inverted
            tag = cls.classify(metric, float(value), lower_better)
            alerts[metric] = tag

        # Overall = worst tag
        if "s6" in alerts.values():
            overall = "s6"
        elif "s2" in alerts.values():
            overall = "s2"
        else:
            overall = "s7"

        tg_needed = cls.should_alert_telegram(alerts)
        return overall, alerts, tg_needed
