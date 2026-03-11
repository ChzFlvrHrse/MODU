import React, { useEffect, useState, useMemo, useCallback, useRef } from "react";
import { useParams, useSearchParams, useNavigate } from "react-router-dom";
import { CircularProgress } from "@mui/material";
import UploadIcon from "@mui/icons-material/Upload";
import FactCheckIcon from "@mui/icons-material/FactCheck";
import CloseIcon from "@mui/icons-material/Close";
import { ArrowBackIosNew, ChevronRight, ExpandMore, ExpandLess } from "@mui/icons-material";
import { toast } from "react-hot-toast";
import "./Packages.css";

import UploadSubmittal from "../UploadSubmittal/UploadSubmittal";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// ── Types ──────────────────────────────────────────────────────────────────────

interface Submittal {
    id: number;
    submittal_title: string;
    submittal_type_name: string;
    status: string;
    page_count: number;
}

interface Package {
    id: number;
    package_name: string;
    company_name: string | null;
    compliance_score: number | null;
    status: string | null;
    run_count: number;
    last_checked_at: string | null;
    checked_submittal_ids: number[] | null;
    created_at: string;
    submittals: Submittal[];
}

interface RequirementFinding {
    requirement: string;
    status: string;
    evidence: string | null;
    drawing_reference?: string | null;
    notes: string | null;
    spec_pages: number[];
    submittal_pages: number[];
}

interface NonConformance {
    description: string;
    severity: string;
    spec_reference: string | null;
    recommendation: string | null;
}

interface MissingItem {
    description: string;
    spec_reference: string | null;
    required: boolean;
}

interface ComplianceResult {
    is_compliant: boolean;
    compliance_score: number;
    summary: string;
    requirement_findings: RequirementFinding[];
    non_conformances: NonConformance[];
    missing_items: MissingItem[];
    recommendations: string[];
    reviewer_notes: string;
}

interface ComplianceRun {
    id: number;
    compliance_result: ComplianceResult;
    compliance_score: number;
    is_compliant: boolean;
    pipeline: string;
    model: string;
    submittal_ids: number[];
    token_count: number;
    created_at: string;
}

type PaneTarget =
    | { type: "package"; packageId: number }
    | { type: "submittal"; packageId: number; submittalId: number; submittalTitle: string };

interface DragState {
    packageId: number;
    submittalId: number;
    submittalTitle: string;
}
// ── Pane ──────────────────────────────────────────────────────────────────────

interface PaneProps {
    target: PaneTarget;
    packageId: number;
    spec_id: string;
    section_id: string;
    section_number: string;
    packageName: string;
    onClose?: () => void;
    isDragOver: boolean;
    onDragOver: (e: React.DragEvent) => void;
    onDragLeave: () => void;
    onDrop: () => void;
    isDragging: boolean;
    onRunComplete: () => void;
    packages: Package[];
}

