import React, { useState, useEffect } from 'react';
import { CircularProgress } from '@mui/material'
import { Project } from '../../../types/types';
import './Projects.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function Projects() {
  const [projects, setProjects] = useState<Project[]>([]);

  const fetchProjects = async () => {
    const response = await fetch(`${BACKEND_URL}/api/spec/projects`);
    const data = await response.json();
    setProjects(data.projects);
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  // if (projects.length === 1) {
  //   return (
  //     <div className="Projects-loading">
  //       <CircularProgress />
  //     </div>)
  //     ;
  // }

  return (
    <div className="projects">
      <header className="projects-header">
        <div className="projects-list">
          <h2>Projects</h2>
          {projects.map((project) => (
            <div key={project.spec_id}>
              <button className="project-button">
                {project.spec_id}
              </button>
            </div>
          ))}
        </div>
      </header>
    </div>
  );
}
