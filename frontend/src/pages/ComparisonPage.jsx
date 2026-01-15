import { useState } from 'react'
import '../comparison.css'
import { Link } from 'react-router-dom'

function ComparisonPage() {
    const [file, setFile] = useState(null)
    const [preview, setPreview] = useState(null)
    const [prompt, setPrompt] = useState("Describe this scene in detail, focusing on road conditions and traffic.")
    const [loading, setLoading] = useState(false) // General loading state (for button)

    // Independent states
    const [studentResult, setStudentResult] = useState(null)
    const [teacherResult, setTeacherResult] = useState(null)
    const [studentLoading, setStudentLoading] = useState(false)
    const [teacherLoading, setTeacherLoading] = useState(false)

    const [error, setError] = useState(null)

    const handleFileChange = (e) => {
        const selected = e.target.files[0]
        if (selected) {
            setFile(selected)
            setPreview(URL.createObjectURL(selected))
            resetResults()
        }
    }

    const resetResults = () => {
        setStudentResult(null)
        setTeacherResult(null)
        setError(null)
    }

    const handleDragOver = (e) => {
        e.preventDefault()
        e.currentTarget.classList.add('drag-active')
    }

    const handleDragLeave = (e) => {
        e.preventDefault()
        e.currentTarget.classList.remove('drag-active')
    }

    const handleDrop = (e) => {
        e.preventDefault()
        e.currentTarget.classList.remove('drag-active')
        const selected = e.dataTransfer.files[0]
        if (selected) {
            setFile(selected)
            setPreview(URL.createObjectURL(selected))
            resetResults()
        }
    }

    const fetchModel = async (endpoint, setResult, setLoadingState) => {
        setLoadingState(true)
        const formData = new FormData()
        formData.append('file', file)
        formData.append('query', prompt)

        try {
            // Updated to point to /api/{student|teacher} which are handled by the single backend
            const response = await fetch(`/api/${endpoint}`, {
                method: 'POST',
                body: formData,
            })

            if (!response.ok) {
                throw new Error(`${endpoint} error: ${response.statusText}`)
            }

            const data = await response.json()
            setResult(data)
        } catch (err) {
            console.error(err)
            setError(prev => prev ? `${prev} | ${err.message}` : err.message)
        } finally {
            setLoadingState(false)
        }
    }

    const handleCompare = async () => {
        if (!file || !prompt) return

        setLoading(true)
        resetResults()

        // Trigger both independent requests
        Promise.all([
            fetchModel('student', setStudentResult, setStudentLoading),
            fetchModel('teacher', setTeacherResult, setTeacherLoading)
        ]).finally(() => {
            setLoading(false)
        })
    }

    return (
        <div className="comparison-page">
            <header>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <div className="logo-icon" style={{ fontSize: '1.5rem' }}>🧪</div>
                    <h1>VLM Distillation Workbench</h1>
                    <Link to="/" style={{ color: 'var(--accent-color)', marginLeft: '1rem', textDecoration: 'none' }}>
                        🏠 Home
                    </Link>
                </div>
                <div style={{ display: 'flex', gap: '1rem' }}>
                    <span className="badge">Direct Comparison</span>
                </div>
            </header>
            <main>
                <div className="controls">
                    <div
                        className="dropzone"
                        onDragOver={handleDragOver}
                        onDragLeave={handleDragLeave}
                        onDrop={handleDrop}
                        onClick={() => document.getElementById('file-input').click()}
                    >
                        {preview ? (
                            <img src={preview} alt="Upload" className="preview-image" />
                        ) : (
                            <div style={{ color: 'var(--text-secondary)' }}>
                                <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>📷</div>
                                <div>Drag & Drop Image</div>
                            </div>
                        )}
                        <input
                            type="file"
                            id="file-input"
                            onChange={handleFileChange}
                            accept="image/*"
                            style={{ display: 'none' }}
                        />
                    </div>

                    <div className="input-group">
                        <label className="input-label">Analysis Prompt</label>
                        <textarea
                            className="modern-textarea"
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            placeholder="Enter your query here..."
                        />
                    </div>

                    <button className="primary-btn" onClick={handleCompare} disabled={!file || loading}>
                        {loading ? 'Processing...' : 'Run Comparison'}
                    </button>

                    {error && <div className="error-box">{error}</div>}
                </div>

                <div className="comparison-view">
                    {/* Teacher Panel */}
                    <div className="model-panel">
                        <div className="panel-header">
                            <div className="model-name">
                                <span>🎓 Teacher Model</span>
                                <span className="badge teacher-badge">32B</span>
                            </div>
                            <div className="model-meta">
                                <span className="meta-info">Remote</span>
                                {teacherResult?.latency && (
                                    <div className="metric">
                                        ⚡ <span className="metric-value">{teacherResult.latency}s</span>
                                    </div>
                                )}
                            </div>
                        </div>
                        <div className="response-container">
                            {teacherResult?.response ? (
                                <div className="response-content">{teacherResult.response}</div>
                            ) : teacherLoading ? (
                                <div className="loading-state">Thinking...</div>
                            ) : (
                                <div className="empty-state">Ready</div>
                            )}
                        </div>
                    </div>

                    {/* Student Panel */}
                    <div className="model-panel student-panel">
                        <div className="panel-header">
                            <div className="model-name">
                                <span>🚀 Student Model</span>
                                <span className="badge student-badge">1B</span>
                            </div>
                            <div className="model-meta">
                                <span className="meta-info">Local</span>
                                {studentResult?.latency && (
                                    <div className="metric">
                                        ⚡ <span className="metric-value">{studentResult.latency}s</span>
                                    </div>
                                )}
                            </div>
                        </div>
                        <div className="response-container">
                            {studentResult?.response ? (
                                <div className="response-content">{studentResult.response}</div>
                            ) : studentLoading ? (
                                <div className="loading-state">Thinking...</div>
                            ) : (
                                <div className="empty-state">Ready</div>
                            )}
                        </div>
                    </div>
                </div>
            </main>
        </div>
    )
}

export default ComparisonPage
