from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import google.generativeai as genai
import sqlite3
import requests
import io
import base64
from datetime import datetime
app = Flask(__name__)
CORS(app) # Enable CORS for React frontend
class PlantDiseaseAPI:
    def __init__(self):
        # Configure Gemini API
        genai.configure(api_key="")
        self.model = genai.GenerativeModel('gemini-2.5-flash')
       
        # Weather API Configuration
        self.WEATHER_API_KEY = "fa873d009082422188934434250712"
        self.WEATHER_BASE_URL = "http://api.weatherapi.com/v1"
       
        # Database paths
        self.plant_db_path = "plant_disease.db"
        self.plant_table = "plant_data"
        self.solution_db_path = "solution.db"
        self.solution_table = "pesticide_solutions"
       
        # Weather-based disease prediction rules
        self.DISEASE_PREDICTION_RULES = {
            "Rice": {
                "Blast": {
                    "conditions": "High humidity (>80%) + Temperature 25-30°C",
                    "trigger": lambda t, h, r: 25 <= t <= 30 and h > 80 and r > 5,
                    "prevention": "Apply Tricyclazole fungicide, Avoid excessive nitrogen, Ensure proper drainage"
                },
                "Bacterial Leaf Blight": {
                    "conditions": "Temperature 25-34°C + High humidity (>70%) + Rainfall",
                    "trigger": lambda t, h, r: 25 <= t <= 34 and h > 70 and r > 10,
                    "prevention": "Use copper-based bactericides, Remove infected plants"
                },
                "Sheath Blight": {
                    "conditions": "High temperature (>30°C) + High humidity (>85%)",
                    "trigger": lambda t, h, r: t > 30 and h > 85,
                    "prevention": "Apply Validamycin, Maintain proper spacing"
                }
            },
            "Wheat": {
                "Rust": {
                    "conditions": "Temperature 15-25°C + High humidity (>70%)",
                    "trigger": lambda t, h, r: 15 <= t <= 25 and h > 70,
                    "prevention": "Spray Propiconazole, Use resistant varieties"
                },
                "Powdery Mildew": {
                    "conditions": "Cool temperature (15-22°C) + Moderate humidity",
                    "trigger": lambda t, h, r: 15 <= t <= 22 and 50 <= h <= 70,
                    "prevention": "Apply Sulfur or Triadimefon"
                }
            },
            "Tomato": {
                "Late Blight": {
                    "conditions": "Cool temperature (15-25°C) + High humidity (>90%) + Rain",
                    "trigger": lambda t, h, r: 15 <= t <= 25 and h > 90 and r > 2,
                    "prevention": "Apply Metalaxyl + Mancozeb, Remove infected plants"
                },
                "Early Blight": {
                    "conditions": "Temperature 25-30°C + High humidity (>80%)",
                    "trigger": lambda t, h, r: 25 <= t <= 30 and h > 80 and r > 1,
                    "prevention": "Spray Chlorothalonil or Mancozeb"
                }
            },
            "Potato": {
                "Late Blight": {
                    "conditions": "Temperature 15-25°C + High humidity (>90%) + Rainfall",
                    "trigger": lambda t, h, r: 15 <= t <= 25 and h > 90 and r > 5,
                    "prevention": "Apply Metalaxyl + Mancozeb immediately"
                }
            },
            "Cotton": {
                "Wilt": {
                    "conditions": "High temperature (>30°C) + Moderate rainfall",
                    "trigger": lambda t, h, r: t > 30 and r > 5,
                    "prevention": "Use Carbendazim as soil drench, Practice crop rotation"
                },
                "Boll Rot": {
                    "conditions": "High rainfall + High humidity (>85%)",
                    "trigger": lambda t, h, r: 25 <= t <= 30 and h > 85 and r > 15,
                    "prevention": "Improve drainage, Apply Carbendazim + Mancozeb"
                }
            },
            "Sugarcane": {
                "Red Rot": {
                    "conditions": "High temperature (>30°C) + High humidity (>80%)",
                    "trigger": lambda t, h, r: t > 30 and h > 80 and r > 10,
                    "prevention": "Use disease-free setts, Apply Carbendazim"
                }
            },
            "Maize": {
                "Blight": {
                    "conditions": "Temperature 20-28°C + High humidity (>80%)",
                    "trigger": lambda t, h, r: 20 <= t <= 28 and h > 80 and r > 3,
                    "prevention": "Apply Mancozeb, Use resistant hybrids"
                }
            }
        }
   
    def identify_plant(self, input_data, input_type='image'):
        """Use Gemini AI to identify the plant name, disease, and confidence from image, text, or audio"""
        try:
            plant_info = {}
            if input_type == 'image':
                # Decode base64 image
                image_bytes = base64.b64decode(input_data.split(',')[1] if ',' in input_data else input_data)
                image = Image.open(io.BytesIO(image_bytes))
               
                prompt = """You are an expert Botanist. Analyze this plant image and provide ONLY:
1. Plant common name (single word if possible, e.g., "Apple", "Tomato", "Rice")
2. Disease visible (if any)
3. Confidence (0-100)
Respond in this EXACT format (3 lines only):
PLANT: [Plant Name]
DISEASE: [Disease Name or "Healthy"]
CONFIDENCE: [Number 0-100]
Be brief and use simple common names."""
                response = self.model.generate_content([prompt, image])
            elif input_type == 'text':
                prompt = """You are an expert Botanist. Analyze this plant description and provide ONLY:
1. Plant common name (single word if possible, e.g., "Apple", "Tomato", "Rice")
2. Disease visible (if any)
3. Confidence (0-100)
Respond in this EXACT format (3 lines only):
PLANT: [Plant Name]
DISEASE: [Disease Name or "Healthy"]
CONFIDENCE: [Number 0-100]
Be brief and use simple common names.
Description: """
                response = self.model.generate_content(prompt + input_data)
            elif input_type == 'audio':
                # Decode base64 audio
                audio_bytes = base64.b64decode(input_data.split(',')[1] if ',' in input_data else input_data)
                audio_file = genai.upload_file(path=io.BytesIO(audio_bytes), mime_type="audio/webm")
               
                prompt = """Transcribe and analyze this voice description of a plant. Provide ONLY:
1. Plant common name (single word if possible, e.g., "Apple", "Tomato", "Rice")
2. Disease visible (if any)
3. Confidence (0-100)
Respond in this EXACT format (3 lines only):
PLANT: [Plant Name]
DISEASE: [Disease Name or "Healthy"]
CONFIDENCE: [Number 0-100]
Be brief and use simple common names."""
                response = self.model.generate_content([prompt, audio_file])
            else:
                return None

            result = response.text.strip()
           
            for line in result.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    plant_info[key.strip().upper()] = value.strip()
           
            return plant_info
           
        except Exception as e:
            print(f"Gemini API error: {e}")
            return None
   
    def search_plant_database(self, plant_name, disease):
        """Search plant disease database for detailed information"""
        try:
            conn = sqlite3.connect(self.plant_db_path)
            cursor = conn.cursor()
           
            cursor.execute(f"PRAGMA table_info({self.plant_table})")
            columns = [col[1] for col in cursor.fetchall()]
           
            cursor.execute(
                f"SELECT * FROM {self.plant_table} WHERE plant_name LIKE ? LIMIT 1",
                (f"%{plant_name}%",)
            )
            row = cursor.fetchone()
           
            if row:
                match = dict(zip(columns, row))
                conn.close()
                return match, True
           
            if disease and disease.lower() != "healthy":
                cursor.execute(
                    f"SELECT * FROM {self.plant_table} WHERE disease_name LIKE ? LIMIT 1",
                    (f"%{disease}%",)
                )
                row = cursor.fetchone()
               
                if row:
                    match = dict(zip(columns, row))
                    conn.close()
                    return match, True
           
            conn.close()
            return None, False
           
        except Exception as e:
            print(f"Plant database query error: {e}")
            return None, False
   
    def search_pesticide_solution(self, plant_name, disease):
        """Search pesticide solution database for treatment recommendations"""
        try:
            conn = sqlite3.connect(self.solution_db_path)
            cursor = conn.cursor()
           
            cursor.execute(f"PRAGMA table_info({self.solution_table})")
            columns = [col[1] for col in cursor.fetchall()]
           
            cursor.execute(
                f"SELECT * FROM {self.solution_table} WHERE Plant LIKE ? AND Disease LIKE ? LIMIT 1",
                (f"%{plant_name}%", f"%{disease}%")
            )
            row = cursor.fetchone()
           
            if row:
                match = dict(zip(columns, row))
                conn.close()
                return match, True
           
            cursor.execute(
                f"SELECT * FROM {self.solution_table} WHERE Plant LIKE ? LIMIT 1",
                (f"%{plant_name}%",)
            )
            row = cursor.fetchone()
           
            if row:
                match = dict(zip(columns, row))
                conn.close()
                return match, True
           
            if disease and disease.lower() != "healthy":
                cursor.execute(
                    f"SELECT * FROM {self.solution_table} WHERE Disease LIKE ? LIMIT 1",
                    (f"%{disease}%",)
                )
                row = cursor.fetchone()
               
                if row:
                    match = dict(zip(columns, row))
                    conn.close()
                    return match, True
           
            conn.close()
            return None, False
           
        except Exception as e:
            print(f"Pesticide solution database query error: {e}")
            return None, False
   
    def get_weather_data(self, location):
        """Fetch weather data from WeatherAPI"""
        try:
            endpoint = f"{self.WEATHER_BASE_URL}/forecast.json"
            params = {
                "key": self.WEATHER_API_KEY,
                "q": location,
                "days": 3,
                "aqi": "no",
                "alerts": "yes"
            }
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Weather API error: {e}")
            return None
   
    def predict_weather_diseases(self, plant_name, temp_c, humidity, rainfall_mm):
        """Predict diseases based on weather conditions"""
        if plant_name not in self.DISEASE_PREDICTION_RULES:
            return []
       
        predictions = []
        crop_diseases = self.DISEASE_PREDICTION_RULES[plant_name]
       
        for disease, info in crop_diseases.items():
            if info["trigger"](temp_c, humidity, rainfall_mm):
                predictions.append({
                    "disease": disease,
                    "risk": "HIGH",
                    "conditions": info["conditions"],
                    "prevention": info["prevention"]
                })
       
        return predictions
   
    def get_disease_risk_level(self, temp, humidity, rainfall):
        """Calculate overall disease risk level"""
        risk_score = 0
       
        if humidity > 85:
            risk_score += 3
        elif humidity > 70:
            risk_score += 2
        elif humidity > 60:
            risk_score += 1
       
        if rainfall > 15:
            risk_score += 3
        elif rainfall > 5:
            risk_score += 2
        elif rainfall > 1:
            risk_score += 1
       
        if temp > 35 or temp < 10:
            risk_score += 2
       
        if risk_score >= 5:
            return "CRITICAL", "🔴"
        elif risk_score >= 3:
            return "HIGH", "🟠"
        elif risk_score >= 1:
            return "MODERATE", "🟡"
        else:
            return "LOW", "🟢"
   
    def process_chatbot_query(self, query, plant_info):
        """Process user query using Gemini AI"""
        try:
            context = f"""You are a plant disease expert chatbot. The user is asking about:
Plant: {plant_info.get('plant_name', 'Unknown')}
Disease: {plant_info.get('disease', 'Unknown')}
User question: {query}
Provide a helpful, concise answer (2-3 sentences) about this specific plant and disease."""
            response = self.model.generate_content(context)
            answer = response.text.strip()
            return answer
           
        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}"
