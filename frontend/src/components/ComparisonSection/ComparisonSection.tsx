import { useState } from "react";
import { toast } from "react-hot-toast";
import "./ComparisonSection.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// --- Types ---

interface DimensionComparison {
    dimension: string;
    winner: "A" | "B" | "tie";
    a_status: "compliant" | "non_compliant" | "missing" | "partial" | "unclear";
    b_status: "compliant" | "non_compliant" | "missing" | "partial" | "unclear";
    rationale: string;
}

interface ComparisonResult {
    overall_winner: "A" | "B" | "tie";
    score_a: number;
    score_b: number;
    score_delta: number;
    confidence: "high" | "medium" | "low";
    executive_summary: string;
    dimension_comparisons: DimensionComparison[];
    a_exclusive_strengths: string[];
    b_exclusive_strengths: string[];
    shared_deficiencies: string[];
    a_critical_failures: string[];
    b_critical_failures: string[];
    recommendation: string;
}

export interface ComparisonRecord {
    id: number;
    package_id_a: number;
    package_id_b: number;
    package_name_a: string;
    package_name_b: string;
    section_number: string;
    overall_winner: "A" | "B" | "tie";
    score_a: number;
    score_b: number;
    score_delta: number;
    confidence: "high" | "medium" | "low";
    executive_summary: string;
    recommendation: string;
    comparison_result: ComparisonResult;
    model_version: string;
    created_at: string;
}

interface ComparisonSectionProps {
    comparisons: ComparisonSummary[];
}

export interface ComparisonSummary {
    id: number;
    package_name_a: string;
    package_name_b: string;
    score_a: number;
    score_b: number;
    overall_winner: "A" | "B" | "tie";
}

// --- Helpers ---

const pct = (score: number) => `${Math.round(score * 100)}%`;

const statusLabel: Record<string, string> = {
    compliant: "COMPLIANT",
    non_compliant: "NON-COMPLIANT",
    missing: "MISSING",
    partial: "PARTIAL",
    unclear: "UNCLEAR",
};

const statusClass: Record<string, string> = {
    compliant: "status-compliant",
    non_compliant: "status-non-compliant",
    missing: "status-missing",
    partial: "status-partial",
    unclear: "status-unclear",
};

// --- Sub-components ---

function ScoreRing({ score, label }: { score: number; label: string }) {
    const radius = 28;
    const circumference = 2 * Math.PI * radius;
    const pctVal = score * 100;
    const offset = circumference - (pctVal / 100) * circumference;
    const color =
        pctVal >= 75 ? "#4ade80" : pctVal >= 50 ? "#f59e0b" : "#ef4444";

    return (
        <div className="cmp-score-ring">
            <svg width="72" height="72" viewBox="0 0 72 72">
                <circle cx="36" cy="36" r={radius} className="cmp-ring-bg" />
                <circle
                    cx="36"
                    cy="36"
                    r={radius}
                    className="cmp-ring-fill"
                    stroke={color}
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    transform="rotate(-90 36 36)"
                />
            </svg>
            <div className="cmp-ring-label">
                <span className="cmp-ring-pct" style={{ color }}>
                    {pct(score)}
                </span>
                <span className="cmp-ring-sub">{label}</span>
            </div>
        </div>
    );
}

function WinnerBadge({ winner }: { winner: "A" | "B" | "tie" }) {
    const cls =
        winner === "tie"
            ? "winner-badge tie"
            : "winner-badge win";
    const text =
        winner === "tie" ? "TIE" : `PKG ${winner} WINS`;
    return <span className={cls}>{text}</span>;
}

function ConfidenceBadge({ confidence }: { confidence: "high" | "medium" | "low" }) {
    console.log("confidence", confidence);
    return (
        <span className={`confidence-badge confidence-${confidence}`}>
            {confidence.toUpperCase()} CONFIDENCE
        </span>
    );
}

function DimensionRow({ dim }: { dim: DimensionComparison }) {
    return (
        <div className="dim-row">
            <div className="dim-name">{dim.dimension}</div>
            <div className="dim-cells">
                <span className={`dim-status ${statusClass[dim.a_status]}`}>
                    {statusLabel[dim.a_status]}
                </span>
                <span className={`dim-winner-indicator winner-${dim.winner}`}>
                    {dim.winner === "tie" ? "—" : dim.winner === "A" ? "◀" : "▶"}
                </span>
                <span className={`dim-status ${statusClass[dim.b_status]}`}>
                    {statusLabel[dim.b_status]}
                </span>
            </div>
            <div className="dim-rationale">{dim.rationale}</div>
        </div>
    );
}

