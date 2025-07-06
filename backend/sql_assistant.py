from flask import Flask, request, jsonify
from flask_cors import CORS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain.agents import AgentType
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import Document
from dotenv import load_dotenv
import google.generativeai as genai
import os
import traceback
import re
from google.api_core.exceptions import ResourceExhausted

load_dotenv()

app = Flask(__name__)
CORS(app)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}}, supports_credentials=True)

db = None
vectorstore = None
gemini_model = None
sql_agent = None

def initialize_database():
    global db
    try:
        db_user = os.getenv('POSTGRES_USER', 'zobon_user')
        db_password = os.getenv('POSTGRES_PASSWORD', 'zobon_pass')
        db_host = os.getenv('POSTGRES_HOST', 'localhost')
        db_port = os.getenv('POSTGRES_PORT', '5432')
        db_name = os.getenv('POSTGRES_DB', 'zobon_db')
        postgres_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        print(f"🔌 Connecting to database: {db_host}:{db_port}/{db_name}")
        db = SQLDatabase.from_uri(postgres_url)
        db.run("SELECT 1")
        print("✅ Database connection established and tested")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def initialize_embeddings():
    global vectorstore
    try:
        print("🔄 Initializing embeddings...")
        embedding_model = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': False}
        )
        schema_docs = [
            Document(
                page_content="""Table: brand_performance
Columns: id, brand, date, avg_trust_score, total_mentions,
         positive_sentiment_pct, negative_sentiment_pct, bias_violations, updated_at
Description: Daily performance metrics for each brand across sentiment, trust, and bias dimensions""",
                metadata={"type": "schema", "table": "brand_performance"}
            ),
            Document(
                page_content="""Table: bias_alerts
Columns: id, brand, bias_type, trust_score, text_sample, alert_level, timestamp, resolved, created_at
Description: Individual bias violation alerts for brands with details about the type of bias and severity""",
                metadata={"type": "schema", "table": "bias_alerts"}
            )
        ]
        vectorstore = FAISS.from_documents(schema_docs, embedding_model)
        print("✅ Vector store created successfully")
        return True
    except Exception as e:
        print(f"❌ Embeddings initialization failed: {e}")
        traceback.print_exc()
        return False

def initialize_gemini():
    global gemini_model
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY not found in environment variables")
            return False
        genai.configure(api_key=api_key)
        gemini_model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
                max_output_tokens=500,
            )
        )
        print("✅ Gemini model initialized")
        return True
    except Exception as e:
        print(f"❌ Gemini initialization failed: {e}")
        return False

def initialize_sql_agent():
    global sql_agent
    try:
        print("🔄 Initializing SQL Agent...")
        
        # Fixed LLM configuration for SQL Agent
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0.0,
            max_output_tokens=1000,
            streaming=False
        )
        
        print("✅ LLM initialized for SQL Agent")
        
        # Create SQL agent with fixed parameters - removed unsupported parameters
        sql_agent = create_sql_agent(
            llm=llm,
            db=db,
            agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            max_iterations=5,  # Reduced for stability
            max_execution_time=30,  # Reduced timeout
            return_intermediate_steps=True,
            handle_parsing_errors=True
            # Removed early_stopping_method - not supported in current version
        )
        
        print("✅ SQL Agent created successfully")
        
        # Test the agent with a simple query
        try:
            test_result = sql_agent.invoke({"input": "List the available tables in the database"})
            print(f"✅ SQL Agent test successful")
        except Exception as test_error:
            print(f"⚠️ SQL Agent test failed but agent is still usable: {test_error}")
        
        print("✅ SQL Agent initialized")
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize SQL Agent: {e}")
        traceback.print_exc()
        return False

def clean_assistant_response(response):
    if not response:
        return ""
    return re.sub(r'[^\x00-\x7F]+', ' ', response).strip()

def extract_data_from_sql_output(sql_output):
    """Extract meaningful data from SQL agent output"""
    if isinstance(sql_output, dict):
        sql_output = sql_output.get("output", "")
    
    # Convert to string if it's not already
    if not isinstance(sql_output, str):
        sql_output = str(sql_output)
    
    lines = sql_output.strip().split('\n')
    data_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        low = line.lower()
        # Skip agent thinking/action lines
        if any(x in low for x in [
            'thought:', 'action:', 'action input:', 'observation:', 
            'final answer:', 'i need to', 'let me', 'i should'
        ]):
            continue
        
        # Skip error lines
        if any(x in low for x in ['error', 'failed', 'syntax error']):
            continue
        
        # Keep data lines
        if line and (
            line.startswith('(') or 
            line.startswith('[') or
            any(char.isdigit() for char in line) or
            'tata' in low or 'ola' in low or 'mahindra' in low or 'ather' in low
        ):
            data_lines.append(line)
    
    return '\n'.join(data_lines)

