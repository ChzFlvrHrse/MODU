import React, { useRef, useState } from "react";
import type { DragEvent, ChangeEvent } from "react";
import ReactDOM from "react-dom";
import { CircularProgress } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import InsertDriveFileOutlinedIcon from "@mui/icons-material/InsertDriveFileOutlined";
import ClearIcon from "@mui/icons-material/Clear";
import "./UploadSubmittal.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const SUBMITTAL_TYPES: { id: number; label: string }[] = [
    { id: 1042, label: "Shop Drawing" },
    { id: 2187, label: "Product Data" },
    { id: 3561, label: "Material Certification" },
    { id: 4823, label: "Test Report" },
    { id: 5394, label: "Mix Design" },
    { id: 6718, label: "Sample" },
    { id: 7265, label: "Other" },
];

interface UploadSubmittalProps {
    spec_id: string;
    package_id: number;
    package_name: string;
    onClose: () => void;
    onUploaded: () => void;
}

interface FileEntry {
    file: File;
    typeId: number;
}

export default function UploadSubmittal({ spec_id, package_id, package_name, onClose, onUploaded }: UploadSubmittalProps) {
    const inputRef = useRef<HTMLInputElement>(null);
    const [isDragging, setIsDragging] = useState(false);
    const [entries, setEntries] = useState<FileEntry[]>([]);
    const [isUploading, setIsUploading] = useState(false);
    const [error, setError] = useState("");

    const addPdfFiles = (incoming: FileList | null) => {
        setError("");
        if (!incoming || incoming.length === 0) return;
        const arr = Array.from(incoming);
        const pdfs = arr.filter((f) => f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf"));
        if (pdfs.length !== arr.length) setError("Some files were skipped — PDFs only.");
        if (pdfs.length === 0) return;
        setEntries((prev) => {
            const existingNames = new Set(prev.map((e) => e.file.name));
            const newEntries = pdfs
                .filter((f) => !existingNames.has(f.name))
                .map((f) => ({ file: f, typeId: 2187 }));
            return [...prev, ...newEntries];
        });
    };

    const removeFile = (name: string) => setEntries((prev) => prev.filter((e) => e.file.name !== name));

    const setFileType = (name: string, typeId: number) =>
        setEntries((prev) => prev.map((e) => e.file.name === name ? { ...e, typeId } : e));

    const onChange = (e: ChangeEvent<HTMLInputElement>) => {
        addPdfFiles(e.target.files);
        if (inputRef.current) inputRef.current.value = "";
    };

    const onDrop = (e: DragEvent<HTMLDivElement>) => {
        e.preventDefault(); e.stopPropagation();
        setIsDragging(false);
        addPdfFiles(e.dataTransfer.files);
    };

    const onDragOver = (e: DragEvent<HTMLDivElement>) => { e.preventDefault(); setIsDragging(true); };
    const onDragLeave = (e: DragEvent<HTMLDivElement>) => { e.preventDefault(); setIsDragging(false); };

    const handleUpload = async () => {
        if (!entries.length) { setError("Please select at least one PDF."); return; }
        setIsUploading(true);
        setError("");
        try {
            const formData = new FormData();
            entries.forEach((e, i) => {
                formData.append("pdf", e.file, e.file.name);
                formData.append(`submittal_type_id_${i}`, String(e.typeId));
            });
            formData.append("spec_id", spec_id);
            formData.append("package_id", String(package_id));

            const res = await fetch(`${BACKEND_URL}/api/submittal/upload_submittal`, {
                method: "POST",
                body: formData,
            });
            const data = await res.json();
            if (!res.ok || data.error) { setError(data.error ?? "Upload failed."); return; }
            onUploaded();
            setTimeout(() => {
                onClose();
            }, 3000);
        } catch {
            setError("Network error. Please try again.");
            setIsUploading(false);
        }
    };

    const formatSize = (bytes: number) => {
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    return ReactDOM.createPortal(
        <div className="us-overlay" onClick={onClose}>
            <div className="us-modal" onClick={(e) => e.stopPropagation()}>

                {/* Header */}
                <div className="us-header">
                    <div className="us-header-left">
                        <span className="us-title">Upload Submittals</span>
                        <span className="us-package-pill">{package_name}</span>
                    </div>
                    <button className="us-close-btn" onClick={onClose}>
                        <CloseIcon fontSize="small" />
                    </button>
                </div>

                {/* Dropzone */}
                <div
                    className={`us-dropzone ${isDragging ? "dragging" : ""}`}
                    onClick={() => inputRef.current?.click()}
                    onDrop={onDrop}
                    onDragOver={onDragOver}
                    onDragLeave={onDragLeave}
                >
                    <div className="us-dropzone-icon">⬆</div>
                    <div className="us-dropzone-primary">
                        {entries.length > 0 ? "Drop more PDFs or click to add" : "Drag & drop PDFs here"}
                    </div>
                    <div className="us-dropzone-hint">or click to browse</div>
                    <input ref={inputRef} type="file" accept="application/pdf" multiple onChange={onChange} style={{ display: "none" }} />
                </div>

                {/* File list */}
                {entries.length > 0 && (
                    <div className="us-file-list">
                        {entries.map((entry) => (
                            <div key={entry.file.name} className="us-file-row">
                                <InsertDriveFileOutlinedIcon fontSize="small" sx={{ color: "#4a9eff", flexShrink: 0, marginTop: "2px" }} />
                                <div className="us-file-info">
                                    <span className="us-file-name">{entry.file.name}</span>
                                    <span className="us-file-size">{formatSize(entry.file.size)}</span>
                                </div>
                                <select
                                    className="us-file-type-select"
                                    value={entry.typeId}
                                    onChange={(e) => setFileType(entry.file.name, Number(e.target.value))}
                                >
                                    {SUBMITTAL_TYPES.map((t) => (
                                        <option key={t.id} value={t.id}>{t.label}</option>
                                    ))}
                                </select>
                                <button className="us-file-remove" onClick={() => removeFile(entry.file.name)}>
                                    <ClearIcon fontSize="small" />
                                </button>
                            </div>
                        ))}
                    </div>
                )}

                {error && <div className="us-error">{error}</div>}

                {/* Footer */}
                <div className="us-footer">
                    <span className="us-file-count">
                        {entries.length > 0 ? `${entries.length} file${entries.length > 1 ? "s" : ""} selected` : "No files selected"}
                    </span>
                    <div className="us-footer-actions">
                        <button className="us-cancel-btn" onClick={onClose} disabled={isUploading}>Cancel</button>
                        <button
                            className={`us-upload-btn ${isUploading ? "loading" : ""}`}
                            onClick={handleUpload}
                            disabled={isUploading || entries.length === 0}
                        >
                            {isUploading
                                ? <><CircularProgress size={12} sx={{ color: "inherit" }} /> Uploading…</>
                                : `Upload ${entries.length > 0 ? entries.length : ""} PDF${entries.length !== 1 ? "s" : ""}`
                            }
                        </button>
                    </div>
                </div>
            </div>
        </div>,
        document.body
    );
}
