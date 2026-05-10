#!/usr/bin/env python3
"""
Phase 9 自動実行スクリプト
本番運用・継続的監視
単一ファイル、依存性ゼロで実行可能

実装内容:
  - HealthChecker        : 定期ヘルスチェック（API 死活・予算残・エージェント応答）
  - AnomalyDetector      : z-score ベースの統計的異常検知
  - AlertRouter          : 重要度別チャンネル振り分け・スロットリング・重複抑制
  - SLATracker           : p50/p95/p99 レイテンシ・稼働率・正解率
  - AuditTrail           : SHA-256 hash chain による改竄検知付き監査ログ
  - OperationsDashboard  : 全指標を集約したスナップショット
"""

import hashlib
import json
import math
import statistics
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple


# ============================================================================
# Phase 9A: HealthChecker
# ============================================================================

@dataclass
class HealthResult:
    name:      str
    status:    str            # "ok" / "degraded" / "down"
    detail:    str
    measured:  float = 0.0    # 数値メトリクス（任意）
    threshold: float = 0.0
    checked_at: str = field(default_factory=lambda: datetime.now().isoformat())


class HealthChecker:
    """
    システム健全性の定期チェック。
    各 check は (status, detail, measured) を返す callable。
    """

    def __init__(self):
        self.checks: Dict[str, Tuple[Callable, float]] = {}
        self.last_results: List[HealthResult] = []

    def register(self, name: str, fn: Callable[[], Tuple[str, str, float]],
                 threshold: float = 0.0):
        self.checks[name] = (fn, threshold)

    def run_all(self) -> List[HealthResult]:
        results: List[HealthResult] = []
        for name, (fn, thr) in self.checks.items():
            try:
                status, detail, measured = fn()
            except Exception as e:
                status, detail, measured = "down", f"exception: {e}", 0.0
            results.append(HealthResult(
                name=name, status=status, detail=detail,
                measured=float(measured), threshold=float(thr),
            ))
        self.last_results = results
        return results

    def overall_status(self) -> str:
        if not self.last_results:
            return "unknown"
        statuses = [r.status for r in self.last_results]
        if "down" in statuses:     return "down"
        if "degraded" in statuses: return "degraded"
        return "healthy"

    def summary(self) -> Dict:
        counts = {"ok": 0, "degraded": 0, "down": 0}
        for r in self.last_results:
            counts[r.status] = counts.get(r.status, 0) + 1
        return {
            "overall":    self.overall_status(),
            "counts":     counts,
            "total":      len(self.last_results),
            "last_run":   self.last_results[0].checked_at
                          if self.last_results else None,
        }


# ============================================================================
# Phase 9B: AnomalyDetector
# ============================================================================

@dataclass
class MetricPoint:
    name:      str
    value:     float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Anomaly:
    metric:    str
    value:     float
    z_score:   float
    baseline_mean: float
    baseline_std:  float
    timestamp: str


class AnomalyDetector:
    """
    z-score (>= 2.0) ベースの統計的異常検知。
    最低 5 サンプルを基準に、ローリング平均・標準偏差で異常判定。
    """

    Z_THRESHOLD       = 2.0
    MIN_BASELINE_SIZE = 5

    def __init__(self):
        self.points: Dict[str, List[MetricPoint]] = {}

    def record(self, name: str, value: float,
               timestamp: Optional[str] = None) -> MetricPoint:
        ts = timestamp or datetime.now().isoformat()
        pt = MetricPoint(name=name, value=float(value), timestamp=ts)
        self.points.setdefault(name, []).append(pt)
        return pt

    def detect(self, name: str) -> List[Anomaly]:
        series = self.points.get(name, [])
        if len(series) < self.MIN_BASELINE_SIZE + 1:
            return []
        values    = [p.value for p in series]
        anomalies: List[Anomaly] = []
        # 各点を「それまでの履歴」に対して評価（オンライン検出）
        for i in range(self.MIN_BASELINE_SIZE, len(values)):
            baseline = values[:i]
            mu       = statistics.mean(baseline)
            sigma    = statistics.pstdev(baseline) or 1e-9
            z        = (values[i] - mu) / sigma
            if abs(z) >= self.Z_THRESHOLD:
                anomalies.append(Anomaly(
                    metric=name, value=values[i],
                    z_score=round(z, 2),
                    baseline_mean=round(mu, 3),
                    baseline_std=round(sigma, 3),
                    timestamp=series[i].timestamp,
                ))
        return anomalies

    def detect_all(self) -> Dict[str, List[Anomaly]]:
        return {name: self.detect(name) for name in self.points.keys()}