# Initialize API instance
api = PlantDiseaseAPI()
# ==================== API ENDPOINTS ====================
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "Plant Disease API is running"})
@app.route('/api/analyze', methods=['POST'])
def analyze_plant():
    """
    Analyze plant input (image, audio, or text)
    Request body: {
        "image": "base64_encoded_image",  // or "audio": "base64_encoded_audio", or "text": "description"
        "treatment_type": "chemical" | "organic"
    }
    """
    try:
        data = request.json
        treatment_type = data.get('treatment_type', 'chemical')
        input_type = None
        input_data = None

        if 'image' in data:
            input_type = 'image'
            input_data = data['image']
        elif 'audio' in data:
            input_type = 'audio'
            input_data = data['audio']
        elif 'text' in data:
            input_type = 'text'
            input_data = data['text']
        else:
            return jsonify({"error": "No input data provided (image, audio, or text)"}), 400
       
        # Step 1: Identify with Gemini
        plant_info = api.identify_plant(input_data, input_type)
        if not plant_info:
            return jsonify({"error": "Failed to identify plant"}), 500
       
        plant_name = plant_info.get('PLANT', 'Unknown')
        disease = plant_info.get('DISEASE', 'Unknown')
        confidence = int(plant_info.get('CONFIDENCE', 0))
       
        # Step 2: Search plant database
        plant_match, plant_found = api.search_plant_database(plant_name, disease)
       
        # Step 3: Search pesticide solution database
        pesticide_match, pesticide_found = api.search_pesticide_solution(plant_name, disease)
       
        # Format response
        response = {
            "plant_name": plant_name,
            "disease": disease,
            "confidence": confidence,
            "treatment_type": treatment_type,
            "plant_database_match": plant_found,
            "pesticide_database_match": pesticide_found,
            "plant_data": plant_match,
            "pesticide_data": pesticide_match,
            "analysis_complete": True
        }
       
        return jsonify(response)
       
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/api/weather', methods=['POST'])
def get_weather_advisory():
    """
    Get weather-based disease advisory
    Request body: {
        "location": "city_name",
        "plant_name": "plant_name"
    }
    """
    try:
        data = request.json
        location = data.get('location', 'Bangalore')
        plant_name = data.get('plant_name', 'Unknown')
       
        # Fetch weather data
        weather_data = api.get_weather_data(location)
        if not weather_data:
            return jsonify({"error": f"Could not fetch weather data for '{location}'"}), 404
       
        location_info = weather_data['location']
        current = weather_data['current']
        forecast = weather_data['forecast']['forecastday']
       
        # Current conditions
        temp = current['temp_c']
        humidity = current['humidity']
        rainfall = current.get('precip_mm', 0)
       
        # Current risk assessment
        risk_level, risk_icon = api.get_disease_risk_level(temp, humidity, rainfall)
       
        # Current disease predictions
        current_predictions = api.predict_weather_diseases(plant_name, temp, humidity, rainfall)
       
        # Process 3-day forecast
        forecast_data = []
        spray_days = []
       
        for idx, day in enumerate(forecast):
            day_data = day['day']
            avg_temp = day_data['avgtemp_c']
            avg_humidity = day_data['avghumidity']
            total_rain = day_data['totalprecip_mm']
           
            day_risk_level, day_risk_icon = api.get_disease_risk_level(avg_temp, avg_humidity, total_rain)
            day_predictions = api.predict_weather_diseases(plant_name, avg_temp, avg_humidity, total_rain)
           
            forecast_item = {
                "date": day['date'],
                "day_number": idx + 1,
                "max_temp": day_data['maxtemp_c'],
                "min_temp": day_data['mintemp_c'],
                "avg_temp": avg_temp,
                "condition": day_data['condition']['text'],
                "rainfall": total_rain,
                "rain_chance": day_data['daily_chance_of_rain'],
                "humidity": avg_humidity,
                "risk_level": day_risk_level,
                "risk_icon": day_risk_icon,
                "predictions": day_predictions,
                "good_for_spraying": total_rain < 2 and avg_humidity < 80
            }
           
            forecast_data.append(forecast_item)
           
            if forecast_item["good_for_spraying"]:
                spray_days.append(f"{day['date']} (Day {idx+1})")
       
        # Farming recommendations
        recommendations = []
        if rainfall > 10:
            recommendations.append({
                "type": "warning",
                "title": "HEAVY RAINFALL ALERT",
                "items": [
                    "Postpone pesticide/fungicide spraying",
                    "Ensure proper field drainage",
                    "Monitor for waterlogging"
                ]
            })
        elif rainfall < 1 and humidity < 50:
            recommendations.append({
                "type": "info",
                "title": "LOW MOISTURE CONDITIONS",
                "items": [
                    "Schedule irrigation for crops",
                    "Check soil moisture regularly"
                ]
            })
       
        if humidity > 85:
            recommendations.append({
                "type": "warning",
                "title": "HIGH HUMIDITY WARNING",
                "items": [
                    "Increase vigilance for fungal diseases",
                    "Improve air circulation in fields",
                    "Consider preventive fungicide application"
                ]
            })
       
        if current['wind_kph'] > 30:
            recommendations.append({
                "type": "warning",
                "title": "STRONG WIND ALERT",
                "items": [
                    "Postpone pesticide spraying",
                    "Provide support to tall crops"
                ]
            })
       
        response = {
            "location": {
                "name": location_info['name'],
                "region": location_info['region'],
                "localtime": location_info['localtime']
            },
            "current_weather": {
                "temperature": temp,
                "feels_like": current['feelslike_c'],
                "humidity": humidity,
                "rainfall": rainfall,
                "condition": current['condition']['text'],
                "wind_kph": current['wind_kph'],
                "wind_dir": current['wind_dir'],
                "uv_index": current['uv'],
                "risk_level": risk_level,
                "risk_icon": risk_icon
            },
            "current_predictions": current_predictions,
            "forecast": forecast_data,
            "spray_days": spray_days,
            "recommendations": recommendations
        }
       
        return jsonify(response)
       
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/api/chatbot', methods=['POST'])
def chatbot():
    """
    Chatbot endpoint for user queries
    Request body: {
        "query": "user_question",
        "plant_info": {
            "plant_name": "name",
            "disease": "disease"
        }
    }
    """
    try:
        data = request.json
        query = data.get('query')
        plant_info = data.get('plant_info', {})
       
        if not query:
            return jsonify({"error": "No query provided"}), 400
       
        answer = api.process_chatbot_query(query, plant_info)
       
        return jsonify({"answer": answer})
       
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/api/databases/status', methods=['GET'])
def check_databases():
    """Check database status"""
    try:
        status = {}
       
        # Check plant database
        try:
            conn = sqlite3.connect(api.plant_db_path)
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {api.plant_table}")
            plant_count = cursor.fetchone()[0]
            conn.close()
            status['plant_database'] = {
                "status": "connected",
                "records": plant_count
            }
        except Exception as e:
            status['plant_database'] = {
                "status": "error",
                "message": str(e)
            }
       
        # Check solution database
        try:
            conn = sqlite3.connect(api.solution_db_path)
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {api.solution_table}")
            solution_count = cursor.fetchone()[0]
            conn.close()
            status['solution_database'] = {
                "status": "connected",
                "records": solution_count
            }
        except Exception as e:
            status['solution_database'] = {
                "status": "error",
                "message": str(e)
            }
       
        return jsonify(status)
       
    except Exception as e:
        return jsonify({"error": str(e)}), 500
if __name__ == '__main__':

    app.run(debug=True, host='0.0.0.0', port=5000)