function CompliancePane({
    target,
    packageId,
    spec_id,
    section_id,
    section_number,
    packageName,
    onClose,
    isDragOver,
    onDragOver,
    onDragLeave,
    onDrop,
    isDragging,
    onRunComplete,
    packages,
}: PaneProps) {
    const [runs, setRuns] = useState<ComplianceRun[]>([]);
    const [loadingRuns, setLoadingRuns] = useState(false);
    const [running, setRunning] = useState(false);

    const latestRun = runs[0] ?? null;

    const fetchRuns = useCallback(async () => {
        setLoadingRuns(true);
        setRuns([]);
        try {
            if (target.type === "package") {
                const res = await fetch(`${BACKEND_URL}/api/submittal/package_result/${target.packageId}`);
                if (!res.ok) {
                    setRuns([]);
                    return;
                }
                const data = await res.json();
                if (data.result?.compliance_result) {
                    // Shape it to match ComplianceRun interface
                    setRuns([{
                        id: data.result.id,
                        compliance_result: data.result.compliance_result,
                        compliance_score: data.result.compliance_score,
                        is_compliant: data.result.compliance_result.is_compliant,
                        pipeline: "package",
                        model: "claude-sonnet-4-6",
                        submittal_ids: data.result.checked_submittal_ids ?? [],
                        token_count: 0,
                        created_at: data.result.last_checked_at,
                    }]);
                }
            } else {
                const res = await fetch(
                    `${BACKEND_URL}/api/submittal/compliance_runs_for_package?package_id=${target.packageId}&submittal_id=${target.submittalId}`
                );
                const data = await res.json();
                setRuns(data.compliance_runs ?? []);
            }
        } finally {
            setLoadingRuns(false);
        }
    }, [target]);

    useEffect(() => {
        fetchRuns();
    }, [fetchRuns]);

    const handleRun = async () => {
        setRunning(true);
        try {
            const body: Record<string, unknown> = {
                package_id: target.packageId,
                spec_id,
                section_id,
                section_number,
            };

            if (target.type === "submittal") {
                body.submittal_ids = [target.submittalId];
            }

            const res = await fetch(`${BACKEND_URL}/api/submittal/compliance_check`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });

            if (!res.ok) {
                const err = await res.json();
                toast.error(err.error ?? "Compliance check failed.");
                return;
            }

            toast.success("Compliance check complete.");
            await fetchRuns();
            onRunComplete();
        } catch {
            toast.error("Network error running compliance check.");
        } finally {
            setRunning(false);
        }
    };

    const label = target.type === "package"
        ? (packages.find(p => p.id === target.packageId)?.package_name ?? "Package")
        : target.submittalTitle;
    const sublabel = target.type === "package" ? "Full Package" : "Individual Submittal";

    return (
        <div
            className={`pkg-pane${isDragOver ? " drag-over" : ""}${isDragging ? " drag-active" : ""}`}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={(e) => { e.preventDefault(); onDrop(); }}
        >
            {isDragging && (
                <div className="pkg-pane-drop-overlay">
                    <div className="pkg-pane-drop-hint">
                        <span className="pkg-pane-drop-icon">⊕</span>
                        <span>Drop to load here</span>
                    </div>
                </div>
            )}

            <div className="pkg-pane-topbar">
                <div className="pkg-pane-topbar-left">
                    <span className="pkg-pane-label">{label}</span>
                    <span className={`pkg-pane-sublabel ${target.type}`}>{sublabel}</span>
                </div>
                <div className="pkg-pane-topbar-right">
                    <button
                        className={`pkg-run-btn${running ? " loading" : ""}`}
                        onClick={handleRun}
                        disabled={running}
                    >
                        {running ? (
                            <><CircularProgress size={12} sx={{ color: "inherit" }} /> Running…</>
                        ) : (
                            <><FactCheckIcon fontSize="small" /> Run Check</>
                        )}
                    </button>
                    {onClose && (
                        <button className="pkg-pane-close" onClick={onClose} title="Close pane">
                            <CloseIcon fontSize="small" />
                        </button>
                    )}
                </div>
            </div>

            <div className="pkg-pane-body">
                {running && (
                    <div className="pkg-stream-overlay">
                        <div className="pkg-stream-header">
                            <div className="pkg-stream-indicator">
                                <span className="pkg-stream-dot" />
                                <span className="pkg-stream-dot" />
                                <span className="pkg-stream-dot" />
                            </div>
                            <span className="pkg-stream-title">Analyzing submittal…</span>
                        </div>
                    </div>
                )}
                {loadingRuns ? (
                    <div className="pkg-no-results">
                        <CircularProgress size={24} sx={{ color: "rgba(255,255,255,0.3)" }} />
                    </div>
                ) : !latestRun ? (
                    <div className="pkg-no-results">
                        <div className="pkg-no-results-icon">◎</div>
                        <p className="pkg-no-results-title">No compliance check yet</p>
                        <p className="pkg-no-results-sub">
                            {target.type === "submittal"
                                ? "Run a check on this submittal to see individual findings."
                                : "Run a compliance check to see AI-generated findings for this package."}
                        </p>
                    </div>
                ) : (
                    <ComplianceReport result={latestRun.compliance_result} run={latestRun} />
                )}
            </div>
        </div>
    );
}

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function Packages() {
    const { spec_id, package_id } = useParams();
    const [searchParams] = useSearchParams();
    const section_number = searchParams.get("section_number") ?? "";
    const section_title = searchParams.get("section_title");
    const section_id = searchParams.get("section_id") ?? "";

    const navigate = useNavigate();

    const [packages, setPackages] = useState<Package[]>([]);
    const [activePackageId, setActivePackageId] = useState<number | null>(null);
    const [expandedPackageIds, setExpandedPackageIds] = useState<Set<number>>(new Set());
    const [loading, setLoading] = useState(true);
    const [showUpload, setShowUpload] = useState(false);

    const [leftTarget, setLeftTarget] = useState<PaneTarget>({ type: "package", packageId: activePackageId ?? 0 });
    const [rightTarget, setRightTarget] = useState<PaneTarget | null>(null);
    const [dragState, setDragState] = useState<DragState | null>(null);
    const [dragOverPane, setDragOverPane] = useState<"left" | "right" | null>(null);

    const didDrag = useRef(false);

    const activePackage = useMemo(
        () => packages.find((p) => p.id === activePackageId) ?? null,
        [packages, activePackageId]
    );

    const isSplitView = rightTarget !== null;

    const fetchPackages = useCallback(async () => {
        if (!section_id) return;
        try {
            const res = await fetch(`${BACKEND_URL}/api/submittal/sections_packages/${section_id}`);
            const data = await res.json();
            const pkgs: Package[] = data.packages ?? [];
            setPackages(pkgs);
            const urlId = package_id ? parseInt(package_id) : null;
            if (urlId && pkgs.find((p) => p.id === urlId)) {
                setActivePackageId(urlId);
                setExpandedPackageIds(new Set([urlId]));
            } else if (pkgs.length > 0) {
                setActivePackageId(pkgs[0].id);
                setExpandedPackageIds(new Set([pkgs[0].id]));
            }
        } finally {
            setLoading(false);
        }
    }, [section_id, package_id]);

    useEffect(() => {
        fetchPackages();
    }, [fetchPackages]);

    useEffect(() => {
        if (dragState) return;
        setLeftTarget({ type: "package", packageId: activePackageId ?? 0 });
        setRightTarget(null);
    }, [activePackageId]);

    const toggleExpand = (id: number) => {
        setExpandedPackageIds((prev) => {
            const next = new Set(prev);
            next.has(id) ? next.delete(id) : next.add(id);
            return next;
        });
    };

    const handleDragStart = (pkg: Package, sub: Submittal) => {
        setDragState({ packageId: pkg.id, submittalId: sub.id, submittalTitle: sub.submittal_title });
    };

    const handleDragEnd = () => {
        setDragState(null);
        setDragOverPane(null);
    };

    const handleDrop = (pane: "left" | "right") => {
        if (!dragState) return;
        const target: PaneTarget = {
            type: "submittal",
            packageId: dragState.packageId,
            submittalId: dragState.submittalId,
            submittalTitle: dragState.submittalTitle,
        };
        if (pane === "left") setLeftTarget(target);
        else setRightTarget(target);
        setDragState(null);
        setDragOverPane(null);
    };

    return (
        <>
            <div className="pkg-page">
                <div className="pkg-header">
                    <div>
                        <button className="pkg-back-btn" onClick={() => navigate(-1)}>
                            <ArrowBackIosNew fontSize="large" />
                        </button>
                        <h1 className="pkg-title">Packages</h1>
                        {section_number && section_title && (
                            <p className="pkg-subtitle">
                                <span className="pkg-section-title">{section_title} - </span>
                                <span className="pkg-section-badge">{section_number}</span>
                            </p>
                        )}
                    </div>
                    <button
                        className="pkg-run-btn pkg-upload-btn-secondary"
                        onClick={() => setShowUpload(true)}
                    >
                        <UploadIcon fontSize="small" /> Upload Submittal(s)
                    </button>
                </div>

                <div className="pkg-layout">
                    <aside className="pkg-sidebar">
                        <div className="pkg-sidebar-title">Packages</div>
                        {dragState && (
                            <div className="pkg-drag-hint">Drag to a pane to compare</div>
                        )}
                        <div className="pkg-sidebar-list">
                            {loading ? (
                                <div className="pkg-sidebar-loading">
                                    <CircularProgress size={18} sx={{ color: "rgba(255,255,255,0.4)" }} />
                                </div>
                            ) : packages.length === 0 ? (
                                <div className="pkg-sidebar-empty">No packages found.</div>
                            ) : (
                                packages.map((pkg) => {
                                    const isActive = pkg.id === activePackageId;
                                    const isExpanded = expandedPackageIds.has(pkg.id);
                                    const score = pkg.compliance_score;

                                    return (
                                        <div key={pkg.id} className="pkg-sidebar-group">
                                            <button
                                                className={`pkg-sidebar-item${isActive ? " active" : ""}`}
                                                onClick={() => {
                                                    setActivePackageId(pkg.id);
                                                    toggleExpand(pkg.id);
                                                }}
                                            >
                                                <div className="pkg-sidebar-item-left">
                                                    <span className="pkg-sidebar-name">{pkg.package_name}</span>
                                                    {pkg.company_name && (
                                                        <span className="pkg-sidebar-company">{pkg.company_name}</span>
                                                    )}
                                                </div>
                                                <div className="pkg-sidebar-item-right">
                                                    {score !== null && (
                                                        <span className={`pkg-score-badge ${score >= 0.7 ? "good" : score >= 0.4 ? "warn" : "bad"}`}>
                                                            {Math.round(score * 100)}%
                                                        </span>
                                                    )}
                                                    {isExpanded
                                                        ? <ExpandLess fontSize="small" sx={{ color: "rgba(255,255,255,0.3)", flexShrink: 0 }} />
                                                        : <ExpandMore fontSize="small" sx={{ color: "rgba(255,255,255,0.3)", flexShrink: 0 }} />
                                                    }
                                                </div>
                                            </button>

                                            {isExpanded && pkg.submittals.length > 0 && (
                                                <div className="pkg-submittal-list">
                                                    <button
                                                        className="pkg-cumulative-btn"
                                                        onClick={() => setLeftTarget({ type: "package", packageId: pkg.id })}
                                                    >
                                                        <span className="pkg-cumulative-icon">◎</span>
                                                        <div className="pkg-submittal-info">
                                                            <span className="pkg-submittal-title">Cumulative Summary</span>
                                                            <span className="pkg-submittal-type">Full Package</span>
                                                        </div>
                                                    </button>
                                                    {pkg.submittals.map((sub) => (
                                                        <div
                                                            key={sub.id}
                                                            className={`pkg-submittal-item${dragState?.submittalId === sub.id ? " dragging" : ""}`}
                                                            draggable
                                                            onClick={() => {
                                                                if (didDrag) {
                                                                    didDrag.current = false;
                                                                    return;
                                                                }
                                                                setLeftTarget({ type: "submittal", packageId: pkg.id, submittalId: sub.id, submittalTitle: sub.submittal_title });
                                                                // setActivePackageId(pkg.id);
                                                            }}
                                                            onDragStart={(e) => {
                                                                e.stopPropagation();
                                                                didDrag.current = true;
                                                                // setActivePackageId(pkg.id);
                                                                handleDragStart(pkg, sub);
                                                            }}
                                                            onDragEnd={() => {
                                                                handleDragEnd();
                                                                setTimeout(() => {
                                                                    didDrag.current = false;
                                                                }, 0);
                                                            }}
                                                        >
                                                            <ChevronRight fontSize="small" sx={{ color: "rgba(255,255,255,0.2)", flexShrink: 0 }} />
                                                            <div className="pkg-submittal-info">
                                                                <span className="pkg-submittal-title">{sub.submittal_title}</span>
                                                                <span className="pkg-submittal-type">{sub.submittal_type_name}</span>
                                                            </div>
                                                            <span className="pkg-submittal-drag-handle" title="Drag to compare">⠿</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}

                                            {isExpanded && pkg.submittals.length === 0 && (
                                                <div className="pkg-submittal-empty">No submittals uploaded yet.</div>
                                            )}
                                        </div>
                                    );
                                })
                            )}
                        </div>
                    </aside>

                    {!activePackage ? (
                        <main className="pkg-main">
                            <div className="pkg-main-empty">Select a package to view results.</div>
                        </main>
                    ) : (
                        <main className={`pkg-main pkg-main-panes${isSplitView ? " split" : ""}`}>
                            <CompliancePane
                                key={`left-${activePackage.id}-${JSON.stringify(leftTarget)}`}
                                target={leftTarget}
                                packageId={activePackage.id}
                                spec_id={spec_id!}
                                section_id={section_id}
                                section_number={section_number}
                                packageName={activePackage.package_name}
                                isDragOver={dragOverPane === "left"}
                                onDragOver={(e) => { e.preventDefault(); setDragOverPane("left"); }}
                                onDragLeave={() => setDragOverPane(null)}
                                onDrop={() => handleDrop("left")}
                                isDragging={!!dragState}
                                onRunComplete={fetchPackages}
                                packages={packages}
                            />

                            {isSplitView && rightTarget && (
                                <>
                                    <div className="pkg-pane-divider" />
                                    <CompliancePane
                                        key={`right-${activePackage.id}-${JSON.stringify(rightTarget)}`}
                                        target={rightTarget}
                                        packageId={activePackage.id}
                                        spec_id={spec_id!}
                                        section_id={section_id}
                                        section_number={section_number}
                                        packageName={activePackage.package_name}
                                        onClose={() => setRightTarget(null)}
                                        isDragOver={dragOverPane === "right"}
                                        onDragOver={(e) => { e.preventDefault(); setDragOverPane("right"); }}
                                        onDragLeave={() => setDragOverPane(null)}
                                        onDrop={() => handleDrop("right")}
                                        isDragging={!!dragState}
                                        onRunComplete={fetchPackages}
                                        packages={packages}
                                    />
                                </>
                            )}

                            {/* Right drop zone — single view only, while dragging */}
                            {!isSplitView && dragState && (
                                <div
                                    className={`pkg-drop-zone-right${dragOverPane === "right" ? " drag-over" : ""}`}
                                    onDragOver={(e) => { e.preventDefault(); setDragOverPane("right"); }}
                                    onDragLeave={() => setDragOverPane(null)}
                                    onDrop={(e) => { e.preventDefault(); handleDrop("right"); }}
                                >
                                    <span className="pkg-drop-zone-icon">⊕</span>
                                    <span className="pkg-drop-zone-label">Compare here</span>
                                </div>
                            )}
                        </main>
                    )}
                </div>
            </div>

            {showUpload && activePackage && (
                <UploadSubmittal
                    spec_id={spec_id!}
                    package_id={activePackage.id}
                    package_name={activePackage.package_name}
                    onClose={() => setShowUpload(false)}
                    onUploaded={fetchPackages}
                />
            )}
        </>
    );
}

// ── ComplianceReport ───────────────────────────────────────────────────────────

function ComplianceReport({ result, run }: { result: ComplianceResult; run: ComplianceRun }) {
    const scoreColor =
        result.compliance_score >= 0.7 ? "#3fb950" :
            result.compliance_score >= 0.4 ? "#d29922" : "#e74c3c";

    return (
        <div className="pkg-report">
            <div className="pkg-report-header">
                <div className="pkg-report-score-row">
                    <div className="pkg-report-circle" style={{ borderColor: scoreColor }}>
                        <span className="pkg-report-score-value" style={{ color: scoreColor }}>
                            {Math.round(result.compliance_score * 100)}%
                        </span>
                        <span className="pkg-report-score-label">Score</span>
                    </div>
                    <div className="pkg-report-verdict-block">
                        <div className="pkg-report-verdict-top">
                            <div className={`pkg-report-verdict-tag ${result.is_compliant ? "pass" : "fail"}`}>
                                {result.is_compliant ? "✓ Compliant" : "✕ Non-Compliant"}
                            </div>
                            <span className="pkg-report-meta">
                                {run.pipeline} · {new Date(run.created_at).toLocaleString()}
                            </span>
                        </div>
                        <p className="pkg-report-summary-text">{result.summary}</p>
                    </div>
                </div>
            </div>

            {result.non_conformances.length > 0 && (
                <ReportSection title="Non-Conformances">
                    <div className="pkg-nc-list">
                        {result.non_conformances.map((nc, i) => (
                            <div key={i} className={`pkg-nc-card pkg-nc-${nc.severity}`}>
                                <div className="pkg-nc-top">
                                    <span className="pkg-nc-description">{nc.description}</span>
                                    <span className={`pkg-severity-badge pkg-severity-${nc.severity}`}>{nc.severity}</span>
                                </div>
                                {nc.spec_reference && <div className="pkg-nc-spec">{nc.spec_reference}</div>}
                                {nc.recommendation && <div className="pkg-nc-rec">→ {nc.recommendation}</div>}
                            </div>
                        ))}
                    </div>
                </ReportSection>
            )}

            <ReportSection title="Requirement Findings">
                <div className="pkg-findings-wrap">
                    <table className="pkg-findings-table">
                        <thead>
                            <tr>
                                <th style={{ width: "42%" }}>Requirement</th>
                                <th style={{ width: "11%" }}>Status</th>
                                <th>Evidence / Notes</th>
                            </tr>
                        </thead>
                        <tbody>
                            {result.requirement_findings.map((f, i) => (
                                <tr key={i}>
                                    <td>{f.requirement}</td>
                                    <td><span className={`pkg-status-pill status-${f.status}`}>{f.status.replace("_", " ")}</span></td>
                                    <td>
                                        {f.evidence && <p className="pkg-finding-evidence">{f.evidence}</p>}
                                        {f.drawing_reference && <p className="pkg-finding-ref">Drawing: {f.drawing_reference}</p>}
                                        {f.notes && <p className="pkg-finding-notes">{f.notes}</p>}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </ReportSection>

            {result.missing_items.length > 0 && (
                <ReportSection title="Missing Items">
                    <div className="pkg-missing-list">
                        {result.missing_items.map((item, i) => (
                            <div key={i} className="pkg-missing-item">
                                <span className={`pkg-missing-badge ${item.required ? "required" : "optional"}`}>
                                    {item.required ? "Required" : "Optional"}
                                </span>
                                <div className="pkg-missing-text">
                                    <div className="pkg-missing-description">{item.description}</div>
                                    {item.spec_reference && <div className="pkg-missing-spec">{item.spec_reference}</div>}
                                </div>
                            </div>
                        ))}
                    </div>
                </ReportSection>
            )}

            {result.recommendations.length > 0 && (
                <ReportSection title="Recommendations">
                    <div className="pkg-rec-list">
                        {result.recommendations.map((rec, i) => (
                            <div key={i} className="pkg-rec-item">
                                <span className="pkg-rec-index">{String(i + 1).padStart(2, "0")}</span>
                                <span className="pkg-rec-text">{rec}</span>
                            </div>
                        ))}
                    </div>
                </ReportSection>
            )}

            {result.reviewer_notes && (
                <ReportSection title="Reviewer Notes">
                    <div className="pkg-reviewer-notes">{result.reviewer_notes}</div>
                </ReportSection>
            )}
        </div>
    );
}

function ReportSection({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <div className="pkg-report-section">
            <div className="pkg-report-section-header">
                <span className="pkg-report-section-title">{title}</span>
                <div className="pkg-report-section-divider" />
            </div>
            {children}
        </div>
    );
}
