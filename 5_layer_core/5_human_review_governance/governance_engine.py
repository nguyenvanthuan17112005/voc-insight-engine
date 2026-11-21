"""Layer 5: Human Review, Report Approval & Internal Action Governance (INS 05 - INS 08, B 05 - B 06)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

VALID_REPORT_STATES = {"draft", "under_review", "approved", "rejected", "superseded"}
VALID_ACTION_DECISIONS = {"proposed", "accepted", "deferred", "rejected", "implemented", "outcome_reviewed"}


class GovernanceEngine:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.corrections_path = self.output_dir / "reviewer_corrections.jsonl"
        self.registry_path = self.output_dir / "report_registry.json"
        self.actions_path = self.output_dir / "action_register.json"

    def _load_json(self, path: Path, default: Any) -> Any:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return default

    def _save_json(self, path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def register_report(self, bundle_path: Path) -> Dict[str, Any]:
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        registry: Dict[str, Any] = self._load_json(self.registry_path, {"reports": {}})
        report_id = bundle["report_id"]
        entry = {
            "report_id": report_id,
            "snapshot_id": bundle["snapshot_id"],
            "policy_version": bundle.get("policy_version", "policy-v1.0.0"),
            "status": "draft",
            "named_owner": None,
            "decision_reason": "",
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "history": [{"status": "draft", "at": datetime.now().isoformat(timespec="seconds")}],
        }
        registry["reports"][report_id] = entry
        self._save_json(self.registry_path, registry)
        return entry

    def transition_report(
        self, report_id: str, new_status: str, named_owner: str, reason: str = ""
    ) -> Dict[str, Any]:
        if new_status not in VALID_REPORT_STATES:
            raise ValueError(f"Invalid report status: {new_status}")
        if new_status == "approved" and not named_owner.strip():
            raise ValueError("Named owner is required for report approval (INS 05).")
        registry = self._load_json(self.registry_path, {"reports": {}})
        if report_id not in registry["reports"]:
            raise KeyError(f"Unknown report_id: {report_id}")

        entry = registry["reports"][report_id]
        now_iso = datetime.now().isoformat(timespec="seconds")
        entry["status"] = new_status
        entry["named_owner"] = named_owner
        entry["decision_reason"] = reason
        entry["updated_at"] = now_iso
        entry["history"].append(
            {"status": new_status, "owner": named_owner, "reason": reason, "at": now_iso}
        )
        self._save_json(self.registry_path, registry)
        return entry

    def supersede_on_dependency_change(self, reason: str) -> List[str]:
        """Invalidate approved/under_review reports when source data or labels change (DAT 08, INS 05)."""
        registry = self._load_json(self.registry_path, {"reports": {}})
        superseded: List[str] = []
        now_iso = datetime.now().isoformat(timespec="seconds")
        for rpt_id, entry in registry["reports"].items():
            if entry["status"] in {"approved", "under_review"}:
                entry["status"] = "superseded"
                entry["decision_reason"] = reason
                entry["updated_at"] = now_iso
                entry["history"].append(
                    {"status": "superseded", "reason": reason, "at": now_iso}
                )
                superseded.append(rpt_id)
        self._save_json(self.registry_path, registry)
        return superseded

    def record_label_correction(
        self,
        record_id: str,
        reviewer: str,
        old_theme: str,
        new_theme: str,
        old_sentiment: str,
        new_sentiment: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Log human label correction with provenance without auto-retraining (INS 08)."""
        if not reason.strip():
            raise ValueError("Correction reason is mandatory (INS 08).")
        correction = {
            "record_id": record_id,
            "reviewer": reviewer,
            "old_theme": old_theme,
            "new_theme": new_theme,
            "old_sentiment": old_sentiment,
            "new_sentiment": new_sentiment,
            "reason": reason,
            "label_stage": "reviewed",
            "auto_retrain_blocked": True,
            "corrected_at": datetime.now().isoformat(timespec="seconds"),
        }
        with self.corrections_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(correction, ensure_ascii=False) + "\n")
        self.supersede_on_dependency_change(
            f"Label correction on {record_id} by {reviewer}: {reason}"
        )
        return correction

    def propose_action(
        self,
        action_id: str,
        theme_id: str,
        title: str,
        evidence_record_ids: List[str],
        owner: str,
        review_date: str,
    ) -> Dict[str, Any]:
        """Register an internal improvement action proposal (INS 06, INS 07)."""
        register = self._load_json(self.actions_path, {"actions": {}})
        now_iso = datetime.now().isoformat(timespec="seconds")
        action = {
            "action_id": action_id,
            "theme_id": theme_id,
            "title": title,
            "evidence_record_ids": evidence_record_ids,
            "owner": owner,
            "review_date": review_date,
            "status": "proposed",
            "internal_only": True,
            "external_customer_messaging": False,
            "outcome_evidence": "",
            "updated_at": now_iso,
        }
        register["actions"][action_id] = action
        self._save_json(self.actions_path, register)
        return action

    def update_action_status(
        self, action_id: str, new_status: str, outcome_evidence: str = ""
    ) -> Dict[str, Any]:
        if new_status not in VALID_ACTION_DECISIONS:
            raise ValueError(f"Invalid action status: {new_status}")
        register = self._load_json(self.actions_path, {"actions": {}})
        if action_id not in register["actions"]:
            raise KeyError(f"Unknown action_id: {action_id}")
        action = register["actions"][action_id]
        if new_status == "outcome_reviewed" and not outcome_evidence.strip():
            raise ValueError("Outcome review requires owner evidence (INS 07).")
        action["status"] = new_status
        if outcome_evidence:
            action["outcome_evidence"] = outcome_evidence
        action["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self._save_json(self.actions_path, register)
        return action


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Layer 5 Governance Engine")
    parser.add_argument("--report-bundle", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--owner", default="VoC_Lead_SongNhat")
    args = parser.parse_args()

    gov = GovernanceEngine(args.output_dir)
    entry = gov.register_report(args.report_bundle)
    gov.transition_report(entry["report_id"], "under_review", args.owner, "Initial review")
    print(json.dumps(entry, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
