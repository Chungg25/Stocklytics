import React, { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useAgent } from '../../contexts/AgentContext';
import { Target, Search, Moon, Settings, ChevronDown, LogOut, User, Bot } from 'lucide-react';

const TopNav = () => {
  const { user, signOut } = useAuth();
  const { toggleAgent, isAgentOpen } = useAgent();
  const navigate = useNavigate();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setShowUserMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSignOut = async () => {
    await signOut();
    navigate('/login');
  };

  return (
    <header className="bg-dark-sidebar border-b border-dark-border h-14 flex items-center justify-between px-4 md:px-6 fixed top-0 left-20 md:left-24 right-0 z-40">
      <div className="flex items-center gap-8">
        <div className="flex items-center gap-2 cursor-pointer">
          <Target size={24} className="text-primary" />
          <span className="text-xl font-bold text-white tracking-wide">Alphahubiq</span>
        </div>
        
        <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-text-primary">
          <Link to="/screeners" className="hover:text-primary transition-colors flex items-center gap-1">
            AI Picks <span className="text-primary text-xs">✦</span>
          </Link>
          <Link to="/chart" className="hover:text-primary transition-colors flex items-center gap-1">
            Tools <ChevronDown size={14} />
          </Link>
          <Link to="/screeners" className="hover:text-primary transition-colors flex items-center gap-1">
            Best Stocks <ChevronDown size={14} />
          </Link>
        </nav>
      </div>

      <div className="flex items-center gap-3">
        <button className="p-2 rounded-lg hover:bg-dark-hover text-text-muted hover:text-text-primary transition-colors">
          <Settings size={18} />
        </button>
        
        {user ? (
          <div className="relative" ref={menuRef}>
            <button 
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-dark-hover transition-colors"
            >
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-primary to-stock-green flex items-center justify-center text-white text-xs font-bold">
                {user.email?.[0]?.toUpperCase() || 'U'}
              </div>
              <ChevronDown size={14} className="text-text-muted" />
            </button>
            
            {showUserMenu && (
              <div className="absolute right-0 top-full mt-2 w-56 bg-dark-card border border-dark-border rounded-xl shadow-2xl py-2 z-50">
                <div className="px-4 py-2 border-b border-dark-border">
                  <p className="text-xs text-text-muted">Signed in as</p>
                  <p className="text-sm text-white font-medium truncate">{user.email}</p>
                </div>
                <button 
                  onClick={handleSignOut}
                  className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-stock-red hover:bg-dark-hover transition-colors"
                >
                  <LogOut size={16} /> Sign Out
                </button>
              </div>
            )}
          </div>
        ) : (
          <Link 
            to="/login" 
            className="px-4 py-1.5 text-sm font-semibold text-white bg-primary hover:bg-primary-hover rounded-lg transition-colors"
          >
            Login
          </Link>
        )}
      </div>
    </header>
  );
};

export default TopNav;
