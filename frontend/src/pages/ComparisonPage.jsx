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
    const [feedbackStatus, setFeedbackStatus] = useState({}) // { key: 'success' | 'error' | 'loading' }
    const [dpoComment, setDpoComment] = useState("")
    const [selectedWinner, setSelectedWinner] = useState(null)

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
        setDpoComment("")
        setSelectedWinner(null)
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

    const updateFeedbackStatus = (key, status) => {
        setFeedbackStatus(prev => ({ ...prev, [key]: status }))
        setTimeout(() => {
            setFeedbackStatus(prev => {
                const next = { ...prev }
                delete next[key]
                return next
            })
        }, 3000)
    }

    const handleSFTFeedback = async (modelType, isPass) => {
        const result = modelType === 'teacher' ? teacherResult : studentResult
        if (!file || !result) return

        const key = `${modelType}_${isPass ? 'pass' : 'fail'}`
        updateFeedbackStatus(key, 'loading')

        const formData = new FormData()
        formData.append('file', file)
        formData.append('query', prompt)
        formData.append('response', result.response)
        formData.append('model_name', modelType === 'teacher' ? 'Teacher-32B' : 'Student-1B')
        formData.append('is_pass', isPass)

        try {
            const res = await fetch('/api/feedback/sft', {
                method: 'POST',
                body: formData
            })
            if (!res.ok) throw new Error('Failed to save feedback')
            updateFeedbackStatus(key, 'success')
        } catch (err) {
            console.error(err)
            updateFeedbackStatus(key, 'error')
        }
    }

    const handleDPOFeedback = async (winner) => {
        if (!file || !teacherResult || !studentResult) return

        updateFeedbackStatus('dpo', 'loading')

        const formData = new FormData()
        formData.append('file', file)
        formData.append('query', prompt)
        formData.append('model_winner', winner === 'teacher' ? 'Teacher-32B' : 'Student-1B')
        formData.append('model_loser', winner === 'teacher' ? 'Student-1B' : 'Teacher-32B')
        formData.append('response_winner', winner === 'teacher' ? teacherResult.response : studentResult.response)
        formData.append('response_loser', winner === 'teacher' ? studentResult.response : teacherResult.response)
        if (dpoComment) formData.append('comment', dpoComment)

        try {
            const res = await fetch('/api/feedback/dpo', {
                method: 'POST',
                body: formData
            })
            if (!res.ok) throw new Error('Failed to save feedback')
            updateFeedbackStatus('dpo', 'success')
        } catch (err) {
            console.error(err)
            updateFeedbackStatus('dpo', 'error')
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
                        {teacherResult && (
                            <div className="feedback-actions" style={{ padding: '1rem', borderTop: '1px solid var(--border-color)', display: 'flex', gap: '1rem' }}>
                                <button
                                    className={`feedback-btn pass ${feedbackStatus['teacher_pass']}`}
                                    onClick={() => handleSFTFeedback('teacher', true)}
                                >
                                    {feedbackStatus['teacher_pass'] === 'success' ? 'Saved ✓' : 'PASS'}
                                </button>
                                <button
                                    className={`feedback-btn fail ${feedbackStatus['teacher_fail']}`}
                                    onClick={() => handleSFTFeedback('teacher', false)}
                                >
                                    {feedbackStatus['teacher_fail'] === 'success' ? 'Saved ✓' : 'FAIL'}
                                </button>
                            </div>
                        )}
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
                        {studentResult && (
                            <div className="feedback-actions" style={{ padding: '1rem', borderTop: '1px solid var(--border-color)', display: 'flex', gap: '1rem' }}>
                                <button
                                    className={`feedback-btn pass ${feedbackStatus['student_pass']}`}
                                    onClick={() => handleSFTFeedback('student', true)}
                                >
                                    {feedbackStatus['student_pass'] === 'success' ? 'Saved ✓' : 'PASS'}
                                </button>
                                <button
                                    className={`feedback-btn fail ${feedbackStatus['student_fail']}`}
                                    onClick={() => handleSFTFeedback('student', false)}
                                >
                                    {feedbackStatus['student_fail'] === 'success' ? 'Saved ✓' : 'FAIL'}
                                </button>
                            </div>
                        )}
                    </div>
                </div>

                {teacherResult && studentResult && (
                    <div className="dpo-panel" style={{
                        marginTop: '1rem',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.75rem',
                        padding: '1rem',
                        background: 'var(--panel-bg)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '12px'
                    }}>
                        <div style={{
                            fontSize: '0.9rem',
                            color: 'var(--text-secondary)',
                            fontWeight: '700',
                            textTransform: 'uppercase',
                            letterSpacing: '0.05em',
                            borderBottom: '1px solid var(--border-color)',
                            paddingBottom: '0.5rem'
                        }}>
                            Preference
                        </div>

                        <div style={{ display: 'flex', gap: '1rem' }}>
                            <button
                                className="primary-btn"
                                style={{
                                    background: selectedWinner === 'teacher' ? '#eab308' : 'rgba(234, 179, 8, 0.2)',
                                    color: selectedWinner === 'teacher' ? '#000' : '#eab308',
                                    border: selectedWinner === 'teacher' ? '2px solid #fff' : '1px solid transparent',
                                    padding: '0.5rem 1rem', fontSize: '0.9rem', flex: 1
                                }}
                                onClick={() => setSelectedWinner('teacher')}
                                disabled={feedbackStatus['dpo'] === 'success'}
                            >
                                🎓 Teacher Wins
                            </button>
                            <button
                                className="primary-btn"
                                style={{
                                    background: selectedWinner === 'student' ? '#3b82f6' : 'rgba(59, 130, 246, 0.2)',
                                    color: selectedWinner === 'student' ? '#fff' : '#3b82f6',
                                    border: selectedWinner === 'student' ? '2px solid #fff' : '1px solid transparent',
                                    padding: '0.5rem 1rem', fontSize: '0.9rem', flex: 1
                                }}
                                onClick={() => setSelectedWinner('student')}
                                disabled={feedbackStatus['dpo'] === 'success'}
                            >
                                🚀 Student Wins
                            </button>
                        </div>

                        <textarea
                            placeholder="Rationale (optional)..."
                            value={dpoComment}
                            onChange={(e) => setDpoComment(e.target.value)}
                            style={{
                                background: 'rgba(0,0,0,0.3)',
                                border: '1px solid var(--border-color)',
                                borderRadius: '6px',
                                padding: '0.5rem',
                                color: '#fff',
                                fontSize: '0.85rem',
                                minHeight: '40px',
                                resize: 'vertical'
                            }}
                        />

                        <button
                            className="primary-btn"
                            style={{ width: '100%', padding: '0.6rem' }}
                            onClick={() => handleDPOFeedback(selectedWinner)}
                            disabled={!selectedWinner || feedbackStatus['dpo'] === 'success'}
                        >
                            Submit Preference
                        </button>

                        {feedbackStatus['dpo'] === 'success' && (
                            <div style={{ color: 'var(--success)', fontWeight: 'bold', fontSize: '0.9rem', textAlign: 'center' }}>
                                ✓ Preference Saved
                            </div>
                        )}
                    </div>
                )}
            </main>
        </div>
    )
}

export default ComparisonPage
