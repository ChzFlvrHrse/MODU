import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { Project } from '../../../types/types';
import CircularProgress from '@mui/material/CircularProgress';
import { DeleteRounded } from '@mui/icons-material';
import DeleteModal from '../../modals/DeleteModal/DeleteModal';
import './Projects.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

interface ProjectsProps {
  projectsComplete: boolean;
  setProjectsComplete: (projectsComplete: boolean) => void;
}

export default function Projects({ projectsComplete, setProjectsComplete }: ProjectsProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  const [projectName, setProjectName] = useState("");
  const [projectNameError, setProjectNameError] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");

  const [specId, setSpecId] = useState("");
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);

  const checkAllProjectsStatus = (projects_data: Project[]) => {
    const allComplete = projects_data.every(project =>
      project.classification_status === "complete" &&
      project.summary_status === "complete" &&
      project.errors === 0
    );
    setProjectsComplete(allComplete);
  };

  const fetchProjects = async () => {
    const response = await fetch(`${BACKEND_URL}/api/spec/projects`);
    const data = await response.json();
    const projects_data = data.projects ?? [];
    setProjects(projects_data);
    checkAllProjectsStatus(projects_data);
  };

  const handleDeleteProject = async (e: React.MouseEvent<HTMLButtonElement>, spec_id: string) => {
    e.stopPropagation();
    const response = await fetch(`${BACKEND_URL}/api/spec/delete_project/${spec_id}`, {
      method: "DELETE",
    });
    const data = await response.json();
    if (data.error) {
      toast.error(data.error);
      return;
    }
    toast.success("Project deleted successfully");
    fetchProjects();
  };

  function formatDate(iso: string) {
    try {
      return new Date(iso).toLocaleString();
    } catch {
      return iso;
    }
  }

  function formatDuration(created: string, updated: string) {
    try {
      const ms = new Date(updated).getTime() - new Date(created).getTime();
      if (isNaN(ms) || ms < 0) return "—";
      const totalSeconds = Math.floor(ms / 1000);
      const minutes = Math.floor(totalSeconds / 60);
      const seconds = totalSeconds % 60;
      if (minutes === 0) return `${seconds}s`;
      return `${minutes}m ${seconds}s`;
    } catch {
      return "—";
    }
  }

  function shortId(id: string) {
    if (!id) return "";
    return `${id.slice(0, 8)}…${id.slice(-4)}`;
  }

  function getStatusIcon(status: string) {
    const statusMap: Record<string, React.ReactNode> = {
      'complete': '✓',
      'pending': <CircularProgress size={10} sx={{ color: 'inherit' }} />,
      'error': '✕',
      'unknown': '○',
    };
    return statusMap[status] ?? <CircularProgress size={10} sx={{ color: 'inherit' }} />;
  }

  const showDeleteModal = (spec_id: string) => {
    setSpecId(spec_id);
    setDeleteModalOpen(true);
  };

  useEffect(() => {
    if (projectsComplete) return;
    const interval = setInterval(fetchProjects, 10000);
    return () => clearInterval(interval);
  }, [projectsComplete]);

  useEffect(() => {
    fetchProjects();
  }, []);

  return (
    <>
      {deleteModalOpen && (
        <DeleteModal
          item_type="project"
          spec_id={specId}
          onClose={() => setDeleteModalOpen(false)}
        />
      )}

      <div className="projects-page">
        <div className="projects-header">
          <h1 className="projects-title">Projects</h1>
          <p className="projects-subtitle">Your recent spec runs and their status.</p>
        </div>

        <div className="projects-grid">
          {projects?.map((p) => (
            <Link
              key={p.spec_id}
              to={`/projects/${p.spec_id}?project_name=${p.project_name}`}
              title={p.project_name}
              className="project-card"
            >
              {/* Row 1: Name + ID */}
              <div className="project-card-header">
                <div className="project-card-header-left">
                  <span className="project-name">{p.project_name}</span>
                  <span className="project-id" title={p.spec_id}>
                    {shortId(p.spec_id)}
                  </span>
                </div>
                <button
                  className="delete-project-btn"
                  title="Delete project"
                  onClick={() => showDeleteModal(p.spec_id)}
                >
                  <DeleteRounded />
                </button>
              </div>

              {/* Row 2: Status pills */}
              <div className="project-card-status">
                <span className={`pill pill-${p.classification_status}`}>
                  {getStatusIcon(p.classification_status)} {p.classification_status === "complete" ? "CLASSIFICATIONS" : "CLASSIFYING..."}
                </span>
                <span className={`pill pill-${p.summary_status}`}>
                  {getStatusIcon(p.summary_status)} SUMMARIES
                </span>
              </div>

              {/* Row 3: Inline metrics */}
              <div className="project-metrics">
                <div className="metric">
                  <div className="metric-value">{p.total_divisions ?? "—"}</div>
                  <div className="metric-label">Divisions</div>
                </div>
                <div className="metric-divider" />
                <div className="metric">
                  <div className="metric-value">{p.total_sections ?? "—"}</div>
                  <div className="metric-label">Sections</div>
                </div>
                <div className="metric-divider" />
                <div className="metric">
                  <div className="metric-value">{p.sections_with_primary ?? "—"}</div>
                  <div className="metric-label">Primary</div>
                </div>
                <div className="metric-divider" />
                <div className="metric">
                  <div className="metric-value">{p.sections_with_reference ?? "—"}</div>
                  <div className="metric-label">References</div>
                </div>
              </div>

              {/* Row 4: Bottom meta */}
              <div className="project-card-bottom">
                <div className="meta">
                  <span className="meta-label">Created</span>
                  <span className="meta-value">{formatDate(p.created_at)}</span>
                </div>
                <div className="meta">
                  <span className="meta-label">Duration</span>
                  <span className="meta-value">{formatDuration(p.created_at, p.updated_at)}</span>
                </div>
                <div className="meta meta-right">
                  <span className="meta-label">Errors</span>
                  <span
                    className="meta-value"
                    style={{ color: p.errors ? 'rgba(231,76,60,0.9)' : 'rgba(255,255,255,0.85)' }}
                  >
                    {p.errors ?? 0}
                  </span>
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
      </div>
    </>
  );
}
