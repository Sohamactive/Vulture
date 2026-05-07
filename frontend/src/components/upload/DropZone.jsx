import React, { useState, useRef } from 'react';
import { UploadCloud, Link as LinkIcon } from 'lucide-react';
import CyberButton from '../ui/CyberButton';
import { useScanStore } from '../../store/scanStore';

export default function DropZone({ onUpload }) {
  const [isDragging, setIsDragging] = useState(false);
  const [url, setUrl] = useState('');
  const fileInputRef = useRef(null);
  
  const { setUploadedFile, setRepoUrl } = useScanStore();

  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = (file) => {
    setUploadedFile(file);
    if (onUpload) onUpload('file');
  };

  const handleUrlSubmit = (e) => {
    e.preventDefault();
    if (url.trim()) {
      setRepoUrl(url.trim());
      if (onUpload) onUpload('url');
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div 
        className={`relative border-2 border-dashed p-12 text-center transition-all duration-300 bg-[var(--bg-panel)] ${
          isDragging 
            ? 'border-[var(--cyan)] shadow-[0_0_30px_rgba(0,245,255,0.2)] bg-[#00f5ff05]' 
            : 'border-[var(--border)] hover:border-[var(--cyan-dim)] hover:shadow-[0_0_15px_rgba(0,245,255,0.1)]'
        }`}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <input 
          type="file" 
          ref={fileInputRef} 
          onChange={handleFileChange} 
          className="hidden" 
          accept=".zip,.tar.gz" 
        />
        
        <div className="flex flex-col items-center justify-center">
          <UploadCloud 
            size={48} 
            className={`mb-4 transition-colors ${isDragging ? 'text-[var(--cyan)]' : 'text-[var(--text-dim)]'}`} 
          />
          <h3 className="text-xl font-bold mb-2">DROP CODEBASE HERE</h3>
          <p className="text-[var(--text-dim)] mb-6 text-sm">Supports .zip and .tar.gz files up to 50MB</p>
          
          <CyberButton onClick={() => fileInputRef.current?.click()} className="text-sm py-2 px-4">
            Select File
          </CyberButton>
        </div>
      </div>
      
      <div className="flex items-center my-6">
        <div className="flex-grow h-px bg-[var(--border)]"></div>
        <span className="px-4 text-[var(--text-dim)] text-xs uppercase tracking-widest">OR PASTE REPOSITORY</span>
        <div className="flex-grow h-px bg-[var(--border)]"></div>
      </div>
      
      <form onSubmit={handleUrlSubmit} className="flex gap-2">
        <div className="relative flex-grow">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <LinkIcon size={16} className="text-[var(--text-dim)]" />
          </div>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://github.com/user/repo"
            className="w-full bg-[var(--bg-panel)] border border-[var(--border)] text-[var(--text-primary)] px-10 py-3 focus:outline-none focus:border-[var(--cyan)] transition-colors font-mono text-sm"
          />
        </div>
        <CyberButton type="submit" variant="amber" className="text-sm py-2 px-6">
          Scan URL
        </CyberButton>
      </form>
    </div>
  );
}
