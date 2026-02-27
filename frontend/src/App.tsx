import React, { useState } from 'react';
import { Toaster } from 'react-hot-toast';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './index.css';

// Components
import Nav from './components/Nav/Nav';
import Projects from './components/Projects/Projects';
import Sections from './components/Sections/Sections';
import UploadSpec from './components/UploadSpec/UploadSpec';

function App() {
  const [projectsComplete, setProjectsComplete] = useState(true);

  return (
    <React.StrictMode>
      <BrowserRouter>
      <Toaster position="top-right" toastOptions={{ style: { background: '#1a1d26', color: '#fff', border: '1px solid rgba(255,255,255,0.08)' } }} />
        <div className="app-layout">
          <Nav />
          <div className="content">
            <Routes>
              <Route path="/" element={<Navigate to="/projects" />} />
              <Route path="/projects" element={<Projects projectsComplete={projectsComplete} setProjectsComplete={setProjectsComplete} />} />
              <Route path="/projects/:spec_id" element={<Sections />} />
            </Routes>
          </div>
          <UploadSpec setProjectsComplete={setProjectsComplete} />
        </div>
      </BrowserRouter>
    </React.StrictMode>
  );
}

export default App;
