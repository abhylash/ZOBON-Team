import React, { useState, useEffect } from 'react';
import './App.css';
import Header from './components/Header';
import Footer from './components/Footer';
import SankalpScoreCard from './components/SankalpScoreCard';
import SentimentTrendChart from './components/SentimentTrendChart';
import BiasAlertsTable from './components/BiasAlertsTable';
import apiService from './services/api';
import AskAIBox from './components/AskAIBox';
import FullDashboard from './components/FullDashboard';

function App() {
  const [overview, setOverview] = useState({});
  const [brands, setBrands] = useState([]);
  const [selectedBrand, setSelectedBrand] = useState('');
  const [sentimentTrends, setSentimentTrends] = useState([]);
  const [biasDistribution, setBiasDistribution] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [alertSeverityData, setAlertSeverityData] = useState([]);
  const [biasHeatmapData, setBiasHeatmapData] = useState([]);
  const [brandTrustData, setBrandTrustData] = useState([]);

  const [loading, setLoading] = useState(true);
  const [overviewError, setOverviewError] = useState(null);
  const [brandsError, setBrandsError] = useState(null);
  const [alertsError, setAlertsError] = useState(null);

  const fetchDashboardData = async () => {
    setLoading(true);
    setOverviewError(null);
    setBrandsError(null);
    setAlertsError(null);

    try {
      const overviewData = await apiService.getDashboardOverview();
      setOverview(overviewData?.data || {});
    } catch (err) {
      setOverviewError('Failed to load dashboard overview');
    }

    try {
      const brandsData = await apiService.getBrands();
      const extractedBrands = Array.isArray(brandsData?.data)
        ? brandsData.data
        : Array.isArray(brandsData)
        ? brandsData
        : [];
      setBrands(extractedBrands);
    } catch (err) {
      setBrandsError('Failed to load brands');
    }

    try {
      const alertsData = await apiService.getAlerts();
      const extractedAlerts = Array.isArray(alertsData?.data)
        ? alertsData.data
        : Array.isArray(alertsData)
        ? alertsData
        : [];
      setAlerts(extractedAlerts);
    } catch (err) {
      setAlertsError('Failed to load alerts');
    }

    setLoading(false);
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  useEffect(() => {
    const fetchBrandSpecificData = async () => {
      try {
        const [trends, bias, alertSeverity, biasHeatmap, brandTrust] = await Promise.all([
          apiService.getSentimentTrends(selectedBrand || null, 180),
          apiService.getBiasDistribution(selectedBrand || null, 180),
          apiService.getAlertSeverityData(selectedBrand || null, 180),
          apiService.getBiasHeatmapData(selectedBrand || null, 180),
          apiService.getBrandTrustTrends(selectedBrand || null, 180),
        ]);

        setSentimentTrends(Array.isArray(trends?.data) ? trends.data : []);
        setBiasDistribution(Array.isArray(bias?.data) ? bias.data : []);
        setAlertSeverityData(Array.isArray(alertSeverity?.data) ? alertSeverity.data : []);
        setBiasHeatmapData(Array.isArray(biasHeatmap?.data) ? biasHeatmap.data : []);
        setBrandTrustData(Array.isArray(brandTrust?.data) ? brandTrust.data : []);

        console.log("Selected Brand:", selectedBrand);
        console.log("API response for trends:", trends);
      } catch (err) {
        console.error('Error fetching trend or bias data:', err);
      }
    };

    fetchBrandSpecificData();
  }, [selectedBrand]);

  const handleBrandChange = (brand) => {
    setSelectedBrand(brand);
  };

  if (loading) {
    return (
      <div className="App">
        <Header />
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading dashboard...</p>
        </div>
        <Footer />
      </div>
    );
  }

  if (overviewError || brandsError || alertsError) {
    return (
      <div className="App">
        <Header />
        <div className="error-container">
          <h2>Error</h2>
          {overviewError && <p>{overviewError}</p>}
          {brandsError && <p>{brandsError}</p>}
          {alertsError && <p>{alertsError}</p>}
          <button onClick={fetchDashboardData} className="retry-button">
            Retry
          </button>
        </div>
        <Footer />
      </div>
    );
  }

  return (
    <div className="App">
      <Header />
      <div className="dashboard-container">
        {/* Brand Selector */}
        <div className="brand-selector-container">
          <label htmlFor="brand-select">Select Brand:</label>
          <select
            id="brand-select"
            value={selectedBrand}
            onChange={(e) => handleBrandChange(e.target.value)}
            className="brand-select"
          >
            <option value="">All Brands</option>
            {Array.isArray(brands) &&
              brands.map((brand) => (
                <option key={brand.brand} value={brand.brand}>
                  {brand.brand} ({brand.mention_count} mentions)
                </option>
              ))}
          </select>
        </div>

        {/* AI Assistant */}
        <div className="ai-assistant-container">
          <AskAIBox />
        </div>

        {/* Overview Cards */}
        <div className="overview-cards">
          <SankalpScoreCard
            title="Total Campaigns"
            value={overview.total_campaigns || 0}
            trend={overview.total_campaigns > 0 ? '+' : ''}
            color="#4CAF50"
          />
          <SankalpScoreCard
            title="Average Trust Score"
            value={overview.avg_trust_score || 0}
            trend={
              overview.avg_trust_score > 70
                ? '+'
                : overview.avg_trust_score < 50
                ? '-'
                : ''
            }
            color={
              overview.avg_trust_score > 70
                ? '#4CAF50'
                : overview.avg_trust_score < 50
                ? '#f44336'
                : '#FF9800'
            }
          />
          <SankalpScoreCard
            title="Low Trust Campaigns"
            value={overview.low_trust_campaigns || 0}
            trend={overview.low_trust_campaigns > 0 ? '-' : ''}
            color="#f44336"
          />
          <SankalpScoreCard
            title="Active Brands"
            value={overview.total_brands || 0}
            trend=""
            color="#2196F3"
          />
        </div>

        {/* ✅ FIXED: Sentiment Trend Chart with Data */}
        <div className="sentiment-trend-chart">
          <SentimentTrendChart 
            data={sentimentTrends} 
            title={`Sentiment Trends for ${selectedBrand || 'All Brands'}`} 
          />
        </div>

        {/* Alerts Table */}
        <div className="alerts-section">
          <BiasAlertsTable
            alerts={Array.isArray(alerts) ? alerts : []}
            loading={loading}
            error={alertsError}
            onRefresh={fetchDashboardData}
          />
        </div>

        {/* ZOBON Dashboard */}
        <div className="min-h-screen bg-gray-50">
          <FullDashboard />
        </div>
      </div>
      <Footer />
    </div>
  );
}

export default App;