# ============================================================================
# Phase 9C: AlertRouter
# ============================================================================

ALERT_SEVERITIES = ("P0", "P1", "P2", "P3")


@dataclass
class AlertRecord:
    alert_id:   str
    severity:   str
    channel:    str            # "line" / "log" / "suppressed"
    message:    str
    dedup_key:  str
    sent_at:    float          # epoch seconds（テストでの時間制御のため float）
    suppressed_reason: str = ""


class AlertRouter:
    """
    重要度別ルーティング:
      - P0/P1 → LINE 即時
      - P2    → ログのみ（LINE には出さない）
      - P3    → ダイジェスト想定（個別通知しない）
    重複抑制: 同一 dedup_key は cooldown 秒以内なら抑制。
    """

    SEVERITY_TO_CHANNEL = {
        "P0": "line", "P1": "line",
        "P2": "log",  "P3": "log",
    }
    DEFAULT_COOLDOWN_S = 300.0   # 5 分

    def __init__(self, cooldown_s: float = DEFAULT_COOLDOWN_S):
        self.cooldown_s = cooldown_s
        self.records:    List[AlertRecord]    = []
        self._last_seen: Dict[str, float]     = {}    # dedup_key → epoch

    def route(self, severity: str, message: str, dedup_key: str = "",
              now: Optional[float] = None) -> AlertRecord:
        if severity not in ALERT_SEVERITIES:
            severity = "P2"
        ts        = now if now is not None else time.time()
        dedup_key = dedup_key or f"_auto_{len(self.records)}"
        channel   = self.SEVERITY_TO_CHANNEL[severity]
        suppressed_reason = ""

        # 重複抑制
        last = self._last_seen.get(dedup_key, 0.0)
        if last and (ts - last) < self.cooldown_s:
            channel           = "suppressed"
            suppressed_reason = (
                f"cooldown {self.cooldown_s:.0f}s, last={ts - last:.1f}s ago"
            )
        else:
            self._last_seen[dedup_key] = ts

        rec = AlertRecord(
            alert_id=f"ALR-{uuid.uuid4().hex[:6].upper()}",
            severity=severity, channel=channel, message=message,
            dedup_key=dedup_key, sent_at=ts,
            suppressed_reason=suppressed_reason,
        )
        self.records.append(rec)
        return rec

    def stats(self) -> Dict:
        by_channel: Dict[str, int]  = {}
        by_sev:     Dict[str, int]  = {}
        suppressed = 0
        for r in self.records:
            by_channel[r.channel] = by_channel.get(r.channel, 0) + 1
            by_sev[r.severity]    = by_sev.get(r.severity, 0) + 1
            if r.channel == "suppressed":
                suppressed += 1
        return {
            "total":      len(self.records),
            "by_channel": by_channel,
            "by_severity": by_sev,
            "suppressed": suppressed,
        }


# ============================================================================
# Phase 9D: SLATracker
# ============================================================================

@dataclass
class SLASample:
    latency_ms: int
    success:    bool
    timestamp:  str = field(default_factory=lambda: datetime.now().isoformat())


