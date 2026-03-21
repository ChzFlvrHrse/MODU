import React, { useState, useEffect, useCallback } from 'react';
import ReactDOM from 'react-dom';
import { CircularProgress } from "@mui/material";
import { Close, Add, ChevronRight } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import UploadSubmittal from '../../components/UploadSubmittal/UploadSubmittal';
import './PackageModal.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

interface SubmittalPackage {
    id: number;
    package_name: string;
    company_name: string | null;
    status: string;
    compliance_score: number | null;
    is_chosen: boolean;
    created_at: string;
}

interface PackagesModalProps {
    spec_id: string;
    section_id: number;
    section_number: string;
    section_title: string;
    onClose: () => void;
}

type View = "list" | "create" | "upload-prompt";

function PackagesList({
    spec_id,
    section_id,
    section_number,
    section_title,
    onCreatePackage,
}: {
    spec_id: string;
    section_id: number;
    section_number: string;
    section_title: string;
    onCreatePackage: () => void;
}) {
    const [packages, setPackages] = useState<SubmittalPackage[]>([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        const fetchPackages = async () => {
            try {
                const res = await fetch(`${BACKEND_URL}/api/submittal/sections_packages/${section_id}`);
                const data = await res.json();
                setPackages(data.packages ?? []);
            } finally {
                setLoading(false);
            }
        };
        fetchPackages();
    }, [section_id]);

    if (loading) {
        return (
            <div className="pm-loading">
                <CircularProgress size={20} sx={{ color: '#4a9eff' }} />
            </div>
        );
    }

    if (!packages.length) {
        return (
            <div className="pm-empty">
                <span className="pm-empty-icon">∅</span>
                <p>No packages yet for this section.</p>
                <button className="pm-create-cta" onClick={onCreatePackage}>
                    <Add fontSize="small" /> Create your first package
                </button>
            </div>
        );
    }

    return (
        <div className="pm-list">
            {packages.map((pkg) => (
                <button
                    key={pkg.id}
                    className="pm-package-row"
                    onClick={() => navigate(
                        `/packages/${spec_id}/${pkg.id}?section_number=${section_number}&section_title=${encodeURIComponent(section_title)}&section_id=${section_id}`
                    )}
                >
                    <div className="pm-package-row-left">
                        <span className="pm-package-name">{pkg.package_name}</span>
                        {pkg.company_name && (
                            <span className="pm-package-company">{pkg.company_name}</span>
                        )}
                    </div>
                    <div className="pm-package-row-right">
                        {pkg.compliance_score !== null && (
                            <span className={`pm-package-score ${pkg.compliance_score >= 0.7 ? 'score-good' : pkg.compliance_score >= 0.4 ? 'score-warn' : 'score-bad'}`}>
                                {Math.round(pkg.compliance_score * 100)}%
                            </span>
                        )}
                        <span className={`pm-package-status ${pkg.is_chosen ? 'status-chosen' : ''}`}>
                            {pkg.is_chosen ? '✓ Final' : <></>}
                        </span>
                        <ChevronRight fontSize="small" sx={{ color: 'rgba(255,255,255,0.25)' }} />
                    </div>
                </button>
            ))}
        </div>
    );
}

