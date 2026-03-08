import React, { useState, useEffect, useCallback } from 'react';
import ReactDOM from 'react-dom';
import { CircularProgress } from "@mui/material";
import { Close, Delete, Add, ChevronRight } from '@mui/icons-material';
import { toast } from 'react-hot-toast';
import { useNavigate } from 'react-router-dom';
import './SectionModal.css';

interface SpecSummary {
    id: number;
    section_id: number;
    section_number: string;
    section_title: string;
    spec_id: string;
    overview: string;
    key_requirements: string;
    materials: string;
    related_sections: string;
    submittals: string;
    testing: string;
    pages_summarized: string;
    pages_not_summarized: string;
    created_at: string;
    updated_at: string;
}

interface SubmittalPackage {
    id: number;
    package_name: string;
    company_name: string | null;
    status: string;
    compliance_score: number | null;
    created_at: string;
}

interface SectionModalProps {
    spec_id: string;
    section_number: string;
    section_title: string;
    section_id: number;
    onClose: () => void;
}

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const parseJsonField = (field: string): string[] => {
    try {
        const parsed = JSON.parse(field);
        return Array.isArray(parsed) ? parsed : [];
    } catch {
        return [];
    }
};

type TabKey = 'overview' | 'key_requirements' | 'materials' | 'related_sections' | 'submittals' | 'testing' | 'packages';

const TAB_CONFIG: { key: TabKey; label: string }[] = [
    { key: 'overview', label: 'Overview' },
    { key: 'key_requirements', label: 'Requirements' },
    { key: 'materials', label: 'Materials' },
    { key: 'related_sections', label: 'Related Sections' },
    { key: 'submittals', label: 'Submittals' },
    { key: 'testing', label: 'Testing' },
    { key: 'packages', label: 'Packages' },
];

function EmptyState({ label }: { label: string }) {
    return (
        <div className="sm-empty">
            <span className="sm-empty-icon">∅</span>
            <p>No {label.toLowerCase()} specified for this section.</p>
        </div>
    );
}

function ListTab({ items, label }: { items: string[]; label: string }) {
    if (!items.length) return <EmptyState label={label} />;
    return (
        <ul className="sm-list">
            {items.map((item, i) => (
                <li key={i} className="sm-list-item">
                    <span className="sm-list-index">{String(i + 1).padStart(2, '0')}</span>
                    <span className="sm-list-text">{item}</span>
                </li>
            ))}
        </ul>
    );
}

