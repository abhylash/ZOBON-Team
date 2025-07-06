import React, { useEffect, useState } from 'react';
import dayjs from 'dayjs';
import './zobon-dashboard.css'; // Adjust path as needed
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ScatterChart,
  Scatter,
  LineChart,
  Line,
  Cell,
} from 'recharts';

const ECO_COLORS = [
  '#2E7D32', '#4CAF50', '#81C784', '#A5D6A7', '#66BB6A',
  '#388E3C', '#4DB6AC', '#26A69A', '#00897B', '#009688',
  '#8BC34A', '#689F38'
];

const ECO_GRADIENT_COLORS = [
  { start: '#4CAF50', end: '#2E7D32' },
  { start: '#81C784', end: '#4CAF50' },
  { start: '#A5D6A7', end: '#66BB6A' },
  { start: '#4DB6AC', end: '#26A69A' },
  { start: '#8BC34A', end: '#689F38' },
  { start: '#00897B', end: '#009688' },
];

export default function FullDashboard() {
  const [brands, setBrands] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [brandsResponse, alertsResponse] = await Promise.all([
          fetch('http://localhost:5001/api/brands').then(res => res.json()),
          fetch('http://localhost:5001/api/alerts?limit=500').then(res => res.json())
        ]);
        setBrands(brandsResponse || []);
        setAlerts(alertsResponse || []);
      } catch (err) {
        setError('Failed to load dashboard data');
        console.error('Dashboard error:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="zobon-tooltip">
          <p className="zobon-tooltip-label">{label}</p>
          {payload.map((entry, index) => (
            <p key={index} className="zobon-tooltip-item">
              <span className="zobon-tooltip-indicator" style={{ backgroundColor: entry.color }}></span>
              {`${entry.name}: ${typeof entry.value === 'number' ? entry.value.toFixed(2) : entry.value}`}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  const trustData = brands.map(({ brand, avg_trust_score }) => ({
    brand,
    avg_trust_score: Number(avg_trust_score.toFixed(2)),
  }));

  const scatterData = brands.map(({ brand, avg_trust_score, mention_count }) => ({
    brand,
    avg_trust_score: Number(avg_trust_score.toFixed(2)),
    mention_count,
  }));

  const alertLevels = Array.from(new Set(alerts.map(a => a.alert_level)));
  const brandAlertLevelMap = {};
  brands.forEach(({ brand }) => { brandAlertLevelMap[brand] = {}; });
  alerts.forEach(({ brand, alert_level }) => {
    if (brandAlertLevelMap[brand]) {
      brandAlertLevelMap[brand][alert_level] = (brandAlertLevelMap[brand][alert_level] || 0) + 1;
    }
  });
  const stackedBarData = brands.map(({ brand }) => {
    const item = { brand };
    alertLevels.forEach(level => {
      item[level] = brandAlertLevelMap[brand][level] || 0;
    });
    return item;
  });

  const brandDateMap = {};
  alerts.forEach(({ brand, trust_score, timestamp }) => {
    if (!brand || trust_score == null || !timestamp) return;
    const date = dayjs(timestamp).format('YYYY-MM-DD');
    const key = `${brand}-${date}`;
    if (!brandDateMap[key]) brandDateMap[key] = { brand, date, trustScores: [] };
    brandDateMap[key].trustScores.push(trust_score);
  });
  const trendData = Object.values(brandDateMap).map(({ brand, date, trustScores }) => ({
    brand,
    date,
    avgTrustScore: trustScores.reduce((a, b) => a + b, 0) / trustScores.length,
  }));
  const uniqueDates = Array.from(new Set(trendData.map(d => d.date))).sort();
  const uniqueBrands = Array.from(new Set(trendData.map(d => d.brand)));
  const lineChartData = uniqueDates.map(date => {
    const entry = { date };
    uniqueBrands.forEach(brand => {
      const found = trendData.find(d => d.brand === brand && d.date === date);
      entry[brand] = found ? Number(found.avgTrustScore.toFixed(2)) : null;
    });
    return entry;
  });

  if (loading) {
    return (
      <div className="zobon-loading">
        <div className="zobon-loading-content">
          <div className="zobon-loading-spinner"></div>
          <p className="zobon-loading-text">Loading Zobon EV Analytics...</p>
          <p className="zobon-loading-subtext">Powering sustainable mobility insights</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="zobon-error">
        <div className="zobon-error-content">
          <div className="zobon-error-icon">⚡</div>
          <h2 className="zobon-error-title">Connection Error</h2>
          <p className="zobon-error-message">{error}</p>
          <button onClick={() => window.location.reload()} className="zobon-error-button">
            🔄 Reconnect Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="zobon-dashboard">
      <div className="zobon-grid">
        <div className="zobon-chart-container">
          <div className="zobon-chart-header">
            <h2><span className="pulse-dot"></span>⚡ Brand Trust Performance</h2>
          </div>
          <div className="zobon-chart-content">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={trustData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="brand" />
                <YAxis domain={[0, 100]} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="avg_trust_score" fill="#4CAF50" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="zobon-chart-container">
          <div className="zobon-chart-header">
            <h2><span className="pulse-dot"></span>🔋 Brand Visibility Matrix</h2>
            <p>Market presence vs consumer trust analysis</p>
          </div>
          <div className="zobon-chart-content">
            <ResponsiveContainer width="100%" height={300}>
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="mention_count" name="Mentions" />
                <YAxis dataKey="avg_trust_score" name="Trust Score" domain={[0, 100]} />
                <Tooltip content={<CustomTooltip />} />
                <Scatter name="Brands" data={scatterData} fill="#81C784" />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="zobon-chart-container">
          <div className="zobon-chart-header">
            <h2><span className="pulse-dot"></span>⚠️ Alert Distribution</h2>
            <p>Brand monitoring and alert severity breakdown</p>
          </div>
          <div className="zobon-chart-content">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={stackedBarData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="brand" />
                <YAxis />
                <Tooltip content={<CustomTooltip />} />
                <Legend />
                {alertLevels.map((level, idx) => (
                  <Bar key={level} dataKey={level} stackId="a" fill={ECO_COLORS[idx % ECO_COLORS.length]} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="zobon-chart-container">
          <div className="zobon-chart-header">
            <h2><span className="pulse-dot"></span>📈 Trust Evolution Timeline</h2>
            <p>Brand trust performance over time</p>
          </div>
          <div className="zobon-chart-content">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={lineChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis domain={[0, 100]} />
                <Tooltip content={<CustomTooltip />} />
                <Legend />
                {uniqueBrands.map((brand, idx) => (
                  <Line
                    key={brand}
                    type="monotone"
                    dataKey={brand}
                    stroke={ECO_COLORS[idx % ECO_COLORS.length]}
                    strokeWidth={2}
                    dot={{ r: 3 }}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      
    </div>
  );
}
