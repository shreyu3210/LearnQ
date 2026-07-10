import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { fileService } from '../../services/api';
import VideoPlayerPanel from '../../components/video/VideoPlayerPanel';
import '../../assets/styles/Dashboard.css'; // Reusing dashboard styles for tabs/quiz
import { FaArrowLeft } from 'react-icons/fa';

/** Parse "HH:MM:SS" to seconds */
function parseTimestamp(ts: string): number {
  const parts = ts.trim().split(':');
  if (parts.length === 3) return parseInt(parts[0]) * 3600 + parseInt(parts[1]) * 60 + parseInt(parts[2]);
  if (parts.length === 2) return parseInt(parts[0]) * 60 + parseInt(parts[1]);
  return parseFloat(ts);
}

const HistoryDetailsPage: React.FC = () => {
  const { state } = useLocation();
  const navigate = useNavigate();
  
  // If no state is passed (e.g. direct link), we would ideally fetch data by id here.
  // For now, if no item in state, we show an error or return to history.
  const item = state?.item;

  const [activeTab, setActiveTab] = useState<'transcript' | 'summary' | 'mcqs'>('transcript');
  const [seekTime, setSeekTime] = useState<number | null>(null);

  if (!item) {
    return (
        <div className="container-fluid dashboard-container text-center">
            <h3>Item not found.</h3>
            <button className="btn-secondary mt-3" onClick={() => navigate('/history')}>Back to History</button>
        </div>
    );
  }

  // Extract data from nested result object if available, otherwise flat
  const resultData = item.result || {};
  const transcript = resultData.transcription || item.transcript;
  const summary = resultData.summary || item.summary;
  const quizSource = resultData.quiz || item.quiz || item.latex_quiz;

  // Parse quiz if it's a string, or use as object
  let quizData = [];
  try {
      if (typeof quizSource === 'string') {
          quizData = JSON.parse(quizSource);
      } else if (Array.isArray(quizSource)) {
          quizData = quizSource;
      } else if (quizSource && quizSource.latex_quiz) {
           // Handle potential nesting similar to generation response
           quizData = quizSource.latex_quiz;
      }
  } catch (e) {
      console.error("Failed to parse quiz data", e);
  }

  const hasVideo = !!item.storage_path;

  /**
   * Render transcript text with clickable timestamp badges.
   */
  const renderClickableTranscript = (raw: string) => {
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

  return (
    <div className="container-fluid dashboard-container">
      <div className={`dashboard-results-layout ${!hasVideo ? 'no-video' : ''}`}>
        {/* Video Player — OUTSIDE the card */}
        {hasVideo && transcript && (
          <div className="results-video-side">
            <VideoPlayerPanel
              videoUrl={fileService.getVideoStreamUrl(item.storage_path)}
              transcriptRaw={transcript}
              seekTime={seekTime}
            />
          </div>
        )}

        {/* Card */}
        <div className="upload-card results-card-side h-100">
           <div className="d-flex align-items-center mb-4">
             <button className="btn-secondary me-3 p-2" onClick={() => navigate('/history')}>
               <FaArrowLeft />
             </button>
             <h2 className="m-0 text-truncate">{item.title || item.filename}</h2>
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
                     {hasVideo && transcript
                       ? renderClickableTranscript(transcript)
                       : (transcript || "No transcript available.")
                     }
                   </p>
                </div>
              )}

              {activeTab === 'summary' && (
                <div className="content-pane">
                   <h4 className="mb-3">Summary</h4>
                   <div className="markdown-content">
                     <ReactMarkdown>{summary || "No summary available."}</ReactMarkdown>
                   </div>
                </div>
              )}

              {activeTab === 'mcqs' && (
                 <div className="content-pane">
                    <h4 className="mb-3">Quiz</h4>
                    {quizData && quizData.length > 0 ? (
                        <div className="quiz-container">
                          {quizData.map((q: any, idx: number) => (
                            <div key={idx} className="quiz-card mb-4 p-4" style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '1rem' }}>
                               <h5 className="mb-3">{idx + 1}. {q.question}</h5>
                               <div className="options-grid">
                                 {q.choices && q.choices.map((choice: string, cIdx: number) => (
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
                    ) : (
                        <p>No quiz generated for this item.</p>
                    )}
                 </div>
              )}
           </div>
        </div>
      </div>
    </div>
  );
};

export default HistoryDetailsPage;
