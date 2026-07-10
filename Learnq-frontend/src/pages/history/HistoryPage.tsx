import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fileService } from '../../services/api';
import '../../assets/styles/History.css';

interface HistoryItem {
    id: number;
    title: string;
    filename?: string;
    storage_path?: string;
    upload_time?: string;
    // Nested result object based on user JSON
    result?: {
        transcription?: string;
        summary?: string;
        quiz?: any;
    };
    // Keep flat properties for potential backward compatibility
    summary?: string | null;
    transcript?: string | null;
    quiz?: any | null; 
}

const HistoryPage: React.FC = () => {
    // 1. Initialize state from session storage if available (Stale-While-Revalidate)
    const [history, setHistory] = useState<HistoryItem[]>(() => {
        const cached = sessionStorage.getItem('historyCache');
        return cached ? JSON.parse(cached) : [];
    });
    
    // 2. Only show loading details if we have no data
    const [loading, setLoading] = useState(history.length === 0);
    const [error, setError] = useState<string | null>(null);
    const navigate = useNavigate();

    useEffect(() => {
        const fetchHistory = async () => {
            try {
                // If we have data, we are "revalidating" in the background
                // If we don't, we are "loading"
                
                const data = await fileService.getHistory();
                const historyData = data.data || data.history || data;
                
                if (Array.isArray(historyData)) {
                    setHistory(historyData);
                    // Update cache
                    sessionStorage.setItem('historyCache', JSON.stringify(historyData));
                } else {
                    console.error("Unexpected history data format:", data);
                    if (history.length === 0) setError("Received invalid data from server");
                }
            } catch (err: any) {
                console.error("Failed to fetch history:", err);
                if (history.length === 0) setError("Failed to load history.");
            } finally {
                setLoading(false);
            }
        };

        fetchHistory();
    }, []);

    if (loading) return <div className="history-container loading">Loading history...</div>;
    if (error && history.length === 0) return <div className="history-container error">{error}</div>;

    return (
        <div className="container-fluid history-container">
            <h2 className="page-title">Your History</h2>
            {history.length === 0 ? (
                 <div className="empty-state">No history found. Upload some media to get started!</div>
            ) : (
                <div className="history-grid">
                    {history.map((item) => (
                        <div key={item.id} className="history-card">
                            <div className="card-header">
                                <h3 className="card-title" title={item.title || item.filename}>
                                    {item.title || item.filename || 'Untitled Media'}
                                </h3>
                                {/* Assuming upload_time exists, or handle missing date */}
                                <span className="card-date">{item.upload_time ? new Date(item.upload_time).toLocaleDateString() : ''}</span>
                            </div>
                            {/* Summary preview removed as per request */}
                            <div className="card-footer">
                                <button 
                                    className="btn-view"
                                    onClick={() => navigate(`/history/${item.id}`, { state: { item } })}
                                >
                                    View Details
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default HistoryPage;
