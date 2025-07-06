import React from 'react';
import './SankalpScoreCard.css';

const SankalpScoreCard = ({ title, value, trend, color, subtitle, icon }) => {
  const getTrendIcon = () => {
    if (trend === '+') return '↗️';
    if (trend === '-') return '↘️';
    return '';
  };

  const getTrendClass = () => {
    if (trend === '+') return 'trend-positive';
    if (trend === '-') return 'trend-negative';
    return 'trend-neutral';
  };

  const formatValue = (val) => {
    if (typeof val === 'number') {
      if (val > 1000) {
        return (val / 1000).toFixed(1) + 'K';
      }
      return val.toFixed(1);
    }
    return val;
  };

  return (
    <div className="scorecard" style={{ borderLeftColor: color }}>
      <div className="scorecard-header">
        <div className="scorecard-title">
          {icon && <span className="scorecard-icon">{icon}</span>}
          {title}
        </div>
        {trend && (
          <div className={`scorecard-trend ${getTrendClass()}`}>
            {getTrendIcon()}
          </div>
        )}
      </div>
      
      <div className="scorecard-value" style={{ color }}>
        {formatValue(value)}
      </div>
      
      {subtitle && (
        <div className="scorecard-subtitle">
          {subtitle}
        </div>
      )}
      
      <div className="scorecard-footer">
        <div className="scorecard-indicator" style={{ backgroundColor: color }}></div>
      </div>
    </div>
  );
};

export default SankalpScoreCard;