export function ExpandedComparison({
    record,
}: {
    record: ComparisonRecord;
}) {
    const r = record.comparison_result;
    console.log("record", record);

    return (
        <div className="cmp-expanded">
            {/* Score header */}
            <div className="cmp-scores-row">
                <div className="cmp-score-block">
                    <div className="cmp-pkg-name">PKG A</div>
                    <ScoreRing score={record.score_a} label="PKG A" />
                    <div className="cmp-pkg-name">{record.package_name_a}</div>
                </div>
                <div className="cmp-vs-col">
                    <WinnerBadge winner={record.overall_winner} />
                    <div className="cmp-delta">Δ {pct(record.score_delta)}</div>
                    <ConfidenceBadge confidence={record.comparison_result.confidence} />
                </div>
                <div className="cmp-score-block">
                    <div className="cmp-pkg-name">PKG B</div>
                    <ScoreRing score={record.score_b} label="PKG B" />
                    <div className="cmp-pkg-name">{record.package_name_b}</div>
                </div>
            </div>

            {/* Executive summary */}
            <div className="cmp-section-block">
                <div className="cmp-section-label">SUMMARY</div>
                <p className="cmp-summary-text">{record.executive_summary}</p>
            </div>

            {/* Dimension table */}
            {r.dimension_comparisons?.length > 0 && (
                <div className="cmp-section-block">
                    <div className="cmp-section-label">DIMENSION BREAKDOWN</div>
                    <div className="dim-header">
                        <span className="reqs-header">REQUIREMENT</span>
                        <span className="dim-header-right">
                            <span className="pkg-a-header">PKG A</span>
                            <span className="pkg-b-header">PKG B</span>
                        </span>
                    </div>
                    <div className="dim-list">
                        {r.dimension_comparisons.map((d, i) => (
                            <DimensionRow key={i} dim={d} />
                        ))}
                    </div>
                </div>
            )}

            {/* Strengths */}
            <div className="cmp-two-col">
                <div className="cmp-section-block">
                    <div className="cmp-section-label strength-a">PKG A STRENGTHS</div>
                    <ul className="cmp-list">
                        {r.a_exclusive_strengths.map((s, i) => (
                            <li key={i}>{s}</li>
                        ))}
                    </ul>
                </div>
                <div className="cmp-section-block">
                    <div className="cmp-section-label strength-b">PKG B STRENGTHS</div>
                    <ul className="cmp-list">
                        {r.b_exclusive_strengths.map((s, i) => (
                            <li key={i}>{s}</li>
                        ))}
                    </ul>
                </div>
            </div>

            {/* Critical failures */}
            <div className="cmp-two-col">
                <div className="cmp-section-block">
                    <div className="cmp-section-label failure-label">PKG A CRITICAL FAILURES</div>
                    <ul className="cmp-list failure-list">
                        {r.a_critical_failures.map((s, i) => (
                            <li key={i}>{s}</li>
                        ))}
                    </ul>
                </div>
                <div className="cmp-section-block">
                    <div className="cmp-section-label failure-label">PKG B CRITICAL FAILURES</div>
                    <ul className="cmp-list failure-list">
                        {r.b_critical_failures.map((s, i) => (
                            <li key={i}>{s}</li>
                        ))}
                    </ul>
                </div>
            </div>

            {/* Shared deficiencies */}
            <div className="cmp-section-block">
                <div className="cmp-section-label shared-label">SHARED DEFICIENCIES</div>
                <ul className="cmp-list shared-list">
                    {r.shared_deficiencies.map((s, i) => (
                        <li key={i}>{s}</li>
                    ))}
                </ul>
            </div>

            {/* Recommendation */}
            <div className="cmp-section-block">
                <div className="cmp-section-label">RECOMMENDATION</div>
                <p className="cmp-recommendation">{record.recommendation}</p>
            </div>
        </div>
    );
}

function ComparisonTile({ comparison }: { comparison: ComparisonSummary }) {
    const [expanded, setExpanded] = useState(false);
    const [detail, setDetail] = useState<ComparisonRecord | null>(null);
    const [loading, setLoading] = useState(false);

    const handleExpand = async () => {
        if (!expanded && !detail) {
            setLoading(true);
            try {
                const res = await fetch(`${BACKEND_URL}/api/submittal/compliance_comparisons?id=${comparison.id}`);
                const data = await res.json();
                if (data.error) {
                    toast.error(data.error);
                    return;
                }
                setDetail(data.comparison ?? null);
            } finally {
                setLoading(false);
            }
        }
        setExpanded(v => !v);
    };

    return (
        <div className={`cmp-tile ${expanded ? "expanded" : ""}`}>
            <div className="cmp-tile-header" onClick={handleExpand}>
                <div className="cmp-tile-left">
                    <div className="cmp-tile-packages">
                        <span className="cmp-pkg-label pkg-a">{comparison.package_name_a}</span>
                        <span className="cmp-tile-vs">vs</span>
                        <span className="cmp-pkg-label pkg-b">{comparison.package_name_b}</span>
                    </div>
                    <div className="cmp-tile-scores">
                        <span className="cmp-tile-score score-a">{pct(comparison.score_a)}</span>
                        <span className="cmp-tile-score-sep">·</span>
                        <span className="cmp-tile-score score-b">{pct(comparison.score_b)}</span>
                    </div>
                </div>
                <div className="cmp-tile-right">
                    {loading
                        ? <span className="cmp-loading">…</span>
                        : <WinnerBadge winner={comparison.overall_winner} />
                    }
                    <span className={`cmp-chevron ${expanded ? "open" : ""}`}>›</span>
                </div>
            </div>

            {expanded && detail && <ExpandedComparison record={detail} />}
        </div>
    );
}

export default function ComparisonSection({ comparisons }: { comparisons: ComparisonSummary[] }) {
    if (!comparisons || comparisons.length === 0) return null;

    return (
        <div className="cmp-section">
            <div className="cmp-section-header">SUBMITTAL COMPARISONS</div>
            <div className="cmp-tiles">
                {comparisons.map((c) => (
                    <ComparisonTile key={c.id} comparison={c} />
                ))}
            </div>
        </div>
    );
}
