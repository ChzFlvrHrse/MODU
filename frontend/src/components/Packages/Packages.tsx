import React, { useEffect, useState, useMemo } from "react";
import { useParams, useSearchParams, useNavigate } from "react-router-dom";
import { CircularProgress } from "@mui/material";
import UploadIcon from '@mui/icons-material/Upload';
import { ArrowBackIosNew, ChevronRight, ExpandMore, ExpandLess, PlayArrow } from "@mui/icons-material";
import { toast } from "react-hot-toast";
import "./Packages.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

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
    created_at: string;
    submittals: Submittal[];
    compliance_result: ComplianceResult | null;
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

export default function Packages() {
    const { spec_id, package_id } = useParams();
    const [searchParams] = useSearchParams();
    const section_number = searchParams.get("section_number");
    const section_title = searchParams.get("section_title");
    const section_id = searchParams.get("section_id");

    const navigate = useNavigate();

    const [packages, setPackages] = useState<Package[]>([]);
    const [activePackageId, setActivePackageId] = useState<number | null>(null);
    const [expandedPackageIds, setExpandedPackageIds] = useState<Set<number>>(new Set());
    const [highlightedSubmittalId, setHighlightedSubmittalId] = useState<number | null>(null);
    const [loading, setLoading] = useState(true);
    const [running, setRunning] = useState(false);

    const activePackage = useMemo(
        () => packages.find((p) => p.id === activePackageId) ?? null,
        [packages, activePackageId]
    );

    const fetchPackages = async () => {
        if (!spec_id || !section_number) return;
        try {
            const res = await fetch(`${BACKEND_URL}/api/submittal/sections_packages/${section_id}`);
            const data = await res.json();
            const pkgs: Package[] = data.packages ?? [];
            setPackages(pkgs);
            console.log(pkgs);

            // Set active to the package_id from URL param, or first
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
    };

    const handleRunCheck = async () => {
        if (!activePackage || !spec_id || !section_number) return;
        setRunning(true);
        try {
            const res = await fetch(`${BACKEND_URL}/api/submittal/compliance_check`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    package_id: activePackage.id,
                    spec_id,
                    section_number,
                }),
            });
            const data = await res.json();
            if (!res.ok || data.error) {
                toast.error(data.error ?? "Compliance check failed.");
                return;
            }
            toast.success("Compliance check complete.");
            await fetchPackages();
        } catch {
            toast.error("Network error running compliance check.");
        } finally {
            setRunning(false);
        }
    };

    const toggleExpand = (id: number) => {
        setExpandedPackageIds((prev) => {
            const next = new Set(prev);
            next.has(id) ? next.delete(id) : next.add(id);
            return next;
        });
    };

    const handleSubmittalClick = (submittalId: number) => {
        setHighlightedSubmittalId((prev) => (prev === submittalId ? null : submittalId));
    };

    useEffect(() => {
        fetchPackages();
    }, [spec_id, section_number]);

    // Reset highlight when active package changes
    useEffect(() => {
        setHighlightedSubmittalId(null);
    }, [activePackageId]);

    // Filter findings to those referencing the highlighted submittal's pages
    const highlightedSubmittal = useMemo(() => {
        if (!highlightedSubmittalId || !activePackage) return null;
        return activePackage.submittals.find((s) => s.id === highlightedSubmittalId) ?? null;
    }, [highlightedSubmittalId, activePackage]);

    const filteredFindings = useMemo(() => {
        if (!activePackage?.compliance_result) return [];
        if (!highlightedSubmittalId) return activePackage.compliance_result.requirement_findings;
        // Show findings that reference any submittal pages (non-empty submittal_pages)
        return activePackage.compliance_result.requirement_findings.filter(
            (f) => f.submittal_pages && f.submittal_pages.length > 0
        );
    }, [activePackage, highlightedSubmittalId]);

    return (
        <div className="pkg-page">
            {/* Header */}
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
            </div>

            <div className="pkg-layout">
                {/* Sidebar */}
                <aside className="pkg-sidebar">
                    <div className="pkg-sidebar-title">Packages</div>
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
                                        {/* Package row */}
                                        <button
                                            className={`pkg-sidebar-item ${isActive ? "active" : ""}`}
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

                                        {/* Submittals sub-list */}
                                        {isExpanded && pkg.submittals.length > 0 && (
                                            <div className="pkg-submittal-list">
                                                {pkg.submittals.map((sub) => (
                                                    <button
                                                        key={sub.id}
                                                        className={`pkg-submittal-item ${highlightedSubmittalId === sub.id ? "highlighted" : ""}`}
                                                        onClick={() => {
                                                            setActivePackageId(pkg.id);
                                                            handleSubmittalClick(sub.id);
                                                        }}
                                                    >
                                                        <ChevronRight fontSize="small" sx={{ color: "rgba(255,255,255,0.2)", flexShrink: 0 }} />
                                                        <div className="pkg-submittal-info">
                                                            <span className="pkg-submittal-title">{sub.submittal_title}</span>
                                                            <span className="pkg-submittal-type">{sub.submittal_type_name}</span>
                                                        </div>
                                                    </button>
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

                {/* Main content */}
                <main className="pkg-main">
                    {!activePackage ? (
                        <div className="pkg-main-empty">Select a package to view results.</div>
                    ) : (
                        <>
                            {/* Main top bar */}
                            <div className="pkg-main-topbar">
                                <div className="pkg-main-topbar-left">
                                    <span className="pkg-main-package-name">{activePackage.package_name}</span>
                                    {activePackage.company_name && (
                                        <span className="pkg-main-company">{activePackage.company_name}</span>
                                    )}
                                    {highlightedSubmittal && (
                                        <span className="pkg-main-filter-pill">
                                            Filtered: {highlightedSubmittal.submittal_title}
                                            <button className="pkg-main-filter-clear" onClick={() => setHighlightedSubmittalId(null)}>✕</button>
                                        </span>
                                    )}
                                </div>

                                {/* Upload Submittal(s) button */}
                                <button
                                    className={`pkg-run-btn ${running ? "loading" : ""}`}
                                    onClick={handleRunCheck}
                                    disabled={running}
                                >
                                    {running ? (
                                        <><CircularProgress size={12} sx={{ color: "inherit" }} /> Running…</>
                                    ) : (
                                        <><UploadIcon fontSize="small" /> Upload Submittal(s)</>
                                    )}
                                </button>

                                {/* Run Compliance Check button */}
                                {activePackage.submittals.length > 0 && (
                                    <button
                                        className={`pkg-run-btn ${running ? "loading" : ""}`}
                                        onClick={handleRunCheck}
                                        disabled={running}
                                    >
                                        {running ? (
                                            <><CircularProgress size={12} sx={{ color: "inherit" }} /> Running…</>
                                        ) : (
                                            <><PlayArrow fontSize="small" /> Run Compliance Check</>
                                        )}
                                    </button>
                                )}
                            </div>

                            {/* Compliance report or empty state */}
                            {!activePackage.compliance_result ? (
                                <div className="pkg-no-results">
                                    <div className="pkg-no-results-icon">◎</div>
                                    <p className="pkg-no-results-title">No compliance check yet</p>
                                    <p className="pkg-no-results-sub">Run a compliance check to see AI-generated findings for this package.</p>
                                </div>
                            ) : (
                                <ComplianceReport
                                    result={activePackage.compliance_result}
                                    findings={filteredFindings}
                                    isFiltered={!!highlightedSubmittalId}
                                />
                            )}
                        </>
                    )}
                </main>
            </div>
        </div>
    );
}

function ComplianceReport({
    result,
    findings,
    isFiltered,
}: {
    result: ComplianceResult;
    findings: RequirementFinding[];
    isFiltered: boolean;
}) {
    const scoreColor = result.compliance_score >= 0.7 ? "#3fb950" : result.compliance_score >= 0.4 ? "#d29922" : "#e74c3c";

    return (
        <div className="pkg-report">
            {/* Score header */}
            <div className="pkg-report-header">
                <div className="pkg-report-score-row">
                    <div className="pkg-report-circle" style={{ borderColor: scoreColor }}>
                        <span className="pkg-report-score-value" style={{ color: scoreColor }}>
                            {Math.round(result.compliance_score * 100)}%
                        </span>
                        <span className="pkg-report-score-label">Score</span>
                    </div>
                    <div className="pkg-report-verdict-block">
                        <div className={`pkg-report-verdict-tag ${result.is_compliant ? "pass" : "fail"}`}>
                            {result.is_compliant ? "✓ Compliant" : "✕ Non-Compliant"}
                        </div>
                        <p className="pkg-report-summary-text">{result.summary}</p>
                    </div>
                </div>
            </div>

            {/* Non-conformances */}
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

            {/* Requirement findings */}
            <ReportSection title={isFiltered ? `Requirement Findings (Filtered)` : "Requirement Findings"}>
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
                            {findings.map((f, i) => (
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
                            {findings.length === 0 && (
                                <tr><td colSpan={3} className="pkg-findings-empty">No findings match the selected submittal.</td></tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </ReportSection>

            {/* Missing items */}
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

            {/* Recommendations */}
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

            {/* Reviewer notes */}
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
