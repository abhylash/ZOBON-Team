from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
from datetime import datetime
import os
import sys

# Add the processing directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from processing import db_writer

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})


@app.route('/api/dashboard/overview', methods=['GET'])
def get_dashboard_overview():
    conn = None
    try:
        conn = db_writer.connection_pool.getconn()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                COUNT(*) as total_campaigns,
                AVG(trust_score) as avg_trust_score,
                COUNT(CASE WHEN trust_score < 30 THEN 1 END) as low_trust_campaigns,
                COUNT(DISTINCT brand) as total_brands
            FROM campaign_scores 
            WHERE created_at >= NOW() - INTERVAL '7 days'
        """)
        overview = cursor.fetchone()

        cursor.execute("""
            SELECT COUNT(*) 
            FROM bias_alerts 
            WHERE resolved = FALSE AND created_at >= NOW() - INTERVAL '24 hours'
        """)
        recent_alerts = cursor.fetchone()[0]

        cursor.execute("""
            SELECT 
                CASE 
                    WHEN sentiment > 0.1 THEN 'positive'
                    WHEN sentiment < -0.1 THEN 'negative'
                    ELSE 'neutral'
                END as sentiment_category,
                COUNT(*) as count
            FROM campaign_scores 
            WHERE created_at >= NOW() - INTERVAL '7 days'
            GROUP BY sentiment_category
        """)
        sentiment_dist = cursor.fetchall()

        return jsonify({
            'total_campaigns': overview[0] or 0,
            'avg_trust_score': round(overview[1] or 0, 2),
            'low_trust_campaigns': overview[2] or 0,
            'total_brands': overview[3] or 0,
            'recent_alerts': recent_alerts,
            'sentiment_distribution': {row[0]: row[1] for row in sentiment_dist}
        })

    except Exception as e:
        logger.error(f"Error fetching dashboard overview: {e}")
        return jsonify({'error': 'Failed to fetch overview data'}), 500
    finally:
        if conn:
            db_writer.connection_pool.putconn(conn)


@app.route('/api/brands/<brand>/scores', methods=['GET'])
def get_brand_scores(brand):
    try:
        limit = request.args.get('limit', 100, type=int)
        scores = db_writer.get_brand_scores(brand, limit)
        return jsonify(scores)
    except Exception as e:
        logger.error(f"Error fetching brand scores: {e}")
        return jsonify({'error': 'Failed to fetch brand scores'}), 500


@app.route('/api/brands', methods=['GET'])
def get_brands():
    conn = None
    try:
        conn = db_writer.connection_pool.getconn()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT brand, 
                   COUNT(*) as mention_count,
                   AVG(trust_score) as avg_trust_score,
                   MAX(timestamp) as last_mention
            FROM campaign_scores 
            WHERE created_at >= NOW() - INTERVAL '30 days'
            GROUP BY brand 
            ORDER BY mention_count DESC
        """)

        brands = []
        for row in cursor.fetchall():
            brands.append({
                'brand': row[0],
                'mention_count': row[1],
                'avg_trust_score': round(row[2], 2),
                'last_mention': row[3].isoformat() if row[3] else None
            })

        return jsonify(brands)

    except Exception as e:
        logger.error(f"Error fetching brands: {e}")
        return jsonify({'error': 'Failed to fetch brands'}), 500
    finally:
        if conn:
            db_writer.connection_pool.putconn(conn)


@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    try:
        limit = request.args.get('limit', 50, type=int)
        alerts = db_writer.get_recent_alerts(limit)
        for alert in alerts:
            if alert.get('timestamp'):
                alert['timestamp'] = alert['timestamp'].isoformat()
            if alert.get('created_at'):
                alert['created_at'] = alert['created_at'].isoformat()
        return jsonify(alerts)
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        return jsonify({'error': 'Failed to fetch alerts'}), 500


