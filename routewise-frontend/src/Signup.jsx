
import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000'

const footerTextStyle = { marginTop: '14px', fontSize: '14px', color: '#5b6673' }
const footerLinkStyle = { color: '#C98F3F', fontWeight: 600, textDecoration: 'none' }

function Signup() {
  const navigate = useNavigate()

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('vendor')
  const [otp, setOtp] = useState('')
  const [otpSent, setOtpSent] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)

  if (sessionStorage.getItem('token')) {
    return <Navigate to="/dashboard" replace />
  }

  const handleSendOtp = async () => {
    setError('')
    setSuccess('')

    if (!name.trim() || !email.trim() || !password) {
      setError('Please fill in your name, email and password.')
      return
    }

    if (!email.includes('@')) {
      setError('Please enter a valid email address.')
      return
    }

    setLoading(true)

    try {
      const response = await fetch(`${API}/send-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim().toLowerCase() })
      })

      const data = await response.json()

      if (response.ok) {
        setOtpSent(true)
        setSuccess('OTP sent successfully! Please check your email.')
      } else {
        setError(data.message || 'Unable to send OTP.')
      }
    } catch (err) {
      setError('Unable to connect to the server. Please try again later.')
    } finally {
      setLoading(false)
    }
  }

  const handleSignup = async () => {
    setError('')
    setSuccess('')

    if (!otp.trim()) {
      setError('Please enter the OTP sent to your email.')
      return
    }

    setLoading(true)

    try {
      const response = await fetch(`${API}/add-user`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim().toLowerCase(),
          password,
          role,
          otp: otp.trim()
        })
      })

      const data = await response.json()

      if (response.ok) {
        setSuccess('Account created successfully! Redirecting to login...')
        setTimeout(() => navigate('/login', { replace: true }), 1500)
      } else {
        setError(data.message || 'Sign up failed. Please try again.')
      }
    } catch (err) {
      setError('Unable to connect to the server. Please try again later.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="header">
        <div>
          <h1>ROUTEWISE</h1>
          <div className="tagline">Smart delivery route optimizer</div>
        </div>
      </div>

      <div className="auth-container">
        <h1>Create Account</h1>

        <input
          className="input-field"
          type="text"
          placeholder="Full name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />

        <input
          className="input-field"
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value)
            setOtpSent(false)
            setOtp('')
            setError('')
            setSuccess('')
          }}
        />

        <input
          className="input-field"
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <select
          className="input-field"
          value={role}
          onChange={(e) => setRole(e.target.value)}
          style={{ cursor: 'pointer' }}
        >
          <option value="vendor">I am a Vendor</option>
          <option value="delivery_boy">I am a Delivery Boy</option>
        </select>

        {otpSent && (
          <input
            className="input-field"
            type="text"
            placeholder="Enter 6-digit OTP"
            value={otp}
            maxLength={6}
            onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
            onKeyDown={(e) => e.key === 'Enter' && handleSignup()}
          />
        )}

        {error && (
          <p style={{ color: '#c0392b', marginTop: '8px', fontSize: '14px' }}>
            {error}
          </p>
        )}

        {success && (
          <p style={{ color: '#2e7d32', marginTop: '8px', fontSize: '14px' }}>
            {success}
          </p>
        )}

        {!otpSent ? (
          <button
            className="btn-primary"
            onClick={handleSendOtp}
            disabled={loading}
            style={{ opacity: loading ? 0.7 : 1, cursor: loading ? 'not-allowed' : 'pointer' }}
          >
            {loading ? 'Sending OTP...' : 'Send OTP'}
          </button>
        ) : (
          <>
            <button
              className="btn-primary"
              onClick={handleSignup}
              disabled={loading}
              style={{ opacity: loading ? 0.7 : 1, cursor: loading ? 'not-allowed' : 'pointer' }}
            >
              {loading ? 'Creating...' : 'Create Account'}
            </button>

            <button
              className="btn-primary"
              onClick={handleSendOtp}
              disabled={loading}
              style={{ marginTop: '10px', opacity: loading ? 0.7 : 1, cursor: loading ? 'not-allowed' : 'pointer' }}
            >
              Resend OTP
            </button>
          </>
        )}

        <p style={footerTextStyle}>
          Already have an account? <Link to="/login" style={footerLinkStyle}>Login here</Link>
        </p>
      </div>
    </div>
  )
}

export default Signup
