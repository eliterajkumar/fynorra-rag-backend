import React, { useState } from 'react'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  'https://qqkmdkcynfaydivvpfer.supabase.co',
  'sb_publishable_MOyFL1lECnmmGXcOuQPhMw_tfGSQVGe'
)

const API_BASE = 'http://localhost:5000'

export default function RAGInterface() {
  const [file, setFile] = useState(null)
  const [query, setQuery] = useState('')
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(false)

  const uploadFile = async () => {
    if (!file) return
    
    setLoading(true)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const token = session?.access_token
      
      const formData = new FormData()
      formData.append('file', file)
      
      const response = await fetch(`${API_BASE}/api/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      })
      
      const result = await response.json()
      alert(`Upload successful! Job ID: ${result.jobId}`)
    } catch (error) {
      alert(`Upload failed: ${error.message}`)
    }
    setLoading(false)
  }

  const askQuestion = async () => {
    if (!query) return
    
    setLoading(true)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const token = session?.access_token
      
      const response = await fetch(`${API_BASE}/api/query`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query })
      })
      
      const result = await response.json()
      setAnswer(result.answer)
    } catch (error) {
      alert(`Query failed: ${error.message}`)
    }
    setLoading(false)
  }

  return (
    <div style={{ padding: '20px', maxWidth: '600px' }}>
      <h2>RAG Document Chat</h2>
      
      {/* File Upload */}
      <div style={{ marginBottom: '20px' }}>
        <input 
          type="file" 
          accept=".pdf,.txt,.html"
          onChange={(e) => setFile(e.target.files[0])}
        />
        <button onClick={uploadFile} disabled={!file || loading}>
          Upload Document
        </button>
      </div>
      
      {/* Query Interface */}
      <div style={{ marginBottom: '20px' }}>
        <input 
          type="text"
          placeholder="Ask a question about your documents..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ width: '400px', padding: '8px' }}
        />
        <button onClick={askQuestion} disabled={!query || loading}>
          Ask
        </button>
      </div>
      
      {/* Answer Display */}
      {answer && (
        <div style={{ 
          padding: '15px', 
          backgroundColor: '#f5f5f5', 
          borderRadius: '5px' 
        }}>
          <strong>Answer:</strong>
          <p>{answer}</p>
        </div>
      )}
      
      {loading && <p>Loading...</p>}
    </div>
  )
}