from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_THRESHOLDS = {"low": 20, "suspicious": 50, "high": 75}


def _load_json(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _level_for(score: int, thresholds: dict) -> str:
    low = int(thresholds.get("low", 20))
    susp = int(thresholds.get("suspicious", 50))
    high = int(thresholds.get("high", 75))
    if score >= high:
        return "critical"
    if score >= susp:
        return "high"
    if score >= low:
        return "suspicious"
    return "low"


@dataclass
class Finding:
    package: str
    score: int
    level: str
    reasons: list[dict] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    system: bool = False

    def to_dict(self) -> dict:
        return {
            "package": self.package,
            "score": self.score,
            "level": self.level,
            "reasons": self.reasons,
            "permissions": self.permissions,
            "labels": self.labels,
            "flags": self.flags,
            "system": self.system,
        }


class ThreatEngine:
    """Heuristic + signature scoring. Explainable, no black box."""

    def __init__(
        self,
        rules_dir: str | Path | None = None,
        thresholds: dict | None = None,
    ) -> None:
        base = Path(rules_dir) if rules_dir else Path(__file__).resolve().parent.parent / "rules"
        self.heuristics = _load_json(base / "heuristics.json")
        self.signatures = _load_json(base / "signatures.json")
        self.thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
        self.permission_weights: dict[str, int] = dict(
            self.heuristics.get("permission_weights") or {}
        )
        self.flag_weights: dict[str, int] = dict(self.heuristics.get("flag_weights") or {})
        self.cap = int(self.heuristics.get("cap", 100))
        self.min_finding = int(self.heuristics.get("min_finding_score", 15))
        self.dangerous_count_weight = int(self.heuristics.get("dangerous_count_weight", 3))
        self.system_factor = float(self.heuristics.get("system_score_factor", 0.4))

    def evaluate(
        self,
        apps: list[dict] | None = None,
        permissions: list[dict] | None = None,
        services: dict | None = None,
    ) -> dict[str, Any]:
        apps = apps or []
        permissions = permissions or []
        services = services or {}

        apps_by_pkg = {a.get("package"): a for a in apps if a.get("package")}
        findings: list[Finding] = []

        for row in permissions:
            package = row.get("package") or ""
            if not package:
                continue
            app = apps_by_pkg.get(package, {})
            system = bool(app.get("system") or row.get("system"))
            reasons: list[dict] = []
            score = 0

            dangerous = list(row.get("dangerous") or [])
            labels = list(row.get("labels") or [])
            for perm in dangerous:
                weight = int(self.permission_weights.get(perm, 5))
                score += weight
                reasons.append(
                    {
                        "code": "permission",
                        "weight": weight,
                        "detail": perm.rsplit(".", 1)[-1],
                    }
                )

            extra = len(dangerous) * self.dangerous_count_weight
            if extra:
                score += extra
                reasons.append(
                    {
                        "code": "dangerous_count",
                        "weight": extra,
                        "detail": f"{len(dangerous)} dangerous permissions",
                    }
                )

            flags: list[str] = []
            if row.get("overlay"):
                flags.append("overlay")
                w = int(self.flag_weights.get("overlay", 8))
                score += w
                reasons.append({"code": "overlay", "weight": w, "detail": "draw over other apps"})
            if row.get("accessibility"):
                flags.append("accessibility")
                w = int(self.flag_weights.get("accessibility", 10))
                score += w
                reasons.append(
                    {"code": "accessibility", "weight": w, "detail": "accessibility service enabled"}
                )

            sig_hits = self._signature_score(package, app)
            for hit in sig_hits:
                score += int(hit["score"])
                reasons.append(
                    {
                        "code": "signature",
                        "weight": int(hit["score"]),
                        "detail": hit["title"],
                        "id": hit.get("id"),
                    }
                )

            if system and score:
                before = score
                score = int(score * self.system_factor)
                reasons.append(
                    {
                        "code": "system_discount",
                        "weight": score - before,
                        "detail": f"system app ×{self.system_factor}",
                    }
                )

            score = max(0, min(self.cap, score))
            if score < self.min_finding and not sig_hits:
                continue

            findings.append(
                Finding(
                    package=package,
                    score=score,
                    level=_level_for(score, self.thresholds),
                    reasons=reasons,
                    permissions=dangerous,
                    labels=labels,
                    flags=flags,
                    system=system,
                )
            )

        findings.sort(key=lambda f: (-f.score, f.package))
        risk_score = findings[0].score if findings else 0
        threat_count = sum(1 for f in findings if f.score >= self.min_finding)

        overlay_apps = list(services.get("overlay_apps") or [])
        a11y_apps = list(services.get("accessibility_services") or [])

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "risk_score": risk_score,
            "risk_level": _level_for(risk_score, self.thresholds),
            "threat_count": threat_count,
            "thresholds": dict(self.thresholds),
            "findings": [f.to_dict() for f in findings],
            "services": {
                "overlay_apps": overlay_apps,
                "accessibility_services": a11y_apps,
            },
            "apps_evaluated": len(permissions),
        }

    def _signature_score(self, package: str, app: dict) -> list[dict]:
        hits: list[dict] = []
        known = self.signatures.get("known_packages") or []
        for entry in known:
            if str(entry.get("package", "")).lower() == package.lower():
                hits.append(
                    {
                        "id": entry.get("id"),
                        "score": int(entry.get("score", 50)),
                        "title": entry.get("title") or "Known bad package",
                    }
                )

        for entry in self.signatures.get("package_patterns") or []:
            pattern = entry.get("regex")
            if not pattern:
                continue
            try:
                if re.search(pattern, package):
                    hits.append(
                        {
                            "id": entry.get("id"),
                            "score": int(entry.get("score", 40)),
                            "title": entry.get("title") or "Package pattern match",
                        }
                    )
            except re.error:
                continue

        installer = str(app.get("installer") or "").lower()
        system = bool(app.get("system"))
        for rule in self.signatures.get("installer_rules") or []:
            if rule.get("apply_to_system") is False and system:
                continue
            allowed = [str(x).lower() for x in (rule.get("installers") or [])]
            if installer in allowed:
                hits.append(
                    {
                        "id": rule.get("id"),
                        "score": int(rule.get("score", 20)),
                        "title": rule.get("title") or "Installer rule",
                    }
                )

        return hits
