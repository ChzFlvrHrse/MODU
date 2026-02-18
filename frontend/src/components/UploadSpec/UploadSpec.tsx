import React, { useRef, useState } from "react";
import type { DragEvent, ChangeEvent } from "react";
import { CircularProgress } from "@mui/material";
import "./UploadSpec.css";

interface UploadSpecProps {
    handleUpload: (files: File[]) => Promise<void> | void;
    isUploading: boolean;
}

export default function UploadSpec({ handleUpload, isUploading }: UploadSpecProps) {
    const inputRef = useRef<HTMLInputElement>(null);
    const [isDragging, setIsDragging] = useState(false);

    // keep these if you plan to use them later
    const [projectName, setProjectName] = useState("");
    const [projectNameError, setProjectNameError] = useState("");

    // ✅ store as File[] (much easier than FileList)
    const [files, setFiles] = useState<File[]>([]);
    const [error, setError] = useState("");

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

    //   if (isUploading) {
    //     return (
    //       <div className="upload-container">
    //         <CircularProgress />
    //       </div>
    //     );
    //   }

    return (
        <div className="upload-container">
            <div className="upload-title">Upload a new spec</div>
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
                    {isUploading ? <CircularProgress size={20} color="inherit"/> : "Upload"}
                </button>
                {isUploading && <h5 className="upload-button-text">Uploading {files.length} PDF(s). This may take a few minutes.</h5>}
            </div>
        </div>
    );
}