def execute_sql_query_directly(question):
    """Enhanced fallback method to execute SQL queries directly"""
    try:
        question_lower = question.lower()
        
        # Bias violations queries
        if ("bias violations" in question_lower or "bias violation" in question_lower) and "last 7 days" in question_lower:
            if "most" in question_lower or "highest" in question_lower:
                query = """
                SELECT brand, COUNT(*) as violation_count
                FROM bias_alerts
                WHERE timestamp >= NOW() - INTERVAL '7 days'
                GROUP BY brand
                ORDER BY violation_count DESC
                LIMIT 5;
                """
            else:
                query = """
                SELECT brand, COUNT(*) as violation_count
                FROM bias_alerts
                WHERE timestamp >= NOW() - INTERVAL '7 days'
                GROUP BY brand
                ORDER BY violation_count DESC;
                """
        
        # Brand performance queries
        elif "brand performance" in question_lower:
            query = """
            SELECT brand, AVG(avg_trust_score) as avg_trust, 
                   AVG(positive_sentiment_pct) as avg_positive_sentiment,
                   SUM(bias_violations) as total_bias_violations
            FROM brand_performance 
            WHERE date >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY brand
            ORDER BY avg_trust DESC
            LIMIT 10;
            """
        
        # Recent alerts query
        elif "recent" in question_lower and ("alert" in question_lower or "bias" in question_lower):
            query = """
            SELECT brand, bias_type, alert_level, timestamp
            FROM bias_alerts
            WHERE timestamp >= NOW() - INTERVAL '7 days'
            ORDER BY timestamp DESC
            LIMIT 10;
            """
        
        # Trust score queries
        elif "trust score" in question_lower:
            query = """
            SELECT brand, AVG(avg_trust_score) as avg_trust_score,
                   COUNT(*) as data_points
            FROM brand_performance 
            WHERE date >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY brand
            ORDER BY avg_trust_score DESC
            LIMIT 10;
            """
        
        # Sentiment analysis queries
        elif "sentiment" in question_lower:
            query = """
            SELECT brand, 
                   AVG(positive_sentiment_pct) as avg_positive,
                   AVG(negative_sentiment_pct) as avg_negative,
                   AVG(total_mentions) as avg_mentions
            FROM brand_performance 
            WHERE date >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY brand
            ORDER BY avg_positive DESC
            LIMIT 10;
            """
        
        # Generic recent data query
        else:
            query = """
            SELECT brand, date, avg_trust_score, total_mentions, 
                   positive_sentiment_pct, negative_sentiment_pct, bias_violations
            FROM brand_performance 
            WHERE date >= CURRENT_DATE - INTERVAL '7 days'
            ORDER BY date DESC, bias_violations DESC
            LIMIT 15;
            """
        
        print(f"🔍 Executing direct SQL: {query}")
        result = db.run(query)
        print(f"🔍 Direct SQL result: {result}")
        return result
        
    except Exception as e:
        print(f"❌ Direct SQL execution failed: {e}")
        traceback.print_exc()
        return None

# Initialize all components
if not initialize_database(): 
    print("❌ Database initialization failed - exiting")
    exit(1)
if not initialize_embeddings(): 
    print("❌ Embeddings initialization failed - exiting")
    exit(1)
if not initialize_gemini(): 
    print("❌ Gemini initialization failed - exiting")
    exit(1)
if not initialize_sql_agent(): 
    print("❌ SQL Agent initialization failed - exiting")
    exit(1)

