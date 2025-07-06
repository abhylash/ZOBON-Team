// src/components/Footer.jsx
import React from 'react';
import './Footer.css';

const Footer = () => {
  return (
    <footer className="zobon-footer">
      <div className="footer-content">
        <p className="copyright">&copy; {new Date().getFullYear()} ZOBON — Ethical EV Insights</p>
        <p className="footer-message">Made with 🌱 for a greener future</p>
      </div>
    </footer>
  );
};

export default Footer;