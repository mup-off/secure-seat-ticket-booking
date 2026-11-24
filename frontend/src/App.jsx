import { Link, Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './auth.jsx';
import Home from './pages/Home.jsx';
import EventPage from './pages/EventPage.jsx';
import Login from './pages/Login.jsx';
import Register from './pages/Register.jsx';
import TwoFactorSetup from './pages/TwoFactorSetup.jsx';
import Orders from './pages/Orders.jsx';
import OrderPage from './pages/OrderPage.jsx';
import Dashboard from './pages/organizer/Dashboard.jsx';
import NewEvent from './pages/organizer/NewEvent.jsx';
import ManageEvent from './pages/organizer/ManageEvent.jsx';
import Attendees from './pages/organizer/Attendees.jsx';
import CheckIn from './pages/organizer/CheckIn.jsx';

// Route guards only decide what to show. The real checks are on the server:
// every API call is authorised by Django, whatever this code does.
function RequireUser({ role, children }) {
  const { user } = useAuth();
  if (user === undefined) return <p className="empty">Loading…</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (role && user.role !== role) return <Navigate to="/" replace />;
  if (user.role === 'organizer' && !user.totp_enabled) return <Navigate to="/2fa/setup" replace />;
  return children;
}

function Header() {
  const { user, logout } = useAuth();
  return (
    <header className="site">
      <Link className="brand" to="/">SecureSeat</Link>
      <nav>
        {user ? (
          <>
            {user.role === 'organizer' ? (
              <>
                <Link to="/organizer">My events</Link>
                <Link to="/organizer/checkin">Check-in</Link>
              </>
            ) : (
              <Link to="/orders">My orders</Link>
            )}
            <span className="who">{user.email}</span>
            <button type="button" className="link" onClick={logout}>Log out</button>
          </>
        ) : (
          <>
            <Link to="/login">Log in</Link>
            <Link to="/register">Sign up</Link>
          </>
        )}
      </nav>
    </header>
  );
}

export default function App() {
  return (
    <>
      <Header />
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/events/:id" element={<EventPage />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/2fa/setup" element={<TwoFactorSetup />} />
          <Route path="/orders" element={<RequireUser><Orders /></RequireUser>} />
          <Route path="/orders/:id" element={<RequireUser><OrderPage /></RequireUser>} />
          <Route path="/organizer" element={<RequireUser role="organizer"><Dashboard /></RequireUser>} />
          <Route path="/organizer/events/new" element={<RequireUser role="organizer"><NewEvent /></RequireUser>} />
          <Route path="/organizer/events/:id" element={<RequireUser role="organizer"><ManageEvent /></RequireUser>} />
          <Route path="/organizer/events/:id/attendees" element={<RequireUser role="organizer"><Attendees /></RequireUser>} />
          <Route path="/organizer/checkin" element={<RequireUser role="organizer"><CheckIn /></RequireUser>} />
          <Route path="*" element={<p className="empty">Page not found.</p>} />
        </Routes>
      </main>
      <footer className="site">SecureSeat · event tickets paid with MTN MoMo or Airtel Money</footer>
    </>
  );
}
