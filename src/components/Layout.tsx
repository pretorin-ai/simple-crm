import { Link, useLocation } from 'react-router-dom';
import { Home, Users, FileText, LogOut, Shield, Key } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const { user, isAdmin, logout, queueCounts } = useAuth();

  const pendingReassignments = queueCounts?.pending_reassignments || 0;

  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: Home, badge: 0 },
    { path: '/contacts', label: 'Contacts', icon: Users, badge: pendingReassignments },
    { path: '/contracts', label: 'Contracts', icon: FileText, badge: 0 },
    { path: '/api-settings', label: 'API', icon: Key, badge: 0 },
  ];

  // Add admin-only nav items
  if (isAdmin) {
    navItems.push({ path: '/users', label: 'Users', icon: Shield, badge: 0 });
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-4">
            <a href="https://pretorin.com" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2">
              <img
                src="/logo-gray-orange.png"
                alt="Pretorin"
                className="h-8"
              />
            </a>
            <div className="border-l border-border h-8"></div>
            <h1 className="text-lg font-semibold">Simple CRM</h1>
          </div>
          <div className="flex items-center gap-4">
            {user && (
              <>
                <span className="text-sm text-muted-foreground">{user.name}</span>
                <Button variant="outline" size="sm" onClick={logout}>
                  <LogOut className="mr-2 h-4 w-4" />
                  Logout
                </Button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="border-b border-border bg-muted/30">
        <div className="container mx-auto px-4">
          <ul className="flex gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname.startsWith(item.path);
              return (
                <li key={item.path}>
                  <Link
                    to={item.path}
                    className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors ${
                      isActive
                        ? 'border-b-2 border-primary text-foreground'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                    {item.badge > 0 && (
                      <span className="ml-1 inline-flex items-center justify-center px-2 py-0.5 text-xs font-bold leading-none text-white bg-destructive rounded-full">
                        {item.badge}
                      </span>
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      </nav>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">{children}</main>
    </div>
  );
}