function CreatePackageForm({
    section_id,
    spec_id,
    onCancel,
    onCreated,
}: {
    section_id: number;
    spec_id: string;
    onCancel: () => void;
    onCreated: (package_id: number, package_name: string) => void;
}) {
    const [packageName, setPackageName] = useState('');
    const [company, setCompany] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleCreate = async () => {
        if (!packageName.trim()) { setError('Package name is required.'); return; }
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
            onCreated(data.package.id, packageName.trim());
        } catch {
            setError('Network error. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="pm-create-form">
            <p className="pm-create-form-title">New Package</p>
            <div className="pm-create-form-fields">
                <div className="pm-create-form-field">
                    <label className="pm-create-form-label">
                        Package Name <span className="pm-required">*</span>
                    </label>
                    <input
                        className="pm-create-form-input"
                        placeholder="e.g. Unit Masonry Submittal Rev 1"
                        value={packageName}
                        autoFocus
                        onChange={(e) => { setPackageName(e.target.value); if (error) setError(null); }}
                        onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                    />
                </div>
                <div className="pm-create-form-field">
                    <label className="pm-create-form-label">
                        Company <span className="pm-optional">Optional</span>
                    </label>
                    <input
                        className="pm-create-form-input"
                        placeholder="e.g. Victory Steel Company"
                        value={company}
                        onChange={(e) => setCompany(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                    />
                </div>
            </div>
            {error && <p className="pm-create-form-error">{error}</p>}
            <div className="pm-create-form-actions">
                <button className="pm-cancel-btn" onClick={onCancel} disabled={loading}>Cancel</button>
                <button
                    className={`pm-submit-btn ${loading ? 'loading' : ''}`}
                    onClick={handleCreate}
                    disabled={loading || !packageName.trim()}
                >
                    {loading ? 'Creating Package...' : 'Create Package +'}
                </button>
            </div>
        </div>
    );
}

export default function PackagesModal({
    spec_id,
    section_id,
    section_number,
    section_title,
    onClose,
}: PackagesModalProps) {
    const [view, setView] = useState<View>("list");
    const [uploadPackageId, setUploadPackageId] = useState<number | null>(null);
    const [uploadPackageName, setUploadPackageName] = useState<string>("");
    const [showUpload, setShowUpload] = useState(false);

    const handleKeyDown = useCallback((e: KeyboardEvent) => {
        if (e.key === 'Escape') onClose();
    }, [onClose]);

    useEffect(() => {
        document.addEventListener('keydown', handleKeyDown);
        document.body.style.overflow = 'hidden';
        return () => {
            document.removeEventListener('keydown', handleKeyDown);
            document.body.style.overflow = '';
        };
    }, [handleKeyDown]);

    const handleCreated = (package_id: number, package_name: string) => {
        setUploadPackageId(package_id);
        setUploadPackageName(package_name);
        setView("upload-prompt");
    };

    // Skip — just close the modal, no navigation
    const handleSkip = () => {
        onClose();
    };

    // Launch the upload modal on top
    const handleLaunchUpload = () => {
        setShowUpload(true);
    };

    // Upload finished or cancelled — just close everything, no navigation
    const handleUploadClose = () => {
        setShowUpload(false);
        onClose();
    };

    return (
        <>
            {ReactDOM.createPortal(
                <div className="pm-overlay" onClick={onClose}>
                    <div className="pm-root" onClick={(e) => e.stopPropagation()}>
                        <div className="pm-header">
                            <div className="pm-header-left">
                                <span className="pm-section-number">{section_number}</span>
                                <h2 className="pm-section-title">{section_title}</h2>
                            </div>
                            <div className="pm-header-right">
                                {view === "list" && (
                                    <button className="pm-new-btn" onClick={() => setView("create")}>
                                        <Add fontSize="small" /> New Package
                                    </button>
                                )}
                                <button className="pm-close-btn" onClick={onClose}>
                                    <Close fontSize="small" />
                                </button>
                            </div>
                        </div>

                        <div className="pm-content">
                            {view === "list" && (
                                <PackagesList
                                    spec_id={spec_id}
                                    section_id={section_id}
                                    section_number={section_number}
                                    section_title={section_title}
                                    onCreatePackage={() => setView("create")}
                                />
                            )}
                            {view === "create" && (
                                <CreatePackageForm
                                    section_id={section_id}
                                    spec_id={spec_id}
                                    onCancel={() => setView("list")}
                                    onCreated={handleCreated}
                                />
                            )}
                            {view === "upload-prompt" && uploadPackageId && (
                                <div className="pm-upload-prompt">
                                    <div className="pm-upload-prompt-check">✓</div>
                                    <p className="pm-upload-prompt-title">Package Created</p>
                                    <p className="pm-upload-prompt-name">{uploadPackageName}</p>
                                    <p className="pm-upload-prompt-sub">Upload submittals now, or do it later from the package page.</p>
                                    <div className="pm-upload-prompt-actions">
                                        <button className="pm-cancel-btn" onClick={handleSkip}>Skip for now</button>
                                        <button className="pm-submit-btn" onClick={handleLaunchUpload}>Upload Submittals →</button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>,
                document.body
            )}

            {showUpload && uploadPackageId && (
                <UploadSubmittal
                    spec_id={spec_id}
                    package_id={uploadPackageId}
                    package_name={uploadPackageName}
                    onClose={handleUploadClose}
                    onUploaded={handleUploadClose}
                />
            )}
        </>
    );
}
