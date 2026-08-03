import React, { useState, useEffect } from 'react';
import axios from 'axios';

const ChatSummary = ({ conversationId }) => {
    const [summary, setSummary] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!conversationId) return;

        const fetchSummary = async () => {
            try {
                setLoading(true);
                // FIXED: Use import.meta.env for Vite, with fallback to localhost
                const baseUrl = import.meta.env.VITE_API_URL || '';
                const response = await axios.get(
                    `${baseUrl}/api/chat-public/${conversationId}/summary`
                );
                setSummary(response.data);
                setError(null);
            } catch (err) {
                setError('Failed to load summary');
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        fetchSummary();
    }, [conversationId]);

    const downloadPDF = async () => {
        try {
            const baseUrl = import.meta.env.VITE_API_URL || '';
            const response = await axios.post(
                `${baseUrl}/api/chat-public/${conversationId}/end`,
                {},
                { responseType: 'blob' }
            );
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `chat_${conversationId}.pdf`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) {
            console.error('PDF download failed:', err);
        }
    };

    if (loading) return <div className="loading-summary">Loading summary...</div>;
    if (error) return <div className="error-summary">{error}</div>;
    if (!summary) return <div>No summary available</div>;

    return (
        <div className="chat-summary-card">
            <div className="summary-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                <h3 style={{ margin: 0 }}>📊 Chat Summary</h3>
                <button 
                    className="btn btn-primary" 
                    onClick={downloadPDF}
                    style={{
                        background: '#D61903',
                        color: '#fff',
                        border: 'none',
                        padding: '8px 16px',
                        borderRadius: '6px',
                        cursor: 'pointer'
                    }}
                >
                    📄 Download PDF
                </button>
            </div>
            
            <div className="summary-content">
                <div className="summary-stats" style={{ display: 'flex', gap: '20px', marginBottom: '10px' }}>
                    <span>📊 Messages: {summary.message_count}</span>
                    <span>👤 User: {summary.user_message_count}</span>
                    <span>🤖 Bot: {summary.bot_message_count}</span>
                </div>
                
                <div className="summary-sentiment" style={{ marginBottom: '10px' }}>
                    <strong>Sentiment:</strong> 
                    <span className={`sentiment-${summary.sentiment}`} style={{
                        marginLeft: '8px',
                        padding: '2px 10px',
                        borderRadius: '12px',
                        background: summary.sentiment === 'positive' ? '#d4edda' : 
                                   summary.sentiment === 'negative' ? '#f8d7da' : '#e2e3e5',
                        color: summary.sentiment === 'positive' ? '#155724' : 
                               summary.sentiment === 'negative' ? '#721c24' : '#383d41'
                    }}>
                        {summary.sentiment}
                    </span>
                </div>
                
                <div className="summary-key-points" style={{ marginBottom: '10px' }}>
                    <strong>Key Points:</strong>
                    <ul style={{ margin: '5px 0', paddingLeft: '20px' }}>
                        {summary.key_points && summary.key_points.map((point, index) => (
                            <li key={index}>{point}</li>
                        ))}
                    </ul>
                </div>
                
                <div className="summary-text" style={{
                    background: '#f8f9fa',
                    padding: '10px',
                    borderRadius: '6px',
                    maxHeight: '200px',
                    overflowY: 'auto'
                }}>
                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>{summary.summary}</pre>
                </div>
            </div>
        </div>
    );
};

export default ChatSummary;