class SLATracker:
    """
    SLA 指標 — レイテンシ p50/p95/p99、稼働率、正解率。
    """

    def __init__(self, target_p95_ms: int = 3000,
                 target_uptime_pct: float = 99.0):
        self.target_p95_ms     = target_p95_ms
        self.target_uptime_pct = target_uptime_pct
        self.samples: List[SLASample] = []

    def record(self, latency_ms: int, success: bool = True) -> SLASample:
        s = SLASample(latency_ms=int(latency_ms), success=bool(success))
        self.samples.append(s)
        return s

    def percentile(self, p: float) -> float:
        if not self.samples:
            return 0.0
        values = sorted(s.latency_ms for s in self.samples)
        # 線形補間版（NIST 推奨に近い）
        k = (len(values) - 1) * p
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return float(values[int(k)])
        d0 = values[f] * (c - k)
        d1 = values[c] * (k - f)
        return round(d0 + d1, 2)

    def p50(self) -> float: return self.percentile(0.50)
    def p95(self) -> float: return self.percentile(0.95)
    def p99(self) -> float: return self.percentile(0.99)

    def uptime_pct(self) -> float:
        if not self.samples:
            return 100.0
        ok = sum(1 for s in self.samples if s.success)
        return round(ok / len(self.samples) * 100, 2)

    def is_breaching(self) -> Dict:
        return {
            "p95_breach":    self.p95() > self.target_p95_ms,
            "uptime_breach": self.uptime_pct() < self.target_uptime_pct,
            "p95_actual":    self.p95(),
            "uptime_actual": self.uptime_pct(),
        }


# ============================================================================
# Phase 9E: AuditTrail (hash-chained, tamper-evident)
# ============================================================================

GENESIS_HASH = "0" * 64


@dataclass
class AuditEntry:
    seq:        int
    actor:      str            # 例: "strategist", "human:owner"
    action:     str            # 例: "decision_logged", "override", "budget_consumed"
    payload:    Dict[str, Any]
    timestamp:  str
    prev_hash:  str
    entry_hash: str


