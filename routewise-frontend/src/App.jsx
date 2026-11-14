import { useState, useEffect } from 'react'
import { Routes, Route, Link, Navigate, useNavigate } from 'react-router-dom'
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet'
import L from 'leaflet'
import Signup from './Signup.jsx'
import './App.css'

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000'
const EMPTY_ROUTE = { optimized_route: [], total_distance_km: 0, total_eta_minutes: 0 }
const DEFAULT_CENTER = [28.6139, 77.2090] // Delhi

const footerTextStyle = { marginTop: '14px', fontSize: '14px', color: '#5b6673' }
const footerLinkStyle = { color: '#C98F3F', fontWeight: 600, textDecoration: 'none' }

const storeIcon = L.divIcon({
  html: `<div style="background:#2c3e50;color:#fff;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;box-shadow:0 0 0 2px #fff;">🏠</div>`,
  className: '',
  iconSize: [28, 28],
  iconAnchor: [14, 14]
})

const boyIcon = L.divIcon({
  html: `<div style="background:#27ae60;color:#fff;width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;box-shadow:0 0 0 2px #fff;">🛵</div>`,
  className: '',
  iconSize: [26, 26],
  iconAnchor: [13, 13]
})

function StatusBadge({ status }) {
  const isDelivered = status === 'delivered'
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 10px',
        borderRadius: '999px',
        fontSize: '11px',
        fontWeight: 600,
        textTransform: 'capitalize',
        color: isDelivered ? '#1e7e34' : '#a15c00',
        background: isDelivered ? '#e3f6e8' : '#fdf0dd'
      }}
    >
      {status}
    </span>
  )
}

function LogoutButton({ onClick }) {
  const [hover, setHover] = useState(false)
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        padding: '7px 14px',
        borderRadius: '8px',
        border: '1px solid #C98F3F',
        background: hover ? '#C98F3F' : 'transparent',
        color: hover ? '#fff' : '#F0D9B0',
        fontSize: '13px',
        fontWeight: 500,
        cursor: 'pointer',
        transition: 'all 0.2s ease'
      }}
    >
      <svg
        width="15"
        height="15"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
        <polyline points="16 17 21 12 16 7" />
        <line x1="21" y1="12" x2="9" y2="12" />
      </svg>
      Logout
    </button>
  )
}

function Header({ children }) {
  return (
    <div className="header" style={{ position: 'relative' }}>
      <div>
        <h1>ROUTEWISE</h1>
        <div className="tagline">Smart delivery route optimizer</div>
      </div>
      {children}
    </div>
  )
}

function Login() {
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [otp, setOtp] = useState('')
  const [otpSent, setOtpSent] = useState(false)
  const [loginError, setLoginError] = useState('')
  const [loading, setLoading] = useState(false)

  const cleanEmail = email.trim().toLowerCase()

  const handleLogin = async () => {
    setLoginError('')

    if (!cleanEmail || !password) {
      setLoginError('Please enter email and password.')
      return
    }

    setLoading(true)

    try {
      const response = await fetch(`${API}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: cleanEmail,
          password
        })
      })

      const data = await response.json()

      if (response.ok) {
        setOtpSent(true)
        setLoginError(data.message)
      } else {
        setLoginError(data.message || 'Login failed')
      }
    } catch (err) {
      setLoginError('Unable to connect to the server.')
    } finally {
      setLoading(false)
    }
  }

  const handleVerifyOTP = async () => {
    setLoginError('')

    if (!otp.trim()) {
      setLoginError('Please enter OTP.')
      return
    }

    setLoading(true)

    try {
      const response = await fetch(`${API}/login-verify-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: cleanEmail,
          otp: otp.trim()
        })
      })

      const data = await response.json()

      if (response.ok && data.token) {
        sessionStorage.setItem('token', data.token)
        sessionStorage.setItem('role', data.role)
        sessionStorage.setItem('email', cleanEmail)

        navigate('/dashboard', { replace: true })
      } else {
        setLoginError(data.message || 'OTP verification failed')
      }
    } catch (err) {
      setLoginError('Unable to connect to the server.')
    } finally {
      setLoading(false)
    }
  }

  if (sessionStorage.getItem('token')) {
    return <Navigate to="/dashboard" replace />
  }

  return (
    <div>
      <Header />

      <div className="auth-container">
        <h1>RouteWise Login</h1>

        <input
          className="input-field"
          type="email"
          placeholder="Enter email"
          value={email}
          disabled={otpSent}
          onChange={(e) => setEmail(e.target.value)}
        />

        <input
          className="input-field"
          type="password"
          placeholder="Enter password"
          value={password}
          disabled={otpSent}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !otpSent && handleLogin()}
        />

        {otpSent && (
          <>
            <p>OTP sent to your email. Please check your inbox.</p>

            <input
              className="input-field"
              type="text"
              placeholder="Enter 6-digit OTP"
              maxLength={6}
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
              onKeyDown={(e) => e.key === 'Enter' && handleVerifyOTP()}
            />

            <button
  className="btn-primary"
  onClick={handleVerifyOTP}
  disabled={loading}
  style={{ marginBottom: '15px' }}
>
  {loading ? 'Verifying...' : 'Verify OTP & Login'}
</button>

            <button
  className="btn-primary"
  onClick={handleLogin}
  disabled={loading}
  style={{ marginTop: '5px' }}
>
  Resend OTP
</button>
          </>
        )}

        {!otpSent && (
          <button
            className="btn-primary"
            onClick={handleLogin}
            disabled={loading}
          >
            {loading ? 'Sending OTP...' : 'Login'}
          </button>
        )}

        {loginError && (
          <p style={{
            color: '#c0392b',
            marginTop: '8px',
            fontSize: '14px'
          }}>
            {loginError}
          </p>
        )}

        <p style={footerTextStyle}>
          Don't have an account?{' '}
          <Link to="/signup" style={footerLinkStyle}>
            Sign up here
          </Link>
        </p>
      </div>
    </div>
  )
}




