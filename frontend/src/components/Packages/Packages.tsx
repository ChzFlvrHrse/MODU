import React, { useEffect, useState, useMemo, useCallback, useRef } from "react";
import { useParams, useSearchParams, useNavigate } from "react-router-dom";
import { CircularProgress } from "@mui/material";
import UploadIcon from "@mui/icons-material/Upload";
import FactCheckIcon from "@mui/icons-material/FactCheck";
import CloseIcon from "@mui/icons-material/Close";
import { ArrowBackIosNew, ExpandMore, ExpandLess, CompareArrows } from "@mui/icons-material";
import { toast } from "react-hot-toast";
import "./Packages.css";

import UploadSubmittal from "../UploadSubmittal/UploadSubmittal";
import type { ComparisonSummary, ComparisonRecord } from "../ComparisonSection/ComparisonSection";
import { ExpandedComparison } from "../ComparisonSection/ComparisonSection";

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
    | { type: "submittal"; packageId: number; submittalId: number; submittalTitle: string }
    | { type: "comparison"; comparisonId: number };

interface DragState {
    packageId: number;
    submittalId: number;
    submittalTitle: string;
}

// ── Comparison Detail ──────────────────────────────────────────────────────────

function ComparisonDetail({ comparisonId }: { comparisonId: number }) {
    const [detail, setDetail] = useState<ComparisonRecord | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        setLoading(true);
        setDetail(null);
        fetch(`${BACKEND_URL}/api/submittal/compliance_comparisons?id=${comparisonId}`)
            .then(r => r.json())
            .then(data => setDetail(data ?? null))
            .finally(() => setLoading(false));
    }, [comparisonId]);

    if (loading) return (
        <div className="pkg-no-results">
            <CircularProgress size={24} sx={{ color: "rgba(255,255,255,0.3)" }} />
        </div>
    );
    if (!detail) return (
        <div className="pkg-no-results">
            <p className="pkg-no-results-title">Comparison not found.</p>
        </div>
    );

    return <ExpandedComparison record={detail} />;
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
        if (target.type === "comparison") return;
        setLoadingRuns(true);
        setRuns([]);
        try {
            if (target.type === "package") {
                const res = await fetch(`${BACKEND_URL}/api/submittal/package_result/${target.packageId}`);
                if (!res.ok) { setRuns([]); return; }
                const data = await res.json();
                if (data.result?.compliance_result) {
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
        if (target.type === "comparison") return;
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

    const label = target.type === "comparison"
        ? "Comparison"
        : target.type === "package"
            ? (packages.find(p => p.id === target.packageId)?.package_name ?? "Package")
            : target.submittalTitle;

    const sublabel = target.type === "comparison"
        ? "comparison"
        : target.type === "package" ? "package" : "submittal";

    const sublabelText = target.type === "comparison"
        ? "Submittal Comparison"
        : target.type === "package" ? "Full Package" : "Individual Submittal";

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
                    <span className={`pkg-pane-sublabel ${sublabel}`}>{sublabelText}</span>
                </div>
                <div className="pkg-pane-topbar-right">
                    {target.type !== "comparison" && (
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
                    )}
                    {onClose && (
                        <button className="pkg-pane-close" onClick={onClose} title="Close pane">
                            <CloseIcon fontSize="small" />
                        </button>
                    )}
                </div>
            </div>

            <div className="pkg-pane-body">
                {target.type === "comparison" ? (
                    <ComparisonDetail comparisonId={target.comparisonId} />
                ) : (
                    <>
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
                    </>
                )}
            </div>
        </div>
    );
}

// ── Sidebar ────────────────────────────────────────────────────────────────────

interface SidebarProps {
    packages: Package[];
    loading: boolean;
    comparisons: ComparisonSummary[];
    activePackageId: number | null;
    expandedPackageIds: Set<number>;
    leftTarget: PaneTarget;
    dragState: DragState | null;
    didDrag: React.RefObject<boolean>;
    onPackageClick: (pkg: Package) => void;
    onCumulativeClick: (pkg: Package) => void;
    onCumulativeDragStart: (e: React.DragEvent, pkg: Package) => void;
    onCumulativeDragEnd: () => void;
    onSubmittalClick: (pkg: Package, sub: Submittal) => void;
    onSubmittalDragStart: (e: React.DragEvent, pkg: Package, sub: Submittal) => void;
    onSubmittalDragEnd: () => void;
    onComparisonClick: (c: ComparisonSummary) => void;
}

function Sidebar({
    packages,
    loading,
    comparisons,
    activePackageId,
    expandedPackageIds,
    leftTarget,
    dragState,
    didDrag,
    onPackageClick,
    onCumulativeClick,
    onCumulativeDragStart,
    onCumulativeDragEnd,
    onSubmittalClick,
    onSubmittalDragStart,
    onSubmittalDragEnd,
    onComparisonClick,
}: SidebarProps) {
    const [activeTab, setActiveTab] = useState<"packages" | "comparisons">("packages");

    console.log("PACKAGES", packages);

    return (
        <div className="pkg-sidebar">
            {/* Tabs */}
            <div className="pkg-sidebar-tabs">
                <button
                    className={`pkg-sidebar-tab${activeTab === "packages" ? " active" : ""}`}
                    onClick={() => setActiveTab("packages")}
                >
                    Packages
                    <span className="pkg-sidebar-tab-count">{packages.length}</span>
                </button>
                <button
                    className={`pkg-sidebar-tab${activeTab === "comparisons" ? " active" : ""}`}
                    onClick={() => setActiveTab("comparisons")}
                >
                    Comparisons
                    {comparisons.length > 0 && (
                        <span className="pkg-sidebar-tab-count">{comparisons.length}</span>
                    )}
                </button>
            </div>

            {/* Tab content */}
            <div className="pkg-sidebar-body">
                {activeTab === "packages" && (
                    <>
                        {dragState && (
                            <div className="pkg-drag-hint">Drag to a pane to compare</div>
                        )}
                        {loading ? (
                            <div className="pkg-sidebar-loading">
                                <CircularProgress size={18} sx={{ color: "rgba(255,255,255,0.4)" }} />
                            </div>
                        ) : packages.length === 0 ? (
                            <div className="pkg-sidebar-empty">No packages found.</div>
                        ) : (
                            packages.map((pkg) => {
                                const isExpanded = expandedPackageIds.has(pkg.id);
                                const score = pkg.compliance_score;
                                const scoreColor = score === null ? null
                                    : score >= 0.7 ? "#3fb950"
                                    : score >= 0.4 ? "#d29922"
                                    : "#e74c3c";

                                return (
                                    <div key={pkg.id} className="pkg-sidebar-group">
                                        {/* Package card */}
                                        <button
                                            className={`pkg-card${pkg.id === activePackageId ? " active" : ""}`}
                                            onClick={() => onPackageClick(pkg)}
                                        >
                                            <div className="pkg-card-top">
                                                <div className="pkg-card-info">
                                                    <span className="pkg-card-name">{pkg.package_name}</span>
                                                    {pkg.company_name && (
                                                        <span className="pkg-card-company">{pkg.company_name}</span>
                                                    )}
                                                </div>
                                                <div className="pkg-card-right">
                                                    {score !== null && (
                                                        <span className="pkg-card-score" style={{ color: scoreColor ?? undefined }}>
                                                            {Math.round(score * 100)}%
                                                        </span>
                                                    )}
                                                    {isExpanded
                                                        ? <ExpandLess fontSize="small" sx={{ color: "rgba(255,255,255,0.3)", flexShrink: 0 }} />
                                                        : <ExpandMore fontSize="small" sx={{ color: "rgba(255,255,255,0.3)", flexShrink: 0 }} />
                                                    }
                                                </div>
                                            </div>
                                            {/* Score bar */}
                                            {score !== null && (
                                                <div className="pkg-card-bar-track">
                                                    <div
                                                        className="pkg-card-bar-fill"
                                                        style={{
                                                            width: `${Math.round(score * 100)}%`,
                                                            background: scoreColor ?? "#6b7280",
                                                        }}
                                                    />
                                                </div>
                                            )}
                                        </button>

                                        {/* Expanded submittals */}
                                        {isExpanded && pkg.submittals.length > 0 && (
                                            <div className="pkg-tree">
                                                {/* Cumulative */}
                                                <div className="pkg-tree-line">
                                                    <div className="pkg-tree-connector" />
                                                    <div
                                                        className="pkg-cumulative-btn"
                                                        draggable
                                                        onClick={() => {
                                                            if (didDrag.current) { didDrag.current = false; return; }
                                                            onCumulativeClick(pkg);
                                                        }}
                                                        onDragStart={(e) => {
                                                            e.dataTransfer.setData("text/plain", String(pkg.id));
                                                            e.stopPropagation();
                                                            didDrag.current = true;
                                                            onCumulativeDragStart(e, pkg);
                                                        }}
                                                        onDragEnd={() => {
                                                            onCumulativeDragEnd();
                                                            setTimeout(() => { didDrag.current = false; }, 0);
                                                        }}
                                                    >
                                                        <span className="pkg-cumulative-icon">◎</span>
                                                        <div className="pkg-submittal-info">
                                                            <span className="pkg-submittal-title">Cumulative Summary</span>
                                                            <span className="pkg-submittal-type">Full Package</span>
                                                        </div>
                                                    </div>
                                                </div>

                                                {/* Individual submittals */}
                                                {pkg.submittals.map((sub, idx) => (
                                                    <div key={sub.id} className="pkg-tree-line">
                                                        <div className={`pkg-tree-connector${idx === pkg.submittals.length - 1 ? " last" : ""}`} />
                                                        <div
                                                            className={`pkg-submittal-item${dragState?.submittalId === sub.id ? " dragging" : ""}`}
                                                            draggable
                                                            onClick={() => {
                                                                if (didDrag.current) { didDrag.current = false; return; }
                                                                onSubmittalClick(pkg, sub);
                                                            }}
                                                            onDragStart={(e) => {
                                                                e.dataTransfer.setData("text/plain", String(sub.id));
                                                                e.stopPropagation();
                                                                didDrag.current = true;
                                                                onSubmittalDragStart(e, pkg, sub);
                                                            }}
                                                            onDragEnd={() => {
                                                                onSubmittalDragEnd();
                                                                setTimeout(() => { didDrag.current = false; }, 0);
                                                            }}
                                                        >
                                                            <div className="pkg-submittal-info">
                                                                <span className="pkg-submittal-title">{sub.submittal_title}</span>
                                                                <span className="pkg-submittal-type">{sub.submittal_type_name}</span>
                                                            </div>
                                                            <span className="pkg-submittal-drag-handle" title="Drag to compare">⠿</span>
                                                        </div>
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
                    </>
                )}

                {activeTab === "comparisons" && (
                    <>
                        {comparisons.length === 0 ? (
                            <div className="pkg-sidebar-empty">No comparisons yet.<br />Load two packages and run a comparison.</div>
                        ) : (
                            comparisons.map((c) => (
                                <button
                                    key={c.id}
                                    className={`pkg-comparison-item${leftTarget.type === "comparison" && leftTarget.comparisonId === c.id ? " active" : ""}`}
                                    onClick={() => onComparisonClick(c)}
                                >
                                    <div className="pkg-comparison-item-names">
                                        <span className="pkg-comparison-name-a">{c.package_name_a}</span>
                                        <span className="pkg-comparison-vs">vs</span>
                                        <span className="pkg-comparison-name-b">{c.package_name_b}</span>
                                    </div>
                                    <span className={`pkg-comparison-winner winner-${c.overall_winner}`}>
                                        {c.overall_winner === "tie" ? "TIE" : `PKG ${c.overall_winner}`}
                                    </span>
                                </button>
                            ))
                        )}
                    </>
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
    const [comparisons, setComparisons] = useState<ComparisonSummary[]>([]);
    const [runningComparison, setRunningComparison] = useState(false);

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

    const canRunComparison =
        leftTarget.type === "package" &&
        rightTarget?.type === "package" &&
        leftTarget.packageId !== rightTarget?.packageId;

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

    const fetchComparisons = useCallback(async () => {
        if (!section_id) return;
        const res = await fetch(`${BACKEND_URL}/api/submittal/get_compliance_comparisons_list?section_id=${section_id}`);
        const data = await res.json();
        setComparisons(data.comparisons ?? []);
    }, [section_id]);

    useEffect(() => { fetchPackages(); }, [fetchPackages]);
    useEffect(() => { fetchComparisons(); }, [fetchComparisons]);

    useEffect(() => {
        if (dragState) return;
        setLeftTarget({ type: "package", packageId: activePackageId ?? 0 });
        setRightTarget(null);
    }, [activePackageId]);

    const handlePackageClick = (pkg: Package) => {
        setActivePackageId(pkg.id);
        setExpandedPackageIds((prev) => {
            const next = new Set(prev);
            next.has(pkg.id) ? next.delete(pkg.id) : next.add(pkg.id);
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

    const handleDropPackage = (pane: "left" | "right", pkgId: number) => {
        const target: PaneTarget = { type: "package", packageId: pkgId };
        if (pane === "left") setLeftTarget(target);
        else setRightTarget(target);
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

    const handleRunComparison = async () => {
        if (leftTarget.type !== "package" || rightTarget?.type !== "package") return;
        const idA = leftTarget.packageId;
        const idB = rightTarget.packageId;
        setRunningComparison(true);
        try {
            const res = await fetch(`${BACKEND_URL}/api/submittal/run_compliance_comparison`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    package_id_a: idA,
                    package_id_b: idB,
                    section_id,
                    section_number,
                }),
            });
            if (!res.ok) {
                const err = await res.json();
                toast.error(err.error ?? "Comparison failed.");
                return;
            }
            toast.success("Comparison complete.");
            await fetchComparisons();
            setRightTarget(null);
        } catch {
            toast.error("Network error running comparison.");
        } finally {
            setRunningComparison(false);
        }
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
                    <div className="pkg-header-actions">
                        {canRunComparison && (
                            <button
                                className={`pkg-run-btn pkg-compare-btn${runningComparison ? " loading" : ""}`}
                                onClick={handleRunComparison}
                                disabled={runningComparison}
                            >
                                {runningComparison ? (
                                    <><CircularProgress size={12} sx={{ color: "inherit" }} /> Comparing…</>
                                ) : (
                                    <><CompareArrows fontSize="small" /> Run Comparison</>
                                )}
                            </button>
                        )}
                        <button
                            className="pkg-run-btn pkg-upload-btn-secondary"
                            onClick={() => setShowUpload(true)}
                        >
                            <UploadIcon fontSize="small" /> Upload Submittal(s)
                        </button>
                    </div>
                </div>

                <div className="pkg-layout">
                    <Sidebar
                        packages={packages}
                        loading={loading}
                        comparisons={comparisons}
                        activePackageId={activePackageId}
                        expandedPackageIds={expandedPackageIds}
                        leftTarget={leftTarget}
                        dragState={dragState}
                        didDrag={didDrag}
                        onPackageClick={handlePackageClick}
                        onCumulativeClick={(pkg) => setLeftTarget({ type: "package", packageId: pkg.id })}
                        onCumulativeDragStart={(e, pkg) => setDragState({ packageId: pkg.id, submittalId: -1, submittalTitle: "" })}
                        onCumulativeDragEnd={handleDragEnd}
                        onSubmittalClick={(pkg, sub) => setLeftTarget({ type: "submittal", packageId: pkg.id, submittalId: sub.id, submittalTitle: sub.submittal_title })}
                        onSubmittalDragStart={(e, pkg, sub) => handleDragStart(pkg, sub)}
                        onSubmittalDragEnd={handleDragEnd}
                        onComparisonClick={(c) => setLeftTarget({ type: "comparison", comparisonId: c.id })}
                    />

                    {!activePackage && leftTarget.type !== "comparison" ? (
                        <main className="pkg-main">
                            <div className="pkg-main-empty">Select a package to view results.</div>
                        </main>
                    ) : (
                        <main className={`pkg-main pkg-main-panes${isSplitView ? " split" : ""}`}>
                            <CompliancePane
                                key={`left-${JSON.stringify(leftTarget)}`}
                                target={leftTarget}
                                packageId={activePackage?.id ?? 0}
                                spec_id={spec_id!}
                                section_id={section_id}
                                section_number={section_number}
                                packageName={activePackage?.package_name ?? ""}
                                isDragOver={dragOverPane === "left"}
                                onDragOver={(e) => { e.preventDefault(); setDragOverPane("left"); }}
                                onDragLeave={() => setDragOverPane(null)}
                                onDrop={() => {
                                    if (dragState?.submittalId === -1) handleDropPackage("left", dragState.packageId);
                                    else handleDrop("left");
                                }}
                                isDragging={!!dragState}
                                onRunComplete={fetchPackages}
                                packages={packages}
                            />

                            {isSplitView && rightTarget && (
                                <>
                                    <div className="pkg-pane-divider" />
                                    <CompliancePane
                                        key={`right-${JSON.stringify(rightTarget)}`}
                                        target={rightTarget}
                                        packageId={activePackage?.id ?? 0}
                                        spec_id={spec_id!}
                                        section_id={section_id}
                                        section_number={section_number}
                                        packageName={activePackage?.package_name ?? ""}
                                        onClose={() => setRightTarget(null)}
                                        isDragOver={dragOverPane === "right"}
                                        onDragOver={(e) => { e.preventDefault(); setDragOverPane("right"); }}
                                        onDragLeave={() => setDragOverPane(null)}
                                        onDrop={() => {
                                            if (dragState?.submittalId === -1) handleDropPackage("right", dragState.packageId);
                                            else handleDrop("right");
                                        }}
                                        isDragging={!!dragState}
                                        onRunComplete={fetchPackages}
                                        packages={packages}
                                    />
                                </>
                            )}

                            {!isSplitView && dragState && (
                                <div
                                    className={`pkg-drop-zone-right${dragOverPane === "right" ? " drag-over" : ""}`}
                                    onDragOver={(e) => { e.preventDefault(); setDragOverPane("right"); }}
                                    onDragLeave={() => setDragOverPane(null)}
                                    onDrop={(e) => {
                                        e.preventDefault();
                                        if (dragState?.submittalId === -1) handleDropPackage("right", dragState.packageId);
                                        else handleDrop("right");
                                    }}
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
