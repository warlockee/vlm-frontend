import React, { useState, useEffect } from 'react';
import axios from 'axios';
import ImageUpload from '../components/ImageUpload';
import ChatInterface from '../components/ChatInterface';
import { Link } from 'react-router-dom';

// Configure Axios - uses Vite proxy to backend
const api = axios.create({
    baseURL: '/api',
    timeout: 300000, // 5 minutes for long 16k context generation
});

function HomePage() {
    const [selectedImage, setSelectedImage] = useState(null);
    const [response, setResponse] = useState(null);
    const [loading, setLoading] = useState(false);
    const [isModelLoaded, setIsModelLoaded] = useState(false);

    useEffect(() => {
        // Check backend health/status
        const checkHealth = async () => {
            try {
                const res = await api.get('/health');
                if (res.data.status === 'ok') {
                    setIsModelLoaded(res.data.model_loaded);
                }
            } catch (error) {
                console.error("Backend not reachable", error);
            }
        };

        checkHealth();
        const interval = setInterval(checkHealth, 5000);
        return () => clearInterval(interval);
    }, []);

    const handleImageSelect = (file) => {
        setSelectedImage(file);
        setResponse(null); // Clear previous response when new image selected
    };

    const handleSendPrompt = async (prompt) => {
        if (!selectedImage) {
            alert("Please upload an image first.");
            return;
        }

        setLoading(true);
        setResponse(null);

        const formData = new FormData();
        formData.append('file', selectedImage);
        formData.append('prompt', prompt);

        try {
            const res = await api.post('/inference', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                }
            });
            setResponse(res.data.response);
        } catch (error) {
            console.error("Inference Error", error);
            setResponse("Error: Failed to get response from server. " + (error.response?.data?.detail || error.message));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container">
            <header className="app-header">
                <h1 className="app-title">Visual Understanding Demo</h1>
                <p className="app-subtitle">Advanced Visual Language Model Playground</p>
                <div style={{ marginTop: '1rem' }}>
                    <Link to="/compare" className="btn-primary" style={{ textDecoration: 'none', display: 'inline-block' }}>
                        Go to Comparison Bench
                    </Link>
                </div>
            </header>

            <div className="main-grid">
                <ImageUpload
                    onImageSelect={handleImageSelect}
                    selectedImage={selectedImage}
                />
                <ChatInterface
                    onSendPrompt={handleSendPrompt}
                    response={response}
                    isLoading={loading}
                    isModelLoaded={isModelLoaded}
                />
            </div>
        </div>
    );
}

export default HomePage;