class AuditTrail:
    """
    改竄検知付き append-only ログ。
    各エントリは前エントリのハッシュを含み、SHA-256 でチェーンを構成する。
    verify() で全チェーンの整合性を検証可能。
    """

    def __init__(self):
        self.entries: List[AuditEntry] = []

    def append(self, actor: str, action: str,
               payload: Optional[Dict] = None) -> AuditEntry:
        prev = self.entries[-1].entry_hash if self.entries else GENESIS_HASH
        seq  = len(self.entries) + 1
        ts   = datetime.now().isoformat()
        body = {
            "seq": seq, "actor": actor, "action": action,
            "payload": payload or {}, "timestamp": ts, "prev_hash": prev,
        }
        h = self._hash(body)
        entry = AuditEntry(
            seq=seq, actor=actor, action=action,
            payload=payload or {}, timestamp=ts,
            prev_hash=prev, entry_hash=h,
        )
        self.entries.append(entry)
        return entry

    def verify(self) -> Tuple[bool, List[str]]:
        """全エントリのハッシュ整合性を検証。改竄を検出する。"""
        issues: List[str] = []
        prev_hash = GENESIS_HASH
        for e in self.entries:
            if e.prev_hash != prev_hash:
                issues.append(f"seq={e.seq}: prev_hash mismatch")
            body = {
                "seq": e.seq, "actor": e.actor, "action": e.action,
                "payload": e.payload, "timestamp": e.timestamp,
                "prev_hash": e.prev_hash,
            }
            recomputed = self._hash(body)
            if recomputed != e.entry_hash:
                issues.append(f"seq={e.seq}: entry_hash mismatch (tampered)")
            prev_hash = e.entry_hash
        return len(issues) == 0, issues

    def query(self, actor: Optional[str] = None,
              action: Optional[str] = None) -> List[AuditEntry]:
        items = self.entries
        if actor:  items = [e for e in items if e.actor  == actor]
        if action: items = [e for e in items if e.action == action]
        return items

    @staticmethod
    def _hash(body: Dict) -> str:
        data = json.dumps(body, sort_keys=True,
                          ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(data).hexdigest()


# ============================================================================
# Phase 9F: OperationsDashboard
# ============================================================================

class OperationsDashboard:
    """全 Phase 9 コンポーネントを集約したスナップショット"""

    def __init__(
        self,
        health:   HealthChecker,
        anomaly:  AnomalyDetector,
        alerts:   AlertRouter,
        sla:      SLATracker,
        audit:    AuditTrail,
    ):
        self.health  = health
        self.anomaly = anomaly
        self.alerts  = alerts
        self.sla     = sla
        self.audit   = audit

    def snapshot(self) -> Dict:
        anomaly_counts = {
            n: len(items) for n, items in self.anomaly.detect_all().items()
        }
        audit_ok, audit_issues = self.audit.verify()
        return {
            "generated_at": datetime.now().isoformat(),
            "health":   self.health.summary(),
            "anomaly":  {
                "metrics_tracked": list(self.anomaly.points.keys()),
                "anomalies":       anomaly_counts,
                "total":           sum(anomaly_counts.values()),
            },
            "alerts":   self.alerts.stats(),
            "sla":      {
                "p50_ms":     self.sla.p50(),
                "p95_ms":     self.sla.p95(),
                "p99_ms":     self.sla.p99(),
                "uptime_pct": self.sla.uptime_pct(),
                "breach":     self.sla.is_breaching(),
            },
            "audit":    {
                "entries":   len(self.audit.entries),
                "verified":  audit_ok,
                "issues":    audit_issues,
            },
        }

    def to_json(self) -> str:
        return json.dumps(self.snapshot(), ensure_ascii=False, indent=2)


# ============================================================================
# テスト実行
# ============================================================================

def run_tests():
    passed = 0
    failed = 0
    errors: List[str] = []

    def check(name: str, condition: bool, detail: str = ""):
        nonlocal passed, failed
        if condition:
            print(f"  ✅ {name}")
            passed += 1
        else:
            print(f"  ❌ {name}" + (f"\n     {detail}" if detail else ""))
            failed += 1
            errors.append(name)

    print("=" * 80)
    print("🚀 Phase 9 統合テスト実行（本番運用・継続的監視）")
    print("=" * 80)

    # ------------------------------------------------------------------
    # テスト 1-5: HealthChecker
    # ------------------------------------------------------------------
    print("\n📋 テスト 1-5: HealthChecker")

    health = HealthChecker()

    # 仮想チェック: 予算残・API レイテンシ・エージェント応答
    health.register("budget_remaining", lambda: ("ok",       "1660 円残", 1660.0),
                    threshold=600.0)
    health.register("api_latency_ms",   lambda: ("degraded", "p95=2500ms", 2500.0),
                    threshold=2000.0)
    health.register("agent_responsive", lambda: ("ok",       "3/3 応答",   3.0),
                    threshold=3.0)
    # わざと例外を起こすチェック
    def boom():
        raise RuntimeError("DB unreachable")
    health.register("audit_db", boom, threshold=1.0)

    results = health.run_all()
    check("テスト 1: 4 チェック実行 → 4 結果",
          len(results) == 4)

    statuses = [r.status for r in results]
    check("テスト 2: 例外チェックは status='down'",
          "down" in statuses, f"got {statuses}")
    check("テスト 3: degraded を含むため overall='down'（down 優先）",
          health.overall_status() == "down",
          f"got {health.overall_status()}")

    # 例外チェックを取り除いて再実行
    health.checks.pop("audit_db")
    health.run_all()
    check("テスト 4: 例外を除外後 → overall='degraded'",
          health.overall_status() == "degraded",
          f"got {health.overall_status()}")

    s = health.summary()
    check("テスト 5: summary — total=3, counts.ok>=2",
          s["total"] == 3 and s["counts"]["ok"] >= 2, f"got {s}")

    # ------------------------------------------------------------------
    # テスト 6-10: AnomalyDetector
    # ------------------------------------------------------------------
    print("\n📋 テスト 6-10: AnomalyDetector")

    detector = AnomalyDetector()

    # ベースライン: 1 時間あたりコスト 0.5 円前後で安定
    for v in [0.5, 0.6, 0.4, 0.55, 0.45, 0.52]:
        detector.record("hourly_cost_jpy", v)

    # サンプル不足では検知されない
    check("テスト 6: 6 サンプル中 5 がベースライン → 異常 0 件（安定）",
          len(detector.detect("hourly_cost_jpy")) == 0)

    # 急増スパイク
    detector.record("hourly_cost_jpy", 5.0)   # 平常値の ~10 倍
    anomalies = detector.detect("hourly_cost_jpy")
    check("テスト 7: コスト急増 → 異常検知（1 件）",
          len(anomalies) == 1, f"got {len(anomalies)}")
    check("テスト 8: z-score >= 2.0",
          anomalies and abs(anomalies[0].z_score) >= 2.0,
          f"z={anomalies[0].z_score if anomalies else None}")

    # 別メトリクス: 判定数 / 時間
    for v in [10, 12, 11, 9, 13, 10, 11]:
        detector.record("decisions_per_hour", v)
    no_anomalies = detector.detect("decisions_per_hour")
    check("テスト 9: 安定メトリクスは異常 0 件",
          len(no_anomalies) == 0)

    all_results = detector.detect_all()
    check("テスト 10: detect_all で 2 メトリクスとも返る",
          set(all_results.keys()) == {"hourly_cost_jpy", "decisions_per_hour"})

    # ------------------------------------------------------------------
    # テスト 11-15: AlertRouter
    # ------------------------------------------------------------------
    print("\n📋 テスト 11-15: AlertRouter")

    router = AlertRouter(cooldown_s=300.0)
    t0 = 1_000_000.0

    a1 = router.route("P0", "予算 80% 突破", dedup_key="budget_80", now=t0)
    a2 = router.route("P2", "ライブラリ更新通知", dedup_key="lib_update", now=t0)
    a3 = router.route("P3", "日次サマリ",         dedup_key="daily",   now=t0)

    check("テスト 11: P0 → channel='line'",
          a1.channel == "line", f"got {a1.channel}")
    check("テスト 12: P2 → channel='log'（LINE 通知しない）",
          a2.channel == "log",  f"got {a2.channel}")
    check("テスト 13: P3 → channel='log'（ダイジェスト想定）",
          a3.channel == "log",  f"got {a3.channel}")

    # 同 dedup_key を 60 秒後に再送 → 抑制
    a4 = router.route("P0", "予算 80% 突破（再送）",
                      dedup_key="budget_80", now=t0 + 60)
    check("テスト 14: cooldown 内 → channel='suppressed'",
          a4.channel == "suppressed",
          f"got {a4.channel}, reason={a4.suppressed_reason}")

    # cooldown 後（301 秒経過） → 再送許可
    a5 = router.route("P0", "予算 80% 突破（時間経過後）",
                      dedup_key="budget_80", now=t0 + 301)
    check("テスト 15: cooldown 経過後 → channel='line' に復帰",
          a5.channel == "line", f"got {a5.channel}")

    # ------------------------------------------------------------------
    # テスト 16-21: SLATracker
    # ------------------------------------------------------------------
    print("\n📋 テスト 16-21: SLATracker")

    sla = SLATracker(target_p95_ms=3000, target_uptime_pct=99.0)

    # 50 サンプル: 大半 1000ms前後、その上に 5 件の遅延 + 1 件の失敗
    for ms in [800, 900, 1000, 1100, 1200, 950, 1050, 1150, 980, 1020] * 5:
        sla.record(ms, success=True)
    for spike in [4000, 4500, 5000, 4200, 4800]:
        sla.record(spike, success=True)
    sla.record(0, success=False)     # 失敗

    check("テスト 16: 56 サンプル記録",
          len(sla.samples) == 56)

    p50 = sla.p50()
    check("テスト 17: p50 が中央付近（800–1200ms）",
          800 <= p50 <= 1200, f"got {p50}")

    p95 = sla.p95()
    check("テスト 18: p95 がスパイク影響を反映（>= 1500ms）",
          p95 >= 1500, f"got {p95}")

    uptime = sla.uptime_pct()
    expected_uptime = round(55 / 56 * 100, 2)   # ~98.21
    check("テスト 19: 稼働率 = 55/56 ≈ 98.21%",
          abs(uptime - expected_uptime) < 0.05, f"got {uptime}")

    breach = sla.is_breaching()
    check("テスト 20: 稼働率 98.21% < 99% → uptime_breach=True",
          breach["uptime_breach"] is True,
          f"got {breach}")

    # 空 tracker
    empty = SLATracker()
    check("テスト 21: 空 tracker — p50=0, uptime=100",
          empty.p50() == 0.0 and empty.uptime_pct() == 100.0)

    # ------------------------------------------------------------------
    # テスト 22-26: AuditTrail
    # ------------------------------------------------------------------
    print("\n📋 テスト 22-26: AuditTrail")

    audit = AuditTrail()
    e1 = audit.append("strategist", "decision_logged",
                      {"task": "RAR-S 検証", "level": "A_HARD_STOP"})
    e2 = audit.append("human:owner", "override",
                      {"decision_id": e1.payload.get("id", "DEC-X"),
                       "from": "C_AUTO", "to": "B_LIGHT"})
    e3 = audit.append("operator", "decision_logged",
                      {"task": "クレーム文言判定", "level": "B_LIGHT"})

    check("テスト 22: 3 エントリ追加 → seq 1,2,3",
          [e.seq for e in audit.entries] == [1, 2, 3])

    check("テスト 23: 各エントリの prev_hash がチェーン構成",
          e1.prev_hash == GENESIS_HASH
          and e2.prev_hash == e1.entry_hash
          and e3.prev_hash == e2.entry_hash)

    ok, issues = audit.verify()
    check("テスト 24: 改竄なし → verify=True",
          ok and not issues, f"issues={issues}")

    # 改竄してみる
    audit.entries[1].payload["to"] = "A_HARD_STOP"   # 不正書き換え
    bad_ok, bad_issues = audit.verify()
    check("テスト 25: payload 改竄を検知 → verify=False",
          not bad_ok and any("tampered" in i for i in bad_issues),
          f"issues={bad_issues}")

    # 改竄を元に戻して query を確認
    audit.entries[1].payload["to"] = "B_LIGHT"
    overrides = audit.query(action="override")
    check("テスト 26: action='override' で 1 件抽出",
          len(overrides) == 1, f"got {len(overrides)}")

    # ------------------------------------------------------------------
    # テスト 27-30: OperationsDashboard
    # ------------------------------------------------------------------
    print("\n📋 テスト 27-30: OperationsDashboard")

    dashboard = OperationsDashboard(health, detector, router, sla, audit)
    snap = dashboard.snapshot()

    check("テスト 27: snapshot に全 5 セクションあり",
          set(snap.keys()) >= {"health", "anomaly", "alerts", "sla", "audit"},
          f"keys={list(snap.keys())}")

    check("テスト 28: alerts.suppressed >= 1（cooldown で 1 件抑制）",
          snap["alerts"]["suppressed"] >= 1,
          f"got {snap['alerts']}")

    check("テスト 29: anomaly.total >= 1（コスト急増 1 件検知）",
          snap["anomaly"]["total"] >= 1,
          f"got {snap['anomaly']}")

    json_out = dashboard.to_json()
    check("テスト 30: to_json() で valid JSON が出力される",
          isinstance(json.loads(json_out), dict),
          f"len={len(json_out)}")

    # ------------------------------------------------------------------
    # サマリー
    # ------------------------------------------------------------------
    total = passed + failed
    print()
    print("=" * 80)
    print("📊 テスト結果サマリー")
    print("=" * 80)
    print(f"✅ 成功: {passed}/{total}")
    print(f"❌ 失敗: {failed}/{total}")
    print(f"📈 成功率: {passed / total * 100:.1f}%")
    print("=" * 80)

    if failed == 0:
        print()
        print("🎉 Phase 9 完全実装完了！すべてのテストに PASS しました。")
        print()
        print("本番運用の継続的監視レイヤー:")
        print("  1. HealthChecker        — 定期ヘルスチェック")
        print("  2. AnomalyDetector      — z-score 統計的異常検知")
        print("  3. AlertRouter          — 重要度別ルーティング・スロットリング")
        print("  4. SLATracker           — p50/p95/p99・稼働率計測")
        print("  5. AuditTrail           — SHA-256 hash chain 改竄検知")
        print("  6. OperationsDashboard  — 全指標スナップショット")
        print()
        print("次ステップ: Phase 10 - 継続改善・スケールアウト準備")
    else:
        print()
        print(f"⚠️  {failed} 件のテストが失敗しました。")
        for e in errors:
            print(f"  - {e}")


if __name__ == "__main__":
    run_tests()
