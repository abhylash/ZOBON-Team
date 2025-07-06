import React, { useState } from 'react';
import './BiasAlertsTable.css';

const BiasAlertsTable = ({ alerts: initialAlerts = [], loading, error, onRefresh }) => {
  const [resolvingIds, setResolvingIds] = useState(new Set());
  const [alerts, setAlerts] = useState(initialAlerts);

  const handleResolveAlert = async (alertId) => {
    if (resolvingIds.has(alertId)) return;

    try {
      setResolvingIds(prev => new Set(prev).add(alertId));

      // Optional: call backend to resolve alert
      // await apiService.resolveAlert(alertId);

      // Simulate local removal
      setAlerts(prevAlerts => prevAlerts.filter(alert => alert.id !== alertId));
    } catch (err) {
      console.error('Error resolving alert:', err);
      alert('Failed to resolve alert');
    } finally {
      setResolvingIds(prev => {
        const newSet = new Set(prev);
        newSet.delete(alertId);
        return newSet;
      });
    }
  };

  const getAlertLevelClass = (level) => {
    switch ((level || '').toLowerCase()) {
      case 'critical': return 'alert-critical';
      case 'high': return 'alert-high';
      case 'medium': return 'alert-medium';
      case 'low': return 'alert-low';
      default: return 'alert-medium';
    }
  };

  const getAlertLevelIcon = (level) => {
    switch ((level || '').toLowerCase()) {
      case 'critical': return '🚨';
      case 'high': return '⚠️';
      case 'medium': return '⚡';
      case 'low': return 'ℹ️';
      default: return '⚡';
    }
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading && alerts.length === 0) {
    return (
      <div className="alerts-container">
        <h3>Recent Bias Alerts</h3>
        <div className="alerts-loading">Loading alerts...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alerts-container">
        <h3>Recent Bias Alerts</h3>
        <div className="alerts-error">
          <p>{error}</p>
          <button onClick={onRefresh} className="retry-button">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="alerts-container">
      <div className="alerts-header">
        <h3>Recent Bias Alerts</h3>
        <div className="alerts-actions">
          <button 
            onClick={onRefresh} 
            className="refresh-button"
            disabled={loading}
          >
            {loading ? '⏳' : '🔄'} Refresh
          </button>
          <span className="alerts-count">
            {alerts.length} active alerts
          </span>
        </div>
      </div>

      {alerts.length === 0 ? (
        <div className="alerts-empty">
          <p>🎉 No active alerts! All campaigns are performing well.</p>
        </div>
      ) : (
        <div className="alerts-table-container">
          <table className="alerts-table">
            <thead>
              <tr>
                <th>Level</th>
                <th>Brand</th>
                <th>Bias Type</th>
                <th>Trust Score</th>
                <th>Sample Text</th>
                <th>Time</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((alert) => (
                <tr key={alert.id} className="alert-row">
                  <td className="alert-level">
                    <span className={`alert-badge ${getAlertLevelClass(alert.alert_level)}`}>
                      {getAlertLevelIcon(alert.alert_level)}
                      {alert.alert_level}
                    </span>
                  </td>
                  <td className="alert-brand">
                    <strong>{alert.brand}</strong>
                  </td>
                  <td className="alert-bias-type">{alert.bias_type}</td>
                  <td className="alert-trust-score">
                    <span className={`trust-score ${alert.trust_score < 30 ? 'critical' : alert.trust_score < 50 ? 'warning' : 'good'}`}>
                      {alert.trust_score?.toFixed(1)}
                    </span>
                  </td>
                  <td className="alert-text">
                    <div className="text-sample" title={alert.text_sample}>
                      {alert.text_sample}
                    </div>
                  </td>
                  <td className="alert-timestamp">
                    {formatTimestamp(alert.timestamp)}
                  </td>
                  <td className="alert-actions">
                    <button
                      onClick={() => handleResolveAlert(alert.id)}
                      disabled={resolvingIds.has(alert.id)}
                      className="resolve-button"
                    >
                      {resolvingIds.has(alert.id) ? '⏳' : '✅'} Resolve
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default BiasAlertsTable;
