import React, { useEffect, useRef, useState } from "react";
import type { DragEvent, ChangeEvent } from "react";
import "./UploadSpec.css";

// MUI Icons
import { CircularProgress } from "@mui/material";
import CloseIcon from '@mui/icons-material/Close';
import UploadIcon from '@mui/icons-material/Upload';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

interface UploadSpecProps {
    setProjectsComplete: (projectsComplete: boolean) => void;
}

export default function UploadSpec({ setProjectsComplete }: UploadSpecProps) {
    const [isUploading, setIsUploading] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);
    const [isDragging, setIsDragging] = useState(false);
    const [show, setShow] = useState(false);
    const uploadContainerRef = useRef<HTMLDivElement>(null);

    // keep these if you plan to use them later
    // const [projectName, setProjectName] = useState("");
    // const [projectNameError, setProjectNameError] = useState("");

    // ✅ store as File[] (much easier than FileList)
    const [files, setFiles] = useState<File[]>([]);
    const [error, setError] = useState("");


    const handleUpload = async (files: File[]) => {
        setIsUploading(true);
        setProjectsComplete(false);
        const formData = new FormData();
        files.forEach((f) => formData.append("pdf", f, f.name));

        const response = await fetch(`${BACKEND_URL}/api/spec/upload`, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) throw new Error(await response.text());
        console.log("upload response", await response.json());
        setShow(false);
        setFiles([]);
        setError("");
        setIsUploading(false);
    };

    const pickFile = () => inputRef.current?.click();

    const setPdfFiles = (incoming: FileList | File[] | null) => {
        setError("");
        if (!incoming) return;

        const arr = Array.isArray(incoming) ? incoming : Array.from(incoming);

        // keep only PDFs
        const pdfs = arr.filter((f) => {
            const nameOk = f.name.toLowerCase().endsWith(".pdf");
            const typeOk = f.type === "application/pdf"; // may be empty in some browsers, so we also check name
            return typeOk || nameOk;
        });

        if (pdfs.length === 0) {
            setFiles([]);
            setError("Please upload PDF files only.");
            return;
        }

        // If you want to reject non-pdfs when mixed:
        if (pdfs.length !== arr.length) {
            setError("Some files were ignored (only PDFs are allowed).");
        }

        setFiles(pdfs);
    };

    const onChange = (e: ChangeEvent<HTMLInputElement>) => {
        setPdfFiles(e.target.files);
        // allow re-selecting same file(s)
        if (inputRef.current) inputRef.current.value = "";
    };

    const onDrop = (e: DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
        setPdfFiles(e.dataTransfer.files);
    };

    const onDragOver = (e: DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(true);
    };

    const onDragLeave = (e: DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
    };

    const onUploadClick = async () => {
        if (!files.length) {
            setError("Choose at least one PDF first.");
            return;
        }
        await handleUpload(files);
    };

    const handleClose = () => {
        setShow(false);
        setFiles([]);
        setError("");
        return;
    };

    useEffect(() => {
        if (!show) return;

        const handleClickOutside = (event: MouseEvent) => {
            if (uploadContainerRef.current &&
                !uploadContainerRef.current.contains(event.target as Node)) {
                setShow(false);
                setFiles([]);
                setError("");
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [show]);

    if (!show) {
        return (
            <div className="upload-fab" onClick={() => setShow(true)}>
                <UploadIcon fontSize="large" />
                <span className="fab-tooltip">Upload New Spec</span>
            </div>
        )
    }

    return (
        <div className="upload-container" ref={uploadContainerRef}>
            <div className="upload-container-header">
                <div className="upload-title">Upload a new spec</div>
                <CloseIcon className="close-icon" onClick={handleClose} />
            </div>
            <div className="upload-subtitle">Drop PDF(s) here or click to browse.</div>

            <div
                className={`dropzone ${isDragging ? "dropzone-dragging" : ""}`}
                onClick={pickFile}
                onDrop={onDrop}
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
                role="button"
                tabIndex={0}
            >
                <div className="dropzone-inner">
                    <div className="dropzone-icon">⬆️</div>

                    <div className="dropzone-text">
                        {files.length ? (
                            <>
                                <div className="dropzone-file">
                                    {files.length === 1 ? files[0].name : `${files.length} PDFs selected`}
                                </div>

                                <div className="dropzone-hint">
                                    {files.length <= 3
                                        ? files.map((f) => f.name).join(", ")
                                        : `${files.slice(0, 3).map((f) => f.name).join(", ")} +${files.length - 3} more`}
                                </div>

                                <div className="dropzone-hint">Click to replace</div>
                            </>
                        ) : (
                            <>
                                <div className="dropzone-primary">Drag & drop PDF(s)</div>
                                <div className="dropzone-hint">or click to choose files</div>
                            </>
                        )}
                    </div>
                </div>

                <input
                    ref={inputRef}
                    type="file"
                    accept="application/pdf"
                    multiple
                    onChange={onChange}
                    style={{ display: "none" }}
                />
            </div>

            {error && <div className="upload-error">{error}</div>}

            <div className="upload-button-container">
                <button className="upload-button" onClick={onUploadClick} disabled={isUploading}>
                    {isUploading ? <CircularProgress size={20} color="inherit" /> : "Upload"}
                </button>
                {isUploading && <h5 className="upload-button-text">Uploading {files.length} PDF(s). This may take a few minutes.</h5>}
            </div>
        </div>
    );
}