function PackagesTab({
    section_number,
    section_id,
    spec_id,
    section_title,
    onCreatePackage,
}: {
    section_number: string;
    section_id: number;
    spec_id: string;
    section_title: string;
    onCreatePackage: () => void;
}) {
    const [packages, setPackages] = useState<SubmittalPackage[]>([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    const fetchPackages = async () => {
        try {
            const res = await fetch(`${BACKEND_URL}/api/submittal/sections_packages/${section_id}`);
            const data = await res.json();
            setPackages(data.packages ?? []);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchPackages();
    }, [section_id]);

    if (loading) {
        return (
            <div className="sm-packages-loading">
                <CircularProgress size={20} sx={{ color: '#4a9eff' }} />
            </div>
        );
    }

    if (!packages.length) {
        return (
            <div className="sm-packages-empty">
                <span className="sm-empty-icon">∅</span>
                <p>No packages yet for this section.</p>
                <button className="sm-create-package-cta" onClick={onCreatePackage}>
                    <Add fontSize="small" /> Create your first package
                </button>
            </div>
        );
    }

    return (
        <div className="sm-packages-list">
            {packages.map((pkg) => (
                <button
                    key={pkg.id}
                    className="sm-package-row"
                    onClick={() => navigate(`/packages/${spec_id}/${pkg.id}?section_number=${section_number}&section_title=${section_title}&section_id=${section_id}`)}
                    >
                    <div className="sm-package-row-left">
                        <span className="sm-package-name">{pkg.package_name}</span>
                        {pkg.company_name && (
                            <span className="sm-package-company">{pkg.company_name}</span>
                        )}
                    </div>
                    <div className="sm-package-row-right">
                        {pkg.compliance_score !== null && (
                            <span className={`sm-package-score ${pkg.compliance_score >= 0.7 ? 'score-good' : pkg.compliance_score >= 0.4 ? 'score-warn' : 'score-bad'}`}>
                                {Math.round(pkg.compliance_score * 100)}%
                            </span>
                        )}
                        <span className={`sm-package-status status-${pkg.status ?? 'none'}`}>
                            COMPLIANCE CHECK {pkg.status?.toUpperCase() ?? 'NONE'}
                        </span>
                        <ChevronRight fontSize="small" sx={{ color: 'rgba(255,255,255,0.25)' }} />
                    </div>
                </button>
            ))}
        </div>
    );
}

function CreatePackageInline({
    section_id,
    spec_id,
    onCancel,
    onCreated,
}: {
    section_id: number;
    spec_id: string;
    onCancel: () => void;
    onCreated: (package_id: number) => void;
}) {
    const [packageName, setPackageName] = useState('');
    const [company, setCompany] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleCreate = async () => {
        if (!packageName.trim()) {
            setError('Package name is required.');
            return;
        }
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${BACKEND_URL}/api/submittal/create_submittal_package`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    section_id,
                    spec_id,
                    package_name: packageName.trim(),
                    company_name: company.trim() || null,
                }),
            });
            const data = await res.json();
            if (!res.ok || data.error) {
                setError(data.error ?? 'Failed to create package.');
                return;
            }
            setTimeout(() => {
                onCreated(data.package_id);
            }, 3000);
        } catch {
            setError('Network error. Please try again.');
        } finally {
            setLoading(false);
        }
    };


    return (
        <div className="sm-create-inline">
            <p className="sm-create-inline-title">New Package</p>
            <div className="sm-create-inline-fields">
                <div className="sm-create-inline-field">
                    <label className="sm-create-inline-label">
                        Package Name <span className="sm-required">*</span>
                    </label>
                    <input
                        className="sm-create-inline-input"
                        placeholder="e.g. Unit Masonry Submittal Rev 1"
                        value={packageName}
                        autoFocus
                        onChange={(e) => { setPackageName(e.target.value); if (error) setError(null); }}
                        onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                    />
                </div>
                <div className="sm-create-inline-field">
                    <label className="sm-create-inline-label">
                        Company <span className="sm-optional">Optional</span>
                    </label>
                    <input
                        className="sm-create-inline-input"
                        placeholder="e.g. Victory Steel Company"
                        value={company}
                        onChange={(e) => setCompany(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                    />
                </div>
            </div>
            {error && <p className="sm-create-inline-error">{error}</p>}
            <div className="sm-create-inline-actions">
                <button className="sm-create-inline-cancel" onClick={onCancel} disabled={loading}>
                    Cancel
                </button>
                <button
                    className={`sm-create-inline-submit ${loading ? 'loading' : ''}`}
                    onClick={handleCreate}
                    disabled={loading || !packageName.trim()}
                >
                    {loading ? "Creating Package..." : 'Create Package +'}
                </button>
            </div>
        </div>
    );
}

export default function SectionModal({ spec_id, section_number, section_title, section_id, onClose }: SectionModalProps) {
    const [summary, setSummary] = useState<SpecSummary | null | undefined>(null);
    const [activeTab, setActiveTab] = useState<TabKey>('overview');
    const [animKey, setAnimKey] = useState(0);
    const [showCreatePackage, setShowCreatePackage] = useState(false);
    const navigate = useNavigate();

    const fetchSummary = async () => {
        const response = await fetch(`${BACKEND_URL}/api/summary/section_summary/${section_id}`);
        const data = await response.json();
        setSummary(data.section_summary || data.existing_summary);
    };

    const handleKeyDown = useCallback((e: KeyboardEvent) => {
        if (e.key === 'Escape') onClose();
    }, [onClose]);

    const handleDeleteSummary = async (summary_id: number) => {
        const response = await fetch(`${BACKEND_URL}/api/summary/delete/${section_id}/${summary_id}`, {
            method: 'DELETE',
        });
        const data = await response.json();
        if (response.ok) {
            toast.success('Section summary deleted successfully');
            onClose();
        } else {
            toast.error(data.message || 'Error deleting section summary');
        }
    };

    const handlePackageCreated = (package_id: number) => {
        onClose();
        navigate(`/packages/${spec_id}/${package_id}?section_number=${section_number}&section_title=${section_title}&section_id=${section_id}`);
    };

    const handleCreatePackageClick = () => {
        setActiveTab('packages');
        setShowCreatePackage(true);
    };

    useEffect(() => { fetchSummary(); }, []);
    useEffect(() => {
        document.addEventListener('keydown', handleKeyDown);
        document.body.style.overflow = 'hidden';
        return () => {
            document.removeEventListener('keydown', handleKeyDown);
            document.body.style.overflow = '';
        };
    }, [handleKeyDown]);

    const handleTabChange = (key: TabKey) => {
        setActiveTab(key);
        setAnimKey(k => k + 1);
        if (key !== 'packages') setShowCreatePackage(false);
    };

    if (!summary) {
        return ReactDOM.createPortal(
            <div className="sm-overlay" onClick={onClose}>
                <div className="sm-loading" onClick={e => e.stopPropagation()}>
                    <CircularProgress size={28} sx={{ color: '#4a9eff' }} />
                    <span>Loading section summary…</span>
                </div>
            </div>,
            document.body
        );
    }

    const pages = parseJsonField(summary.pages_summarized);

    const renderTabContent = () => {
        switch (activeTab) {
            case 'overview':
                return (
                    <div className="sm-overview">
                        <p className="sm-overview-text">{summary.overview}</p>
                        {pages.length > 0 && (
                            <div className="sm-pages">
                                <span className="sm-pages-label">Pages Referenced</span>
                                <div className="sm-pages-chips">
                                    {pages.map(p => (
                                        <span key={p} className="sm-page-chip">{p}</span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                );
            case 'key_requirements':
                return <ListTab items={parseJsonField(summary.key_requirements)} label="Requirements" />;
            case 'materials':
                return <ListTab items={parseJsonField(summary.materials)} label="Materials" />;
            case 'related_sections':
                return <ListTab items={parseJsonField(summary.related_sections)} label="Related Sections" />;
            case 'submittals':
                return <ListTab items={parseJsonField(summary.submittals)} label="Submittals" />;
            case 'testing':
                return <ListTab items={parseJsonField(summary.testing)} label="Testing" />;
            case 'packages':
                return showCreatePackage ? (
                    <CreatePackageInline
                        section_id={summary.section_id}
                        spec_id={spec_id}
                        onCancel={() => setShowCreatePackage(false)}
                        onCreated={handlePackageCreated}
                    />
                ) : (
                    <PackagesTab
                        spec_id={spec_id}
                        section_id={summary.section_id}
                        section_number={summary.section_number}
                        section_title={summary.section_title}
                        onCreatePackage={() => setShowCreatePackage(true)}
                    />
                );
        }
    };

    const getTabCount = (key: TabKey): number | null => {
        if (key === 'overview' || key === 'packages') return null;
        const counts: Record<string, number> = {
            key_requirements: parseJsonField(summary.key_requirements).length,
            materials: parseJsonField(summary.materials).length,
            related_sections: parseJsonField(summary.related_sections).length,
            submittals: parseJsonField(summary.submittals).length,
            testing: parseJsonField(summary.testing).length,
        };
        return counts[key] ?? null;
    };

    return ReactDOM.createPortal(
        <div className="sm-overlay" onClick={onClose}>
            <div className="sm-root" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="sm-header">
                    <div className="sm-header-left">
                        <span className="sm-section-number">{summary.section_number}</span>
                        <h2 className="sm-section-title">{summary.section_title}</h2>
                        <button className="sm-delete-btn" onClick={() => handleDeleteSummary(summary.id)} aria-label="Delete">
                            <Delete fontSize="small" />
                        </button>
                    </div>
                    <div className="sm-header-right">
                        <button className="sm-create-package-btn" onClick={handleCreatePackageClick}>
                            <Add fontSize="small" /> Create Package
                        </button>
                        <span className="sm-spec-id">SPEC {summary.spec_id.slice(0, 8).toUpperCase()}</span>
                        <button className="sm-close-btn" onClick={onClose} aria-label="Close">
                            <Close fontSize="small" />
                        </button>
                    </div>
                </div>

                {/* Tab Bar */}
                <div className="sm-tabs" role="tablist">
                    {TAB_CONFIG.map(({ key, label }) => {
                        const count = getTabCount(key);
                        const isEmpty = count !== null && count === 0;
                        return (
                            <button
                                key={key}
                                role="tab"
                                aria-selected={activeTab === key}
                                className={`sm-tab ${activeTab === key ? 'sm-tab--active' : ''} ${isEmpty ? 'sm-tab--empty' : ''} ${key === 'packages' ? 'sm-tab--packages' : ''}`}
                                onClick={() => handleTabChange(key)}
                            >
                                <span className="sm-tab-label">{label}</span>
                                {count !== null && (
                                    <span className={`sm-tab-badge ${count === 0 ? 'sm-tab-badge--zero' : ''}`}>
                                        {count}
                                    </span>
                                )}
                            </button>
                        );
                    })}
                </div>

                {/* Content */}
                <div className="sm-content" key={animKey} role="tabpanel">
                    {renderTabContent()}
                </div>
            </div>
        </div>,
        document.body
    );
}