@app.route('/api/alerts/<int:alert_id>/resolve', methods=['POST'])
def resolve_alert(alert_id):
    conn = None
    try:
        conn = db_writer.connection_pool.getconn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE bias_alerts 
            SET resolved = TRUE 
            WHERE id = %s
        """, (alert_id,))
        conn.commit()

        if cursor.rowcount > 0:
            return jsonify({'success': True, 'message': 'Alert resolved'})
        else:
            return jsonify({'error': 'Alert not found'}), 404

    except Exception as e:
        logger.error(f"Error resolving alert: {e}")
        return jsonify({'error': 'Failed to resolve alert'}), 500
    finally:
        if conn:
            db_writer.connection_pool.putconn(conn)


@app.route('/api/sentiment-trends', methods=['GET'])
def get_sentiment_trends():
    conn = None
    try:
        brand = request.args.get('brand')
        days = request.args.get('days', 7, type=int)

        conn = db_writer.connection_pool.getconn()
        cursor = conn.cursor()

        where_clause = ""
        params = [days]

        if brand:
            where_clause = "AND brand = %s"
            params.append(brand)

        cursor.execute(f"""
            SELECT 
                DATE(timestamp) as date,
                AVG(sentiment) as avg_sentiment,
                AVG(trust_score) as avg_trust_score,
                COUNT(*) as mention_count
            FROM campaign_scores 
            WHERE timestamp >= NOW() - INTERVAL '%s days' {where_clause}
            GROUP BY DATE(timestamp)
            ORDER BY date
        """, params)

        trends = []
        for row in cursor.fetchall():
            trends.append({
                'date': row[0].isoformat(),
                'avg_sentiment': round(row[1], 3),
                'avg_trust_score': round(row[2], 2),
                'mention_count': row[3]
            })

        return jsonify(trends)

    except Exception as e:
        logger.error(f"Error fetching sentiment trends: {e}")
        return jsonify({'error': 'Failed to fetch sentiment trends'}), 500
    finally:
        if conn:
            db_writer.connection_pool.putconn(conn)


@app.route('/api/bias-distribution', methods=['GET'])
def get_bias_distribution():
    conn = None
    try:
        brand = request.args.get('brand')
        days = request.args.get('days', 7, type=int)

        conn = db_writer.connection_pool.getconn()
        cursor = conn.cursor()

        where_clause = ""
        params = [days]

        if brand:
            where_clause = "AND brand = %s"
            params.append(brand)

        cursor.execute(f"""
            SELECT bias, COUNT(*) as count
            FROM campaign_scores 
            WHERE timestamp >= NOW() - INTERVAL '%s days' {where_clause}
            GROUP BY bias
            ORDER BY count DESC
        """, params)

        distribution = []
        for row in cursor.fetchall():
            distribution.append({
                'bias_type': row[0],
                'count': row[1]
            })

        return jsonify(distribution)

    except Exception as e:
        logger.error(f"Error fetching bias distribution: {e}")
        return jsonify({'error': 'Failed to fetch bias distribution'}), 500
    finally:
        if conn:
            db_writer.connection_pool.putconn(conn)


@app.route('/api/performance/<brand>', methods=['GET'])
def get_brand_performance(brand):
    conn = None
    try:
        days = request.args.get('days', 30, type=int)

        conn = db_writer.connection_pool.getconn()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM brand_performance 
            WHERE brand = %s AND date >= NOW() - INTERVAL '%s days'
            ORDER BY date DESC
        """, (brand, days))

        performance = []
        for row in cursor.fetchall():
            performance.append({
                'date': row[2].isoformat(),
                'avg_trust_score': row[3],
                'total_mentions': row[4],
                'positive_sentiment_pct': row[5],
                'negative_sentiment_pct': row[6],
                'bias_violations': row[7]
            })

        return jsonify(performance)

    except Exception as e:
        logger.error(f"Error fetching brand performance: {e}")
        return jsonify({'error': 'Failed to fetch brand performance'}), 500
    finally:
        if conn:
            db_writer.connection_pool.putconn(conn)


@app.route('/api/alert-severity', methods=['GET'])
def get_alert_severity():
    conn = None
    try:
        brand = request.args.get('brand')
        days = request.args.get('days', 7, type=int)

        conn = db_writer.connection_pool.getconn()
        cursor = conn.cursor()

        sql = f"""
            SELECT alert_level, COUNT(*) as count
            FROM bias_alerts
            WHERE created_at >= NOW() - INTERVAL '{days} days'
        """
        params = []

        if brand:
            sql += " AND brand = %s"
            params.append(brand)

        sql += " GROUP BY alert_level"

        cursor.execute(sql, params)

        result = [{'label': row[0], 'count': row[1]} for row in cursor.fetchall()]
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error fetching alert severity data: {e}")
        return jsonify({'error': 'Failed to fetch alert severity'}), 500
    finally:
        if conn:
            db_writer.connection_pool.putconn(conn)






@app.route('/api/bias-heatmap', methods=['GET'])
def get_bias_heatmap():
    conn = None
    try:
        brand = request.args.get('brand')
        days = request.args.get('days', 7, type=int)

        conn = db_writer.connection_pool.getconn()
        cursor = conn.cursor()

        where_clause = ""
        params = [days]

        if brand:
            where_clause = "AND brand = %s"
            params.append(brand)

        cursor.execute(f"""
            SELECT brand, bias, COUNT(*) as count
            FROM campaign_scores
            WHERE created_at >= NOW() - INTERVAL '%s days' {where_clause}
            GROUP BY brand, bias
        """, params)

        result = [{'brand': row[0], 'bias_type': row[1], 'count': row[2]} for row in cursor.fetchall()]
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error fetching bias heatmap data: {e}")
        return jsonify({'error': 'Failed to fetch bias heatmap'}), 500
    finally:
        if conn:
            db_writer.connection_pool.putconn(conn)


@app.route('/api/brand-trust-trends', methods=['GET'])
def get_brand_trust_trends():
    conn = None
    try:
        brand = request.args.get('brand')
        days = request.args.get('days', 7, type=int)

        conn = db_writer.connection_pool.getconn()
        cursor = conn.cursor()

        where_clause = ""
        params = [days]

        if brand:
            where_clause = "AND brand = %s"
            params.append(brand)

        cursor.execute(f"""
            SELECT brand, date, AVG(avg_trust_score)
            FROM brand_performance
            WHERE date >= NOW() - INTERVAL '%s days' {where_clause}
            GROUP BY brand, date
            ORDER BY date
        """, params)

        result = [
            {'brand': row[0], 'date': row[1].isoformat(), 'avg_trust_score': round(row[2], 2)}
            for row in cursor.fetchall()
        ]
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error fetching brand trust trends: {e}")
        return jsonify({'error': 'Failed to fetch trust trends'}), 500
    finally:
        if conn:
            db_writer.connection_pool.putconn(conn)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
