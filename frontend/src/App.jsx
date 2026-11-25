import { useEffect, useState } from 'react';
import { Link, Navigate, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from './auth.jsx';
import { useToast } from './toast.jsx';
import { BrandMark, Skeleton } from './ui.jsx';
import Home from './pages/Home.jsx';
import EventPage from './pages/EventPage.jsx';
import Login from './pages/Login.jsx';
import Register from './pages/Register.jsx';
import TwoFactorSetup from './pages/TwoFactorSetup.jsx';
import Orders from './pages/Orders.jsx';
import OrderPage from './pages/OrderPage.jsx';
import Dashboard from './pages/organizer/Dashboard.jsx';
import EventWizard from './pages/organizer/EventWizard.jsx';
import ManageEvent from './pages/organizer/ManageEvent.jsx';
import Attendees from './pages/organizer/Attendees.jsx';
import CheckIn from './pages/organizer/CheckIn.jsx';

// Route guards only decide what to show. The real checks are on the server:
// every API call is authorised by Django, whatever this code does.
function RequireUser({ role, children }) {
  const { user } = useAuth();
  if (user === undefined) return <Skeleton height={180} count={2} />;
  if (!user) return <Navigate to="/login" replace />;
  if (role && user.role !== role) return <Navigate to="/" replace />;
  if (user.role === 'organizer' && !user.totp_enabled) return <Navigate to="/2fa/setup" replace />;
  return children;
}

function Header() {
  const { user, logout } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  useEffect(() => { setOpen(false); }, [location.pathname]);

  async function doLogout() {
    await logout();
    toast('You are logged out. See you at the next show!', 'info');
    navigate('/');
  }

  const link = ({ isActive }) => `nav-link${isActive ? ' active' : ''}`;
  return (
    <header className="site">
      <div className="header-inner">
        <Link className="brand" to="/">
          <BrandMark />
          <span className="brand-name">Secure<span>Seat</span></span>
        </Link>
        <button type="button" className="menu-toggle" onClick={() => setOpen(!open)} aria-expanded={open}>Menu</button>
        <nav className={open ? 'open' : ''}>
          <NavLink to="/" end className={link}>Events</NavLink>
          {user ? (
            <>
              {user.role === 'organizer' ? (
                <>
                  <NavLink to="/organizer" end className={link}>My events</NavLink>
                  <NavLink to="/organizer/checkin" className={link}>Check-in</NavLink>
                </>
              ) : (
                <NavLink to="/orders" className={link}>My tickets</NavLink>
              )}
              <span className="user-chip" title={user.email}>
                <span className="avatar">{user.username[0].toUpperCase()}</span>
                <span>
                  <span className="who">@{user.username}</span>{' '}
                  <span className="role-tag">{user.role}</span>
                </span>
              </span>
              <button type="button" className="secondary" onClick={doLogout}>Log out</button>
            </>
          ) : (
            <>
              <NavLink to="/login" className={link}>Log in</NavLink>
              <Link to="/register" className="button">Sign up</Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => { window.scrollTo(0, 0); }, [pathname]);
  return null;
}

export default function App() {
  return (
    <>
      <ScrollToTop />
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
          <Route path="/organizer/events/:id/edit" element={<RequireUser role="organizer"><EventWizard /></RequireUser>} />
          <Route path="/organizer/events/:id" element={<RequireUser role="organizer"><ManageEvent /></RequireUser>} />
          <Route path="/organizer/events/:id/attendees" element={<RequireUser role="organizer"><Attendees /></RequireUser>} />
          <Route path="/organizer/checkin" element={<RequireUser role="organizer"><CheckIn /></RequireUser>} />
          <Route path="*" element={<section className="card narrow"><h1>Lost backstage</h1><p>That page doesn't exist. <Link to="/">Back to events</Link></p></section>} />
        </Routes>
      </main>
      <footer className="site">
        <div className="zigzag" />
        <div className="footer-inner">
          <span>SecureSeat · tickets for Kigali's concerts, conferences, matches and more</span>
          <span>Pay with MTN MoMo or Airtel Money · we never ask for your PIN</span>
        </div>
      </footer>
    </>
  );
}
