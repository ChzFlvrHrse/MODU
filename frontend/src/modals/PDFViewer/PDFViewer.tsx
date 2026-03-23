import React from 'react';
import { CircularProgress } from "@mui/material";
import { Close } from '@mui/icons-material';
import './PDFViewer.css';

interface PDFPage {
    bytes: string;
    media_type: string;
}

interface PDFViewerProps {
    pdfPages: PDFPage[];
    loading: boolean;
    onClose: () => void;
}

export default function PDFViewer({ pdfPages, loading, onClose }: PDFViewerProps) {
    if (loading) {
        return (
            <div className="pdf-viewer-overlay">
                <div className="pdf-viewer-state-card">
                    <CircularProgress size={22} sx={{ color: '#4a9eff' }} />
                    <span>Loading PDF pages...</span>
                </div>
            </div>
        );
    }

    if (pdfPages.length === 0) {
        return (
            <div className="pdf-viewer-overlay">
                <div className="pdf-viewer-state-card">
                    <span>No PDF pages found.</span>
                </div>
            </div>
        );
    }

    return (
        <div className="pdf-viewer-overlay" onClick={onClose}>
            <div className="pdf-viewer-modal" onClick={(e) => e.stopPropagation()}>
                <div className="pdf-viewer-header">
                    <div className="pdf-viewer-header-left">
                        <span className="pdf-viewer-title">PDF Viewer</span>
                        <span className="pdf-viewer-count">
                            {pdfPages.length} {pdfPages.length === 1 ? 'page' : 'pages'}
                        </span>
                    </div>

                    <button
                        className="pdf-viewer-close-button"
                        onClick={onClose}
                        aria-label="Close PDF viewer"
                        type="button"
                    >
                        <Close />
                    </button>
                </div>

                <div className="pdf-viewer-scroll-area">
                    <div className="pdf-viewer-pages">
                        {pdfPages.map((pdfPage, index) => (
                            <section
                                key={`page_${index + 1}`}
                                className="pdf-viewer-page-section"
                                aria-label={`PDF page ${index + 1}`}
                            >
                                <div className="pdf-viewer-page-label">
                                    Page {index + 1}
                                </div>

                                <img
                                    src={`data:${pdfPage.media_type};base64,${pdfPage.bytes}`}
                                    alt={`PDF page ${index + 1}`}
                                    className="pdf-viewer-page-image"
                                    loading="lazy"
                                />
                            </section>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
