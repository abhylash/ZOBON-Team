import React, { useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from 'recharts';
import './SentimentTrendChart.css';

const SentimentTrendChart = ({ data, title = 'Sentiment Trends' }) => {
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return [];
    
    return data.map(item => ({
      date: new Date(item.date).toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric' 
      }),
      sentiment: (item.avg_sentiment * 100).toFixed(1), // Convert to percentage
      trustScore: item.avg_trust_score,
      mentions: item.mention_count,
      fullDate: item.date
    }));
  }, [data]);

console.log('Chart Data:', chartData);

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="custom-tooltip">
          <p className="tooltip-label">{`Date: ${label}`}</p>
          {payload.map((entry, index) => (
            <p key={index} className="tooltip-entry" style={{ color: entry.color }}>
              {entry.dataKey === 'sentiment' && `Sentiment: ${entry.value}%`}
              {entry.dataKey === 'trustScore' && `Trust Score: ${entry.value}`}
              {entry.dataKey === 'mentions' && `Mentions: ${entry.value}`}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  if (!chartData || chartData.length === 0) {
    return (
      <div className="chart-container">
        <h3 className="chart-title">{title}</h3>
        <div className="chart-no-data">
          <p>No data available for the selected period</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chart-container">
      <h3 className="chart-title">{title}</h3>
      
      <div className="chart-wrapper">
        <ResponsiveContainer width="100%" height={400}>
          <AreaChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <defs>
              <linearGradient id="sentimentGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#8884d8" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="#8884d8" stopOpacity={0.1}/>
              </linearGradient>
              <linearGradient id="trustGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#82ca9d" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="#82ca9d" stopOpacity={0.1}/>
              </linearGradient>
            </defs>
            
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis 
              dataKey="date" 
              stroke="#666"
              fontSize={12}
            />
            <YAxis 
              stroke="#666"
              fontSize={12}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            
            <Area
              type="monotone"
              dataKey="sentiment"
              stroke="#8884d8"
              fillOpacity={1}
              fill="url(#sentimentGradient)"
              name="Sentiment %"
            />
            <Area
              type="monotone"
              dataKey="trustScore"
              stroke="#82ca9d"
              fillOpacity={1}
              fill="url(#trustGradient)"
              name="Trust Score"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      
      {/* Summary Stats */}
      <div className="chart-summary">
        <div className="summary-item">
          <span className="summary-label">Avg Sentiment:</span>
          <span className="summary-value sentiment">
            {(chartData.reduce((sum, item) => sum + parseFloat(item.sentiment), 0) / chartData.length).toFixed(1)}%
          </span>
        </div>
        <div className="summary-item">
          <span className="summary-label">Avg Trust Score:</span>
          <span className="summary-value trust">
            {(chartData.reduce((sum, item) => sum + parseFloat(item.trustScore), 0) / chartData.length).toFixed(1)}
          </span>
        </div>
        <div className="summary-item">
          <span className="summary-label">Total Mentions:</span>
          <span className="summary-value mentions">
            {chartData.reduce((sum, item) => sum + parseInt(item.mentions), 0)}
          </span>
        </div>
      </div>
      

    </div>
  );
};

export default SentimentTrendChart;