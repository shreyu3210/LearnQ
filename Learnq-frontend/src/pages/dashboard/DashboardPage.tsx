import React, { useRef, useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { FaCloudUploadAlt, FaYoutube, FaLink } from 'react-icons/fa';
import { fileService } from '../../services/api';
import VideoPlayerPanel from '../../components/video/VideoPlayerPanel';
import '../../assets/styles/Dashboard.css';

/** Parse "HH:MM:SS" to seconds */
function parseTimestamp(ts: string): number {
  const parts = ts.trim().split(':');
  if (parts.length === 3) return parseInt(parts[0]) * 3600 + parseInt(parts[1]) * 60 + parseInt(parts[2]);
  if (parts.length === 2) return parseInt(parts[0]) * 60 + parseInt(parts[1]);
  return parseFloat(ts);
}

const DashboardPage: React.FC = () => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // State for file upload
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [fileStatus, setFileStatus] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  const [videoId, setVideoId] = useState<string | null>(null);

  // State for YouTube
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [isYoutubeLoading, setIsYoutubeLoading] = useState(false);
  const [youtubeStatus, setYoutubeStatus] = useState<{ type: 'success' | 'error', message: string } | null>(null);

  // State for generation
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateStatus, setGenerateStatus] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  const [transcriptionResult, setTranscriptionResult] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'transcript' | 'summary' | 'mcqs'>('transcript');
  const [userName, setUserName] = useState<string | null>(localStorage.getItem('userName'));

  // State for video seek (triggered by clicking timestamps in the transcript)
  const [seekTime, setSeekTime] = useState<number | null>(null);

  // Update username if it changes (e.g. login)
  useEffect(() => {
      const handleAuthChange = () => {
          setUserName(localStorage.getItem('userName'));
      };
      window.addEventListener('auth-change', handleAuthChange);
      return () => window.removeEventListener('auth-change', handleAuthChange);
  }, []);

  // Auto-clear status messages after 5 seconds
  useEffect(() => {
    if (fileStatus) {
      const timer = setTimeout(() => setFileStatus(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [fileStatus]);

  useEffect(() => {
    if (youtubeStatus) {
      const timer = setTimeout(() => setYoutubeStatus(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [youtubeStatus]);

  useEffect(() => {
    if (generateStatus) {
      const timer = setTimeout(() => setGenerateStatus(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [generateStatus]);

  const handleUploadClick = () => {
    if (!isUploading && !isYoutubeLoading) {
      fileInputRef.current?.click();
    }
  };

  const handleGenerate = async () => {
    if (videoId) {
      setIsGenerating(true);
      setGenerateStatus(null);
      try {
        console.log('Generate clicked for:', videoId);
        const response = await fileService.transcribeMedia(videoId);
        console.log('Transcription started:', response);
        
        if (response.status === 'error') {
            const errorMessage = response.data?.model_statuses?.message || 'Unknown error occurred';
            if (errorMessage.includes('No connection could be made') || errorMessage.includes('Triton server')) {
                setGenerateStatus({ type: 'error', message: 'Server is not connected' });
            } else {
                setGenerateStatus({ type: 'error', message: errorMessage });
            }
        } else {
            setGenerateStatus({ type: 'success', message: 'Transcription started successfully!' });
            setTranscriptionResult(response);
        }

      } catch (error: any) {
        console.error('Transcription request failed:', error);
        setGenerateStatus({ type: 'error', message: 'Failed to start transcription.' });
      } finally {
        setIsGenerating(false);
      }
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setIsUploading(true);
      setUploadProgress(0);
      setFileStatus(null);
      setVideoId(null);
      
      try {
        const response = await fileService.uploadMedia(file, (progress) => {
          setUploadProgress(progress);
        });
        
        // Extract video_id from response
        const vId = response.data?.video_id || response.video_id || response.data?.data?.video_id;
        if (vId) {
            setVideoId(vId);
            console.log('Video ID stored:', vId);
        }

        setFileStatus({ type: 'success', message: 'File uploaded successfully!' });
      } catch (error) {
        console.error('Upload failed:', error);
        setFileStatus({ type: 'error', message: 'Failed to upload file. Please try again.' });
      } finally {
        setIsUploading(false);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      }
    }
  };

  const handleYoutubeSubmit = async (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && youtubeUrl.trim()) {
      setIsYoutubeLoading(true);
      setYoutubeStatus(null);
      setVideoId(null);
      
      try {
        const response = await fileService.transcribeYoutube(youtubeUrl);
        setYoutubeStatus({ type: 'success', message: 'YouTube processing complete!' });
        
        const vId = response.data?.video_id || response.video_id || response.data?.data?.video_id;
        if (vId) {
             setVideoId(vId);
             console.log('Video ID stored:', vId);
        }
        
        setYoutubeUrl(''); // Clear input on success

      } catch (error: any) {
        console.error('YouTube submission failed:', error);
        setYoutubeStatus({ type: 'error', message: error.response?.data?.detail || 'Failed to process YouTube URL.' });
      } finally {
        setIsYoutubeLoading(false);
      }
    }
  };

  /**
   * Render the raw transcript string with clickable timestamp badges.
   * Clicking a timestamp seeks the video to that time.
   */
  const renderClickableTranscript = (raw: string) => {
    // Split on timestamp patterns, keeping the delimiters
    const parts = raw.split(/(\[\d{2}:\d{2}:\d{2}\s*-->\s*\d{2}:\d{2}:\d{2}\])/g);
    return parts.map((part, i) => {
      const match = part.match(/\[(\d{2}:\d{2}:\d{2})\s*-->\s*(\d{2}:\d{2}:\d{2})\]/);
      if (match) {
        const seconds = parseTimestamp(match[1]);
        return (
          <span
            key={i}
            className="clickable-timestamp"
            onClick={() => setSeekTime(seconds)}
            title={`Jump to ${match[1]}`}
          >
            {part}
          </span>
        );
      }
      return <span key={i}>{part}</span>;
    });
  };

  // --- RESULTS VIEW: Video player (left) + Card (right) ---
  if (transcriptionResult) {
    return (
      <div className="container-fluid dashboard-container">
        <div className="dashboard-results-layout">
          {/* Video Player — OUTSIDE the card */}
          {videoId && (
            <div className="results-video-side">
              <VideoPlayerPanel
                videoUrl={fileService.getVideoStreamUrl(videoId)}
                transcriptRaw={transcriptionResult.data.timestamp}
                seekTime={seekTime}
              />
            </div>
          )}

          {/* Original card with tabs — UNCHANGED structure */}
          <div className="upload-card results-card-side">
            <div className="w-100 h-100 d-flex flex-column">
              <div className="d-flex justify-content-between align-items-center mb-4">
                <h3 className="m-0">Generation Complete</h3>
                <button 
                  className="btn-secondary py-2 px-3"
                  onClick={() => {
                    setVideoId(null);
                    setTranscriptionResult(null);
                    setFileStatus(null);
                    setYoutubeStatus(null);
                    setGenerateStatus(null);
                    setActiveTab('transcript');
                    setSeekTime(null);
                  }}
                >
                  New Upload
                </button>
              </div>

              {/* Custom Tabs */}
              <div className="custom-tabs mb-4">
                {['transcript', 'summary', 'mcqs'].map((tab) => (
                  <button
                    key={tab}
                    className={`tab-btn ${activeTab === tab ? 'active' : ''}`}
                    onClick={() => setActiveTab(tab as any)}
                  >
                    {tab.charAt(0).toUpperCase() + tab.slice(1)}
                  </button>
                ))}
              </div>

              {/* Tab Content */}
              <div className="tab-content-area">
                {activeTab === 'transcript' && (
                  <div className="content-pane">
                     <h4 className="mb-3">Transcript</h4>
                     <p style={{ whiteSpace: 'pre-line' }}>
                       {videoId
                         ? renderClickableTranscript(transcriptionResult.data.timestamp)
                         : transcriptionResult.data.timestamp
                       }
                     </p>
                  </div>
                )}

                {activeTab === 'summary' && (
                  <div className="content-pane">
                     <h4 className="mb-3">Summary</h4>
                     <ReactMarkdown>{transcriptionResult.data.summary}</ReactMarkdown>
                  </div>
                )}

                {activeTab === 'mcqs' && (
                   <div className="content-pane">
                      <h4 className="mb-3">Quiz</h4>
                      <div className="quiz-container">
                        {transcriptionResult.data.latex_quiz.map((q: any, idx: number) => (
                          <div key={idx} className="quiz-card mb-4 p-4" style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '1rem' }}>
                             <h5 className="mb-3">{idx + 1}. {q.question}</h5>
                             <div className="options-grid">
                               {q.choices.map((choice: string, cIdx: number) => (
                                 <div key={cIdx} className={`option-item p-2 mb-2 ${choice === q.answer ? 'correct-answer' : ''}`} 
                                      style={{ border: choice === q.answer ? '1px solid #10b981' : '1px solid rgba(255,255,255,0.1)', borderRadius: '0.5rem' }}>
                                   {choice}
                                 </div>
                               ))}
                             </div>
                             <div className="mt-2 small" style={{ color: 'rgba(255, 255, 255, 0.7)' }}>
                               <strong>Explanation:</strong> {q.explanation}
                             </div>
                          </div>
                        ))}
                      </div>
                   </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // --- UPLOAD / GENERATE VIEW (original, unchanged) ---
  return (
    <div className="container-fluid dashboard-container">
      <div className="upload-card">
        
        {videoId ? (
          <div className="text-center">
             <div className="mb-4">
               <div style={{ fontSize: '4rem', color: '#10b981', marginBottom: '1rem' }}>
                 <FaCloudUploadAlt />
               </div>
               <h3>Upload Successful!</h3>
               <p className="text-muted">Your media is ready for generation.</p>
             </div>
             
             <div className="action-buttons">
               <button 
                 className="btn-primary"
                 onClick={handleGenerate}
                 disabled={isGenerating}
               >
                 {isGenerating ? 'Generating...' : 'Generate'}
               </button>
               <button 
                 className="btn-secondary"
                 onClick={() => {
                   setVideoId(null);
                   setFileStatus(null);
                   setYoutubeStatus(null);
                   setGenerateStatus(null);
                 }}
                 disabled={isGenerating}
               >
                 Upload Again
               </button>
             </div>
             
             {generateStatus && (
               <div className={`upload-status ${generateStatus.type} mt-4`}>
                 {generateStatus.message}
               </div>
             )}
          </div>
        ) : (
          <>
        {userName && (
            <div className="welcome-message">
                Welcome, <span>{userName}</span>!
            </div>
        )}
        {/* File Upload Section */}
        <div className="upload-section">
          <input 
            type="file" 
            ref={fileInputRef}
            className="d-none" 
            accept="video/*,audio/*"
            onChange={handleFileChange}
            disabled={isUploading || isYoutubeLoading}
          />
          <div 
            className={`upload-btn-large ${(isUploading || isYoutubeLoading) ? 'opacity-50 cursor-not-allowed' : ''}`}
            onClick={handleUploadClick}
            role="button"
            tabIndex={0}
          >
            <FaCloudUploadAlt className="upload-icon" />
            <div>
              <div className="upload-text">{isUploading ? 'Uploading...' : 'Upload File'}</div>
              <div className="upload-subscript">
                Supported formats: <sub>video/mp4, audio/mp3, ...</sub>
              </div>
            </div>
          </div>

          {/* Progress Bar */}
          {isUploading && (
            <div className="progress-container">
              <div className="progress-info">
                <span>Uploading...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="progress-bar-bg">
                <div 
                  className="progress-bar-fill" 
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Status Message for File */}
          {fileStatus && (
            <div className={`upload-status ${fileStatus.type}`}>
              {fileStatus.message}
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="divider">OR</div>

        {/* YouTube Section */}
        <div className="youtube-section">
          <label className="youtube-label" htmlFor="youtube-url">
            <FaYoutube style={{ color: '#ff0000' }} />
            Import from YouTube
          </label>
          <div className="youtube-input-group">
            <div className="youtube-icon-wrapper">
              <FaLink />
            </div>
            <input 
              type="text" 
              id="youtube-url"
              className="youtube-input"
              placeholder="Paste YouTube video link here and press Enter..."
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
              onKeyDown={handleYoutubeSubmit}
              disabled={isYoutubeLoading || isUploading}
            />
          </div>
          
          {/* YouTube Progress / Loading */}
          {isYoutubeLoading && (
            <div className="progress-container">
               <div className="progress-info">
                 <span>Processing YouTube Video...</span>
               </div>
               <div className="progress-bar-bg" style={{ overflow: 'hidden' }}>
                 <div 
                   className="progress-bar-fill" 
                   style={{ width: '100%', animation: 'indeterminate 1.5s infinite linear', transformOrigin: '0% 50%' }}
                 />
               </div>
            </div>
          )}

          {/* Status Message for YouTube */}
          {youtubeStatus && (
            <div className={`upload-status ${youtubeStatus.type}`}>
              {youtubeStatus.message}
            </div>
          )}
        </div>
        </>
        )}

      </div>
    </div>
  );
};

export default DashboardPage;
