import React, { useState, useEffect } from 'react';
// import { healthCheck } from '../services/api';
import apiService from '../services/api'; // ✅

import './Header.css';

const Header = () => {
  const [isOnline, setIsOnline] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  useEffect(() => {
    const checkHealth = async () => {
      try {
        await apiService.healthCheck();
        setIsOnline(true);
        setLastUpdate(new Date());
      } catch (error) {
        setIsOnline(false);
      }
    };

    // Check health immediately
    checkHealth();

    // Set up interval to check every 30 seconds
    const interval = setInterval(checkHealth, 30000);

    return () => clearInterval(interval);
  }, []);

  const formatTime = (date) => {
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  return (
    <header className="header">
      <div className="header-content">
        <div className="header-left">
          <h1 className="header-title">
            <span className="brand-name">ZOBON</span>
            <span className="brand-subtitle">Campaign Monitoring Dashboard</span>
          </h1>
        </div>
        
        <div className="header-right">
          <div className="status-indicator">
            <div className={`status-dot ${isOnline ? 'online' : 'offline'}`}></div>
            <span className="status-text">
              {isOnline ? 'Online' : 'Offline'}
            </span>
          </div>
          
          <div className="last-update">
            <span className="update-label">Last Update:</span>
            <span className="update-time">{formatTime(lastUpdate)}</span>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;