function Dashboard() {
  const token = sessionStorage.getItem('token')
  if (!token) {
    return <Navigate to="/login" replace />
  }
  return <DashboardContent token={token} />
}

function DashboardContent({ token }) {
  const navigate = useNavigate()
  const role = sessionStorage.getItem('role') || ''
  const userEmail = sessionStorage.getItem('email') || ''

  const [routeData, setRouteData] = useState(EMPTY_ROUTE)
  const [myOrders, setMyOrders] = useState([])
  const [deliveredOrders, setDeliveredOrders] = useState([])
  const [deliveryBoys, setDeliveryBoys] = useState([])
  const [selectedBoy, setSelectedBoy] = useState({})
  const [deliveryLocations, setDeliveryLocations] = useState([])

  const [customerName, setCustomerName] = useState('')
  const [address, setAddress] = useState('')
  const [message, setMessage] = useState('')

  const [storeLocation, setStoreLocation] = useState(null)
  const [locationStatus, setLocationStatus] = useState('')
  const [locationLoading, setLocationLoading] = useState(false)

  const handleLogout = () => {
    sessionStorage.removeItem('token')
    sessionStorage.removeItem('role')
    sessionStorage.removeItem('email')
    navigate('/login', { replace: true })
  }

  useEffect(() => {
    window.history.pushState(null, '', window.location.href)
    const onPopState = () => handleLogout()
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  const authFetch = async (path, options = {}) => {
    const res = await fetch(`${API}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
        ...(options.headers || {})
      }
    })
    if (res.status === 401 || res.status === 422) {
      handleLogout()
      throw new Error('Session expired')
    }
    return res
  }

  const loadData = async () => {
    try {
      if (role === 'vendor') {
        const locRes = await authFetch('/vendor/get-location')
        const locJson = await locRes.json()
        if (locJson.store_lat != null && locJson.store_lng != null) {
          setStoreLocation({ lat: locJson.store_lat, lng: locJson.store_lng })
        }
      }

      const routeRes = await authFetch('/optimize-route')
      const routeJson = await routeRes.json()
      setRouteData(
        routeRes.ok && Array.isArray(routeJson.optimized_route) ? routeJson : EMPTY_ROUTE
      )

      const deliveredRes = await authFetch('/my-deliveries')
      const deliveredJson = await deliveredRes.json()
      setDeliveredOrders(Array.isArray(deliveredJson) ? deliveredJson : [])

      if (role === 'vendor') {
        const ordersRes = await authFetch('/my-orders')
        const ordersJson = await ordersRes.json()
        setMyOrders(Array.isArray(ordersJson) ? ordersJson : [])

        const boysRes = await authFetch('/delivery-boys')
        const boysJson = await boysRes.json()
        setDeliveryBoys(Array.isArray(boysJson) ? boysJson : [])
      }
    } catch (err) {
      console.error('loadData failed:', err)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  useEffect(() => {
    if (role !== 'delivery_boy') return
    if (!navigator.geolocation) return

    const sendLocation = () => {
      navigator.geolocation.getCurrentPosition(
        async (pos) => {
          try {
            await authFetch('/delivery/update-location', {
              method: 'POST',
              body: JSON.stringify({
                lat: pos.coords.latitude,
                lng: pos.coords.longitude
              })
            })
          } catch (err) {
            console.error('Failed to update location:', err)
          }
        },
        (err) => console.error('Location error:', err)
      )
    }

    sendLocation()
    const interval = setInterval(sendLocation, 15000)
    return () => clearInterval(interval)
  }, [role])

  useEffect(() => {
    if (role !== 'vendor') return

    const fetchLocations = async () => {
      try {
        const res = await authFetch('/delivery-boys/locations')
        const data = await res.json()
        setDeliveryLocations(Array.isArray(data) ? data : [])
      } catch (err) {
        console.error('Failed to fetch delivery locations:', err)
      }
    }

    fetchLocations()
    const interval = setInterval(fetchLocations, 10000)
    return () => clearInterval(interval)
  }, [role])

  const handleSetStoreLocation = () => {
    if (!navigator.geolocation) {
      setLocationStatus('Geolocation is not supported by your browser.')
      return
    }
    setLocationLoading(true)
    setLocationStatus('Fetching your location...')
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords
        try {
          const res = await authFetch('/vendor/set-location', {
            method: 'POST',
            body: JSON.stringify({ lat: latitude, lng: longitude })
          })
          const data = await res.json()
          if (res.ok) {
            setStoreLocation({ lat: latitude, lng: longitude })
            setLocationStatus(`Store location set! (${latitude.toFixed(4)}, ${longitude.toFixed(4)})`)
            loadData()
          } else {
            setLocationStatus(data.message || 'Failed to update location.')
          }
                } catch (err) {
          console.error('Store location update failed:', err)
          setLocationStatus('Failed to update location. Check browser console.')
        } finally {
          setLocationLoading(false)
        }
      },
      () => {
        setLocationStatus('Location access denied. Please allow location access and try again.')
        setLocationLoading(false)
      }
    )
  }

  const handleAddOrder = async () => {
    if (!customerName.trim() || !address.trim()) {
      setMessage('Please enter both the customer name and address.')
      return
    }
    try {
      const res = await authFetch('/add-order', {
        method: 'POST',
        body: JSON.stringify({ customer_name: customerName, address: address })
      })
      const data = await res.json()
      setMessage(data.message || '')
      if (res.ok) {
        setCustomerName('')
        setAddress('')
        loadData()
      }
    } catch (err) {
      console.error(err)
    }
  }

  const handleAssign = async (orderId) => {
    const boyId = selectedBoy[orderId]
    if (!boyId) {
      setMessage('Please select a delivery boy first.')
      return
    }
    try {
      const res = await authFetch('/assign-order', {
        method: 'POST',
        body: JSON.stringify({ order_id: orderId, delivery_boy_id: Number(boyId) })
      })
      const data = await res.json()
      setMessage(data.message || '')
      if (res.ok) loadData()
    } catch (err) {
      console.error(err)
    }
  }

  const handleDelivered = async (orderId) => {
    const confirmed = window.confirm(
      'Mark this order as delivered? You can undo this from the Completed Deliveries list if it was a mistake.'
    )
    if (!confirmed) return

    try {
      const res = await authFetch(`/mark-delivered/${orderId}`, { method: 'POST' })
      const data = await res.json()
      setMessage(data.message || '')
      if (res.ok) loadData()
    } catch (err) {
      console.error(err)
    }
  }

  const handleUndoDelivered = async (orderId) => {
    const confirmed = window.confirm('Move this order back to pending?')
    if (!confirmed) return

    try {
      const res = await authFetch(`/undo-delivered/${orderId}`, { method: 'POST' })
      const data = await res.json()
      setMessage(data.message || '')
      if (res.ok) loadData()
    } catch (err) {
      console.error(err)
    }
  }

  const numberedIcon = (number) =>
    L.divIcon({
      html: `<div class="custom-marker">${number}</div>`,
      className: '',
      iconSize: [26, 26],
      iconAnchor: [13, 13]
    })

  const route = routeData.optimized_route || []
  const hasRoute = route.length > 0
  const boyName = (id) => {
    const boy = deliveryBoys.find((b) => b.id === id)
    return boy ? boy.name : `#${id}`
  }

  const mapCenter = hasRoute
    ? [route[0].latitude, route[0].longitude]
    : storeLocation
      ? [storeLocation.lat, storeLocation.lng]
      : DEFAULT_CENTER

  return (
    <div>
      <Header>
        <div
          style={{
            position: 'absolute',
            top: '50%',
            right: '24px',
            transform: 'translateY(-50%)',
            display: 'flex',
            alignItems: 'center',
            gap: '14px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '34px',
                height: '34px',
                borderRadius: '50%',
                background: '#C98F3F',
                color: '#fff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 600,
                fontSize: '15px',
                textTransform: 'uppercase'
              }}
            >
              {(userEmail || role || '?').charAt(0)}
            </div>
            <div style={{ textAlign: 'left', lineHeight: 1.25 }}>
              <div style={{ fontSize: '13px', color: '#fff', fontWeight: 500 }}>{userEmail}</div>
              <div style={{ fontSize: '11px', color: '#B8C4D4', textTransform: 'capitalize' }}>
                {role.replace('_', ' ')}
              </div>
            </div>
          </div>
          <LogoutButton onClick={handleLogout} />
        </div>
      </Header>

      <div className="dashboard">
        <div className="stats-row">
          <div className="stat-card">
            <div className="stat-label">Total Orders</div>
            <div className="stat-value">{route.length}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Total Distance</div>
            <div className="stat-value">{routeData.total_distance_km} km</div>
            {hasRoute && routeData.total_eta_minutes != null && (
              <div style={{ fontSize: '12px', color: '#5b6673', marginTop: '2px' }}>
                Est. time: ~{routeData.total_eta_minutes} min
              </div>
            )}
          </div>
          <div className="stat-card">
            <div className="stat-label">Logged in as</div>
            <div className="stat-value" style={{ fontSize: '18px', textTransform: 'capitalize' }}>
              {role.replace('_', ' ')}
            </div>
          </div>
        </div>

        {message && (
          <div
            className="card"
            style={{ padding: '10px 16px', marginBottom: '12px', fontSize: '14px' }}
          >
            {message}
          </div>
        )}

        <div className="dashboard-grid">
          <div>
            {role === 'vendor' && (
              <>
                <div className="card" style={{ padding: '16px', marginBottom: '12px' }}>
                  <h3>Store Location</h3>
                  <button
                    className="btn-primary"
                    onClick={handleSetStoreLocation}
                    disabled={locationLoading}
                  >
                    {locationLoading ? '📍 Fetching...' : '📍 Set My Store Location'}
                  </button>
                  {locationStatus && (
                    <p style={{ fontSize: '13px', marginTop: '8px' }}>{locationStatus}</p>
                  )}
                </div>

                <div className="card add-order-form">
                  <h3>Add New Order</h3>
                  <input
                    className="input-field"
                    type="text"
                    placeholder="Customer Name"
                    value={customerName}
                    onChange={(e) => setCustomerName(e.target.value)}
                  />
                  <input
                    className="input-field"
                    type="text"
                    placeholder="Address"
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                  />
                  <button className="btn-primary" onClick={handleAddOrder}>Add Order</button>
                </div>

                <div className="card">
                  <h3>My Orders</h3>
                  {myOrders.filter((o) => o.status === 'pending').length === 0 ? (
                    <p style={{ fontSize: '14px' }}>No pending orders.</p>
                  ) : (
                    myOrders
                      .filter((order) => order.status === 'pending')
                      .map((order) => (
                        <div
                          key={order.id}
                          style={{ padding: '10px 0', borderBottom: '1px solid #eee', fontSize: '14px' }}
                        >
                          <div>
                            <strong>{order.customer_name}</strong> — {order.address}
                          </div>
                          <div style={{ margin: '4px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <StatusBadge status={order.status} />
                            {order.delivery_boy_id && (
                              <span style={{ fontSize: '12px' }}>
                                Assigned to {boyName(order.delivery_boy_id)}
                              </span>
                            )}
                          </div>

                          <div style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
                            <select
                              value={selectedBoy[order.id] ?? order.delivery_boy_id ?? ''}
                              onChange={(e) =>
                                setSelectedBoy({ ...selectedBoy, [order.id]: e.target.value })
                              }
                              style={{ flex: 1, padding: '6px' }}
                            >
                              <option value="">Select delivery boy</option>
                              {deliveryBoys.map((b) => (
                                <option key={b.id} value={b.id}>{b.name}</option>
                              ))}
                            </select>
                            <button
                              className="btn-primary"
                              style={{ padding: '6px 12px' }}
                              onClick={() => handleAssign(order.id)}
                            >
                              Assign
                            </button>
                          </div>
                        </div>
                      ))
                  )}
                </div>
              </>
            )}

            <div className="card">
              <h3>Optimized Delivery Route</h3>
              {hasRoute ? (
                <ol className="route-list">
                  {route.map((order, index) => (
                    <li key={order.id}>
                      <span className="route-number">{index + 1}</span>
                      {order.customer_name} — {order.address}
                      {order.eta_time && (
                        <span
                          style={{
                            marginLeft: '8px',
                            fontSize: '12px',
                            fontWeight: 600,
                            color: '#a15c00'
                          }}
                        >
                          ETA {order.eta_time} ({order.eta_minutes} min)
                        </span>
                      )}
                      {role === 'delivery_boy' && (
                        <button
                          className="btn-primary"
                          style={{ marginLeft: '10px', padding: '4px 10px', fontSize: '12px' }}
                          onClick={() => handleDelivered(order.id)}
                        >
                          Mark delivered
                        </button>
                      )}
                    </li>
                  ))}
                </ol>
              ) : (
                <p style={{ fontSize: '14px' }}>
                  {role === 'delivery_boy'
                    ? 'No orders have been assigned to you yet.'
                    : 'No pending orders.'}
                </p>
              )}
            </div>

            <div className="card">
              <h3>Completed Deliveries</h3>
              {deliveredOrders.length === 0 ? (
                <p style={{ fontSize: '14px' }}>No deliveries completed yet.</p>
              ) : (
                deliveredOrders.map((order) => (
                  <div
                    key={order.id}
                    style={{ padding: '10px 0', borderBottom: '1px solid #eee', fontSize: '14px' }}
                  >
                    <div>
                      <strong>{order.customer_name}</strong> — {order.address}
                    </div>
                    <div style={{ margin: '4px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <StatusBadge status={order.status} />
                      {order.delivered_at && (
                        <span style={{ fontSize: '12px', color: '#5b6673' }}>
                          Delivered at {new Date(order.delivered_at).toLocaleTimeString()}
                        </span>
                      )}
                    </div>
                    <button
                      style={{
                        marginTop: '6px',
                        padding: '4px 10px',
                        fontSize: '12px',
                        border: '1px solid #c0392b',
                        color: '#c0392b',
                        background: 'transparent',
                        borderRadius: '6px',
                        cursor: 'pointer'
                      }}
                      onClick={() => handleUndoDelivered(order.id)}
                    >
                      Undo (mark as pending)
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="card map-card">
            <MapContainer
              key={`${route.map((o) => o.id).join('-')}-${storeLocation ? `${storeLocation.lat}-${storeLocation.lng}` : 'no-store'}`}
              center={mapCenter}
              zoom={12}
              style={{ height: '520px', width: '100%' }}
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; OpenStreetMap contributors'
              />
              {storeLocation && (
                <Marker position={[storeLocation.lat, storeLocation.lng]} icon={storeIcon}>
                  <Popup>Your Store</Popup>
                </Marker>
              )}
              {route.map((order, index) => (
                <Marker
                  key={order.id}
                  position={[order.latitude, order.longitude]}
                  icon={numberedIcon(index + 1)}
                >
                  <Popup>
                    {order.customer_name} — {order.address}
                    {order.eta_time && (
                      <>
                        <br />
                        ETA: {order.eta_time} ({order.eta_minutes} min)
                      </>
                    )}
                  </Popup>
                </Marker>
              ))}
              {role === 'vendor' && deliveryLocations.map((boy) => (
                <Marker key={`boy-${boy.id}`} position={[boy.lat, boy.lng]} icon={boyIcon}>
                  <Popup>
                    {boy.name} — last updated{' '}
                    {boy.updated_at ? new Date(boy.updated_at).toLocaleTimeString() : 'N/A'}
                  </Popup>
                </Marker>
              ))}
              {hasRoute && (
                <Polyline
                  positions={[
                    ...(storeLocation ? [[storeLocation.lat, storeLocation.lng]] : []),
                    ...route.map((order) => [order.latitude, order.longitude])
                  ]}
                  pathOptions={{ color: '#E8871E', weight: 4 }}
                />
              )}
            </MapContainer>
          </div>
        </div>
      </div>
    </div>
  )
}


function App() {
  return (
    <Routes>
      <Route
        path="/"
        element={<Navigate to={sessionStorage.getItem('token') ? '/dashboard' : '/login'} replace />}
      />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