@app.route('/api/ask', methods=['POST'])
def sql_assistant_query():
    try:
        data = request.get_json()
        user_question = data.get("question", "").strip()
        
        if not user_question:
            return jsonify({"error": "Question cannot be empty"}), 400

        print(f"🔍 Processing question: {user_question}")
        
        # Try SQL Agent first
        sql_agent_output = None
        agent_success = False
        
        try:
            print(f"🔍 Running SQL Agent for question: {user_question}")
            sql_agent_result = sql_agent.invoke({"input": user_question})
            print("🔍 Raw SQL Agent Output:")
            print(sql_agent_result)
            
            if isinstance(sql_agent_result, dict):
                sql_agent_output = sql_agent_result.get("output", "")
            else:
                sql_agent_output = str(sql_agent_result)
            
            # Check if agent provided a meaningful response
            if (sql_agent_output and 
                len(sql_agent_output.strip()) > 20 and
                not any(x in sql_agent_output.lower() for x in [
                    "iteration limit", "time limit", "i don't know", 
                    "cannot", "unable", "syntax error"
                ])):
                agent_success = True
                print("✅ SQL Agent provided valid response")
            else:
                print("🔄 SQL Agent response insufficient, falling back...")
                
        except Exception as agent_error:
            print(f"❌ SQL Agent failed: {agent_error}")
            print("🔄 Falling back to direct SQL execution...")
        
        # Fallback to direct SQL execution if agent failed
        if not agent_success:
            direct_result = execute_sql_query_directly(user_question)
            if direct_result:
                sql_agent_output = f"Query Results:\n{direct_result}"
            else:
                return jsonify({"error": "Both SQL Agent and direct execution failed"}), 500

        if not sql_agent_output:
            return jsonify({"answer": "Sorry, I couldn't get a valid result from the database for your question."})

        # Extract and clean the data
        clean_data = extract_data_from_sql_output(sql_agent_output)
        print("🔍 Cleaned Data for Gemini:")
        print(clean_data)

        # Validate extracted data
        if (not clean_data or 
            len(clean_data.strip()) == 0 or 
            "no data" in clean_data.lower() or 
            "error" in clean_data.lower()):
            
            # Try to extract useful data from raw output
            if "Query Results:" in sql_agent_output:
                raw_data = sql_agent_output.split("Query Results:")[-1].strip()
                if raw_data and len(raw_data) > 10:
                    clean_data = raw_data
                else:
                    return jsonify({"answer": "Sorry, I don't have the required data in my database to answer your question."})
            else:
                return jsonify({"answer": "Sorry, I don't have the required data in my database to answer your question."})

        # Enhanced prompt for Gemini
        prompt = f"""You are ZOBON, a professional data analytics assistant. Analyze the database results and provide a clear, insightful answer.

INSTRUCTIONS:
1. Use ONLY the database results provided below
2. Provide specific numbers, brand names, and values from the data
3. Format your response clearly with proper structure
4. If the question asks for "most" or "highest", identify the top result
5. Be professional and concise
6. If the data doesn't fully answer the question, state what information is available

DATABASE RESULTS:
{clean_data}

USER QUESTION: {user_question}

PROFESSIONAL ANALYSIS:"""

        try:
            response = gemini_model.generate_content(prompt)
            assistant_text = response.text if response and response.text else ""
            cleaned_response = clean_assistant_response(assistant_text)
            
            if len(cleaned_response) < 10:
                return jsonify({"answer": "The data does not contain sufficient information to answer this question."})
            
            return jsonify({"answer": cleaned_response})
            
        except ResourceExhausted:
            return jsonify({"error": "API quota exceeded, please try again later."}), 429
            
        except Exception as gemini_error:
            print(f"❌ Gemini API call failed: {gemini_error}")
            traceback.print_exc()
            
            # Return formatted raw data if Gemini fails
            formatted_data = clean_data.replace('\n', '\n\n')
            return jsonify({
                "answer": f"Here's the data from the database:\n\n{formatted_data}",
                "note": "AI processing unavailable, showing raw database results"
            })

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "database": "connected" if db else "disconnected",
        "vectorstore": "initialized" if vectorstore else "not initialized",
        "gemini": "initialized" if gemini_model else "not initialized",
        "sql_agent": "initialized" if sql_agent else "not initialized"
    })

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Test endpoint to verify database connectivity"""
    try:
        # Test database connection
        db_result = db.run("SELECT COUNT(*) FROM brand_performance;")
        bias_result = db.run("SELECT COUNT(*) FROM bias_alerts;")
        
        return jsonify({
            "status": "success",
            "message": "Database test successful",
            "brand_performance_count": db_result,
            "bias_alerts_count": bias_result
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Database test failed: {str(e)}"
        }), 500

@app.route('/api/test-agent', methods=['GET'])
def test_agent():
    """Test endpoint to verify SQL Agent functionality"""
    try:
        test_question = "How many brands are in the database?"
        result = sql_agent.invoke({"input": test_question})
        
        return jsonify({
            "status": "success",
            "message": "SQL Agent test successful",
            "test_question": test_question,
            "result": result
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"SQL Agent test failed: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(host="127.0.0.1", port=5002, debug=True)