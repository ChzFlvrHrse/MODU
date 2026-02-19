import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { CircularProgress } from '@mui/material'
import { Project } from '../../../types/types';
import './Projects.css';

import UploadSpec from '../UploadSpec/UploadSpec';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function Projects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [projectNameError, setProjectNameError] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");

  const fetchProjects = async () => {
    const response = await fetch(`${BACKEND_URL}/api/spec/projects`);
    const data = await response.json();
    setProjects(data.projects ?? []);
  };

  function formatDate(iso: string) {
    try {
      return new Date(iso).toLocaleString();
    } catch {
      return iso;
    }
  }

  function shortId(id: string) {
    if (!id) return "";
    return `${id.slice(0, 8)}…${id.slice(-4)}`;
  }

  const handleUpload = async (files: File[]) => {
    setIsUploading(true);
    const formData = new FormData();
    files.forEach((f) => formData.append("pdf", f, f.name));

    const response = await fetch(`${BACKEND_URL}/api/spec/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) throw new Error(await response.text());
    console.log("upload response", await response.json());
    setIsUploading(false);
  };

  useEffect(() => {
    // Run fetchProjects every 10 seconds
    const interval = setInterval(() => {
      fetchProjects();
      console.log("projects", projects);
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    fetchProjects();
  }, []);

  return (
    <div className="projects-page">
      <div className="projects-header">
        <h1 className="projects-title">Projects</h1>
        <p className="projects-subtitle">Your recent spec runs and their status.</p>
      </div>

      <div className="projects-grid">
        {projects?.map((p) => (
          <Link
            key={p.spec_id}
            to={`/projects/${p.spec_id}`}
            className="project-card"
          >
            <div className="project-card-top">
              <span className={`pill pill-${p.status}`}>
                {p.status.toUpperCase()}
              </span>
              <div className="project-card-header">
                <span className="project-name">{p.project_name}</span>
              </div>
              <span className="project-id" title={p.spec_id}>
                {shortId(p.spec_id)}
              </span>
            </div>

            <div className="project-metrics">
              <div className="metric">
                <div className="metric-label">Divisions</div>
                <div className="metric-value">{p.total_divisions ?? "-"}</div>
              </div>
              <div className="metric">
                <div className="metric-label">Sections</div>
                <div className="metric-value">{p.total_sections ?? "-"}</div>
              </div>
              <div className="metric">
                <div className="metric-label">Primary</div>
                <div className="metric-value">{p.sections_with_primary ?? "-"}</div>
              </div>
            </div>

            <div className="project-card-bottom">
              <div className="meta">
                <span className="meta-label">Updated</span>
                <span className="meta-value">{formatDate(p.updated_at)}</span>
              </div>
              <div className="meta">
                <span className="meta-label">Errors</span>
                <span className="meta-value">{p.errors ?? 0}</span>
              </div>
            </div>
          </Link>
        ))}
      </div>

      {projects.length === 0 && (
        <div className="empty-state">
          <div className="empty-title">No projects yet</div>
          <div className="empty-subtitle">Run your first spec parse to see it here.</div>
        </div>
      )}

      <UploadSpec handleUpload={handleUpload} isUploading={isUploading} />
    </div>
  );
}
