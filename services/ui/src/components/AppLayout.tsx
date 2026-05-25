import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

const navigationItems = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/demo", label: "Drone demo" },
  { to: "/cameras", label: "Cameras" },
  { to: "/zones", label: "Zones" },
  { to: "/rules", label: "Rules" },
  { to: "/events", label: "Events" },
  { to: "/status", label: "Status" }
];

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function onLogout() {
    await logout();
    navigate("/login");
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span>VA</span>
          <div>
            <h1>Video Analytics</h1>
            <p>Command Center</p>
          </div>
        </div>
        <nav className="sidebar-nav" aria-label="Main navigation">
          {navigationItems.map((item) => (
            <NavLink className="nav-link" key={item.to} to={item.to}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="operator-card">
          <small>Operator</small>
          <strong>{user?.username ?? "unknown"}</strong>
        </div>
        <button className="danger logout-button" onClick={onLogout}>
          Logout
        </button>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
