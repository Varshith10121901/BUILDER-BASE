import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk  
import google.generativeai as genai
import sqlite3
import webbrowser
import threading
import speech_recognition as sr
import requests
from datetime import datetime

class PlantDeficiencyAnalyzer:
    def __init__(self, root):
        self.root = root
        self.root.title("Plant Disease Detection")
        self.root.state('zoomed')
        self.root.configure(bg="#000000")
        
        # Configure Gemini API
        genai.configure(api_key="")
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Weather API Configuration
        self.WEATHER_API_KEY = "fa873d009082422188934434250712"
        self.WEATHER_BASE_URL = "http://api.weatherapi.com/v1"
        
        # Initialize speech recognizer
        self.recognizer = sr.Recognizer()
        
        # Indian language codes for speech recognition
        self.indian_languages = {
            'Hindi': 'hi-IN',
            'Tamil': 'ta-IN',
            'Telugu': 'te-IN',
            'Kannada': 'kn-IN',
            'Malayalam': 'ml-IN',
            'Bengali': 'bn-IN',
            'Marathi': 'mr-IN',
            'Gujarati': 'gu-IN',
            'Punjabi': 'pa-IN',
            'English': 'en-IN'
        }
        
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
        
        self.check_databases()
        
        self.selected_image_path = None
        self.display_image = None
        self.treatment_type = None
        self.current_plant_info = {}
        self.current_location = "Bangalore"  # Default location
        
        self.create_widgets()
    
    def check_databases(self):
        """Check if both databases exist and are accessible"""
        try:
            conn = sqlite3.connect(self.plant_db_path)
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {self.plant_table}")
            plant_count = cursor.fetchone()[0]
            conn.close()
            print(f"✓ Plant Disease Database loaded: {plant_count} records")
        except Exception as e:
            print(f"⚠️ Plant Disease Database: {str(e)}")
        
        try:
            conn = sqlite3.connect(self.solution_db_path)
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {self.solution_table}")
            solution_count = cursor.fetchone()[0]
            conn.close()
            print(f"✓ Pesticide Solution Database loaded: {solution_count} records")
        except Exception as e:
            print(f"⚠️ Pesticide Solution Database: {str(e)}")
    
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
    
    def open_weather_advisory_window(self):
        """Open weather-based disease advisory window"""
        if not self.current_plant_info or 'plant_name' not in self.current_plant_info:
            messagebox.showwarning("Warning", "Please analyze a plant image first!")
            return
        
        # Create weather advisory window
        weather_window = tk.Toplevel(self.root)
        weather_window.title("Weather-Based Disease Advisory")
        weather_window.geometry("900x800")
        weather_window.configure(bg="#000000")
        
        # Title
        title_label = tk.Label(
            weather_window,
            text="🌤️ Weather-Based Disease Prediction",
            font=("Arial Black", 20, "bold"),
            bg="#000000",
            fg="#00ff00"
        )
        title_label.pack(pady=15)
        
        # Location input frame
        location_frame = tk.Frame(weather_window, bg="#001a00", bd=2, relief=tk.RIDGE)
        location_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        tk.Label(
            location_frame,
            text="Enter Location (City):",
            font=("Arial", 13, "bold"),
            bg="#001a00",
            fg="#00ff00"
        ).pack(side=tk.LEFT, padx=15, pady=15)
        
        location_entry = tk.Entry(
            location_frame,
            font=("Arial", 12),
            bg="#003300",
            fg="#00ff00",
            insertbackground="#00ff00",
            width=25
        )
        location_entry.insert(0, self.current_location)
        location_entry.pack(side=tk.LEFT, padx=10, pady=15)
        
        # Display area
        display_frame = tk.Frame(weather_window, bg="#001a00", bd=2, relief=tk.RIDGE)
        display_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))
        
        display_text = scrolledtext.ScrolledText(
            display_frame,
            font=("Segoe UI", 11),
            bg="#001a00",
            fg="#00ff00",
            wrap=tk.WORD,
            padx=20,
            pady=20
        )
        display_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configure tags
        display_text.tag_configure("heading", font=("Arial Black", 14, "bold"), foreground="#00ff00")
        display_text.tag_configure("subheading", font=("Arial", 12, "bold"), foreground="#00ffff")
        display_text.tag_configure("warning", font=("Arial", 11, "bold"), foreground="#ff9900")
        display_text.tag_configure("risk_high", font=("Arial", 11, "bold"), foreground="#ff0000")
        display_text.tag_configure("risk_moderate", font=("Arial", 11, "bold"), foreground="#ffff00")
        display_text.tag_configure("risk_low", font=("Arial", 11, "bold"), foreground="#00ff00")
        display_text.tag_configure("normal", font=("Segoe UI", 11), foreground="#ccffcc")
        
        def fetch_and_display_weather():
            location = location_entry.get().strip()
            if not location:
                messagebox.showwarning("Warning", "Please enter a location!")
                return
            
            self.current_location = location
            plant_name = self.current_plant_info.get('plant_name', 'Unknown')
            
            display_text.delete(1.0, tk.END)
            display_text.insert(tk.END, "🔄 Fetching weather data...\n\n", "heading")
            fetch_btn.config(state=tk.DISABLED)
            
            def fetch_in_thread():
                weather_data = self.get_weather_data(location)
                
                if weather_data:
                    self.root.after(0, lambda: self.display_weather_advisory(
                        display_text, weather_data, plant_name))
                else:
                    display_text.delete(1.0, tk.END)
                    display_text.insert(tk.END, 
                        f"❌ Could not fetch weather data for '{location}'.\n"
                        "Please check the location name and try again.", "warning")
                
                self.root.after(0, lambda: fetch_btn.config(state=tk.NORMAL))
            
            threading.Thread(target=fetch_in_thread, daemon=True).start()
        
        # Fetch button
        fetch_btn = tk.Button(
            location_frame,
            text="🔍 Get Weather Advisory",
            font=("Arial", 11, "bold"),
            bg="#00ff00",
            fg="#000000",
            cursor="hand2",
            command=fetch_and_display_weather
        )
        fetch_btn.pack(side=tk.LEFT, padx=10, pady=15)
        
        # Auto-fetch on open
        fetch_and_display_weather()
    
    def display_weather_advisory(self, text_widget, weather_data, plant_name):
        """Display comprehensive weather-based disease advisory"""
        text_widget.delete(1.0, tk.END)
        
        location_info = weather_data['location']
        current = weather_data['current']
        forecast = weather_data['forecast']['forecastday']
        
        # Header
        text_widget.insert(tk.END, f"📍 {location_info['name']}, {location_info['region']}\n", "heading")
        text_widget.insert(tk.END, f"🌾 Crop: {plant_name}\n", "subheading")
        text_widget.insert(tk.END, f"🕒 {location_info['localtime']}\n\n", "normal")
        
        text_widget.insert(tk.END, "="*80 + "\n", "normal")
        text_widget.insert(tk.END, "CURRENT WEATHER CONDITIONS\n", "heading")
        text_widget.insert(tk.END, "="*80 + "\n\n", "normal")
        
        temp = current['temp_c']
        humidity = current['humidity']
        rainfall = current.get('precip_mm', 0)
        
        text_widget.insert(tk.END, f"🌡️  Temperature: {temp}°C (Feels like: {current['feelslike_c']}°C)\n", "normal")
        text_widget.insert(tk.END, f"💧 Humidity: {humidity}%\n", "normal")
        text_widget.insert(tk.END, f"🌧️  Rainfall: {rainfall} mm\n", "normal")
        text_widget.insert(tk.END, f"☁️  Condition: {current['condition']['text']}\n", "normal")
        text_widget.insert(tk.END, f"💨 Wind: {current['wind_kph']} kph, {current['wind_dir']}\n", "normal")
        text_widget.insert(tk.END, f"☀️  UV Index: {current['uv']}\n\n", "normal")
        
        # Current risk assessment
        risk_level, risk_icon = self.get_disease_risk_level(temp, humidity, rainfall)
        risk_tag = f"risk_{risk_level.lower()}"
        
        text_widget.insert(tk.END, f"{risk_icon} OVERALL DISEASE RISK: {risk_level}\n\n", risk_tag)
        
        # Current disease predictions
        current_predictions = self.predict_weather_diseases(plant_name, temp, humidity, rainfall)
        
        if current_predictions:
            text_widget.insert(tk.END, "⚠️  DISEASE ALERTS (Current Conditions)\n", "warning")
            text_widget.insert(tk.END, "-" * 80 + "\n\n", "normal")
            for pred in current_predictions:
                text_widget.insert(tk.END, f"🦠 {pred['disease']} - {pred['risk']} RISK\n", "risk_high")
                text_widget.insert(tk.END, f"   Conditions: {pred['conditions']}\n", "normal")
                text_widget.insert(tk.END, f"   Prevention: {pred['prevention']}\n\n", "normal")
        else:
            text_widget.insert(tk.END, "✅ No immediate disease risk detected under current conditions\n\n", "risk_low")
        
        # Farming recommendations
        text_widget.insert(tk.END, "="*80 + "\n", "normal")
        text_widget.insert(tk.END, "FARMING RECOMMENDATIONS\n", "heading")
        text_widget.insert(tk.END, "="*80 + "\n\n", "normal")
        
        if rainfall > 10:
            text_widget.insert(tk.END, "🌧️  HEAVY RAINFALL ALERT:\n", "warning")
            text_widget.insert(tk.END, "   • Postpone pesticide/fungicide spraying\n", "normal")
            text_widget.insert(tk.END, "   • Ensure proper field drainage\n", "normal")
            text_widget.insert(tk.END, "   • Monitor for waterlogging\n\n", "normal")
        elif rainfall < 1 and humidity < 50:
            text_widget.insert(tk.END, "💧 LOW MOISTURE CONDITIONS:\n", "subheading")
            text_widget.insert(tk.END, "   • Schedule irrigation for crops\n", "normal")
            text_widget.insert(tk.END, "   • Check soil moisture regularly\n\n", "normal")
        
        if humidity > 85:
            text_widget.insert(tk.END, "🌫️  HIGH HUMIDITY WARNING:\n", "warning")
            text_widget.insert(tk.END, "   • Increase vigilance for fungal diseases\n", "normal")
            text_widget.insert(tk.END, "   • Improve air circulation in fields\n", "normal")
            text_widget.insert(tk.END, "   • Consider preventive fungicide application\n\n", "normal")
        
        if current['wind_kph'] > 30:
            text_widget.insert(tk.END, "💨 STRONG WIND ALERT:\n", "warning")
            text_widget.insert(tk.END, "   • Postpone pesticide spraying\n", "normal")
            text_widget.insert(tk.END, "   • Provide support to tall crops\n\n", "normal")
        
        # 3-day forecast
        text_widget.insert(tk.END, "\n" + "="*80 + "\n", "normal")
        text_widget.insert(tk.END, "3-DAY WEATHER FORECAST & DISEASE PREDICTION\n", "heading")
        text_widget.insert(tk.END, "="*80 + "\n\n", "normal")
        
        spray_days = []
        
        for idx, day in enumerate(forecast):
            day_data = day['day']
            astro = day['astro']
            
            avg_temp = day_data['avgtemp_c']
            avg_humidity = day_data['avghumidity']
            total_rain = day_data['totalprecip_mm']
            
            risk_level, risk_icon = self.get_disease_risk_level(avg_temp, avg_humidity, total_rain)
            
            text_widget.insert(tk.END, f"📅 Day {idx + 1}: {day['date']} {risk_icon}\n", "subheading")
            text_widget.insert(tk.END, "-" * 80 + "\n", "normal")
            text_widget.insert(tk.END, 
                f"Temperature: Max {day_data['maxtemp_c']}°C, Min {day_data['mintemp_c']}°C, Avg {avg_temp}°C\n", 
                "normal")
            text_widget.insert(tk.END, f"Condition: {day_data['condition']['text']}\n", "normal")
            text_widget.insert(tk.END, 
                f"Rainfall: {total_rain} mm (Chance: {day_data['daily_chance_of_rain']}%)\n", 
                "normal")
            text_widget.insert(tk.END, f"Humidity: {avg_humidity}%\n", "normal")
            text_widget.insert(tk.END, 
                f"Sunrise/Sunset: {astro['sunrise']} / {astro['sunset']}\n", 
                "normal")
            text_widget.insert(tk.END, f"Risk Level: {risk_level} {risk_icon}\n\n", f"risk_{risk_level.lower()}")
            
            # Disease predictions for this day
            day_predictions = self.predict_weather_diseases(plant_name, avg_temp, avg_humidity, total_rain)
            
            if day_predictions:
                text_widget.insert(tk.END, f"⚠️  Predicted Diseases:\n", "warning")
                for pred in day_predictions:
                    text_widget.insert(tk.END, f"   • {pred['disease']} - {pred['risk']} RISK\n", "normal")
            else:
                text_widget.insert(tk.END, "✅ Low disease risk\n", "risk_low")
            
            # Daily recommendations
            if total_rain < 2 and avg_humidity < 80:
                spray_days.append(f"{day['date']} (Day {idx+1})")
                text_widget.insert(tk.END, "   ✓ Good day for pesticide spraying\n", "risk_low")
            elif total_rain > 10:
                text_widget.insert(tk.END, "   ⚠️  Avoid field operations, ensure drainage\n", "warning")
            
            text_widget.insert(tk.END, "\n", "normal")
        
        # Spray recommendations
        if spray_days:
            text_widget.insert(tk.END, "="*80 + "\n", "normal")
            text_widget.insert(tk.END, "BEST DAYS FOR SPRAYING\n", "heading")
            text_widget.insert(tk.END, "="*80 + "\n\n", "normal")
            for day in spray_days:
                text_widget.insert(tk.END, f"✓ {day}\n", "risk_low")
        
        text_widget.insert(tk.END, "\n" + "="*80 + "\n", "normal")
        text_widget.insert(tk.END, "📱 For more advisories: Meghdoot App (IMD-ICAR)\n", "normal")
        text_widget.insert(tk.END, "📞 Kisan Call Centre: 1800-180-1551\n", "normal")
    
    def identify_plant_with_gemini(self, image_path):
        """Use Gemini AI to identify the plant name and disease"""
        try:
            image = Image.open(image_path)
            
            prompt = """You are an expert botanist. Analyze this plant image and provide ONLY:

1. Plant common name (single word if possible, e.g., "Apple", "Tomato", "Rice")
2. Disease visible (if any)

Respond in this EXACT format (2 lines only):
PLANT: [Plant Name]
DISEASE: [Disease Name or "Healthy"]

Be brief and use simple common names."""

            response = self.model.generate_content([prompt, image])
            result = response.text.strip()
            
            plant_info = {}
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
            
            cursor.execute(f"SELECT * FROM {self.plant_table} LIMIT 1")
            row = cursor.fetchone()
            
            if row:
                match = dict(zip(columns, row))
                conn.close()
                return match, False
            
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
    
    def create_clickable_link(self, text_widget, text, url, tag_name):
        """Create a clickable hyperlink in text widget"""
        text_widget.insert(tk.END, text, tag_name)
        text_widget.tag_config(tag_name, foreground="#ff9900", underline=True)
        text_widget.tag_bind(tag_name, "<Button-1>", lambda e: webbrowser.open(url))
        text_widget.tag_bind(tag_name, "<Enter>", lambda e: text_widget.config(cursor="hand2"))
        text_widget.tag_bind(tag_name, "<Leave>", lambda e: text_widget.config(cursor=""))
    
    def open_chatbot_window(self):
        """Open chatbot window for user queries"""
        if not self.current_plant_info:
            messagebox.showwarning("Warning", "Please analyze an image first!")
            return
        
        chatbot_window = tk.Toplevel(self.root)
        chatbot_window.title("Plant Health Chatbot")
        chatbot_window.geometry("600x700")
        chatbot_window.configure(bg="#000000")
        
        # Title
        title_label = tk.Label(
            chatbot_window,
            text="🤖 Ask About Your Plant",
            font=("Arial Black", 18, "bold"),
            bg="#000000",
            fg="#00ff00"
        )
        title_label.pack(pady=15)
        
        # Chat display area
        chat_frame = tk.Frame(chatbot_window, bg="#001a00", bd=2, relief=tk.RIDGE)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))
        
        chat_display = scrolledtext.ScrolledText(
            chat_frame,
            font=("Segoe UI", 12),
            bg="#001a00",
            fg="#00ff00",
            wrap=tk.WORD,
            padx=15,
            pady=15
        )
        chat_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        chat_display.config(state=tk.DISABLED)
        
        # Initial greeting
        self.add_chatbot_message(chat_display, "Bot", 
            f"Hello! I'm here to help you with your {self.current_plant_info.get('plant_name', 'plant')}. "
            "Ask me anything about the disease, treatment, or prevention!")
        
        # Input frame
        input_frame = tk.Frame(chatbot_window, bg="#000000")
        input_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        # Language selection
        lang_frame = tk.Frame(input_frame, bg="#000000")
        lang_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            lang_frame,
            text="Voice Language:",
            font=("Arial", 11, "bold"),
            bg="#000000",
            fg="#00ff00"
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        language_var = tk.StringVar(value='English')
        language_menu = tk.OptionMenu(lang_frame, language_var, *self.indian_languages.keys())
        language_menu.config(
            bg="#001a00",
            fg="#00ff00",
            font=("Arial", 10),
            activebackground="#003300",
            activeforeground="#00ff00"
        )
        language_menu.pack(side=tk.LEFT)
        
        # Text input
        user_input = tk.Entry(
            input_frame,
            font=("Segoe UI", 12),
            bg="#001a00",
            fg="#00ff00",
            insertbackground="#00ff00"
        )
        user_input.pack(fill=tk.X, pady=(0, 10))
        
        # Button frame
        button_frame = tk.Frame(input_frame, bg="#000000")
        button_frame.pack(fill=tk.X)
        
        def send_message():
            query = user_input.get().strip()
            if query:
                self.add_chatbot_message(chat_display, "You", query)
                user_input.delete(0, tk.END)
                threading.Thread(target=self.process_chatbot_query, 
                               args=(query, chat_display), daemon=True).start()
        
        def start_voice_input():
            selected_lang = language_var.get()
            lang_code = self.indian_languages[selected_lang]
            self.add_chatbot_message(chat_display, "System", 
                                    f"🎤 Listening in {selected_lang}... Please speak now.")
            threading.Thread(target=self.voice_to_text_browser, 
                           args=(lang_code, user_input, chat_display), daemon=True).start()
        
        # Send button
        send_btn = tk.Button(
            button_frame,
            text="📤 Send",
            font=("Arial", 11, "bold"),
            bg="#00ff00",
            fg="#000000",
            cursor="hand2",
            command=send_message
        )
        send_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Voice button
        voice_btn = tk.Button(
            button_frame,
            text="🎤 Voice Input",
            font=("Arial", 11, "bold"),
            bg="#00cc00",
            fg="#000000",
            cursor="hand2",
            command=start_voice_input
        )
        voice_btn.pack(side=tk.LEFT)
        
        # Bind Enter key
        user_input.bind("<Return>", lambda e: send_message())
    
    def voice_to_text_browser(self, language_code, entry_widget, chat_display):
        """
        Alternative voice recognition using browser-based approach.
        This method uses Google's Speech Recognition API without requiring microphone access.
        """
        try:
            # Open browser for voice input
            import tempfile
            import os
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Voice Input</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background: linear-gradient(135deg, #001a00, #003300);
                        color: #00ff00;
                    }}
                    .container {{
                        text-align: center;
                        background: #001a00;
                        padding: 40px;
                        border-radius: 15px;
                        box-shadow: 0 0 30px rgba(0, 255, 0, 0.3);
                    }}
                    h1 {{ margin-bottom: 20px; }}
                    #start-btn {{
                        background: #00ff00;
                        color: #000000;
                        border: none;
                        padding: 15px 30px;
                        font-size: 18px;
                        font-weight: bold;
                        border-radius: 8px;
                        cursor: pointer;
                        transition: all 0.3s;
                    }}
                    #start-btn:hover {{
                        background: #00cc00;
                        transform: scale(1.05);
                    }}
                    #result {{
                        margin-top: 30px;
                        padding: 20px;
                        background: #002200;
                        border-radius: 8px;
                        min-height: 50px;
                        font-size: 16px;
                    }}
                    .status {{
                        margin-top: 15px;
                        font-style: italic;
                        color: #ffff00;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🎤 Voice Input</h1>
                    <button id="start-btn" onclick="startRecognition()">Start Speaking</button>
                    <div id="result">Your text will appear here...</div>
                    <div class="status" id="status"></div>
                    <p style="margin-top: 20px; color: #00cc00;">
                        Copy the text above and paste it into the chatbot.
                    </p>
                </div>
                
                <script>
                    const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
                    recognition.lang = '{language_code}';
                    recognition.continuous = false;
                    recognition.interimResults = false;
                    
                    function startRecognition() {{
                        document.getElementById('status').textContent = 'Listening...';
                        document.getElementById('result').textContent = 'Speak now...';
                        recognition.start();
                    }}
                    
                    recognition.onresult = function(event) {{
                        const transcript = event.results[0][0].transcript;
                        document.getElementById('result').textContent = transcript;
                        document.getElementById('status').textContent = 'Done! Copy the text above.';
                        
                        // Auto-copy to clipboard
                        navigator.clipboard.writeText(transcript).then(() => {{
                            document.getElementById('status').textContent = '✓ Copied to clipboard! Paste in chatbot.';
                        }});
                    }};
                    
                    recognition.onerror = function(event) {{
                        document.getElementById('status').textContent = 'Error: ' + event.error;
                        document.getElementById('result').textContent = 'Please try again.';
                    }};
                    
                    recognition.onend = function() {{
                        document.getElementById('status').textContent += ' (Recognition ended)';
                    }};
                </script>
            </body>
            </html>
            """
            
            # Create temporary HTML file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html', encoding='utf-8') as f:
                f.write(html_content)
                temp_file = f.name
            
            # Open in browser
            webbrowser.open('file://' + temp_file)
            
            self.root.after(0, lambda: self.add_chatbot_message(
                chat_display, "System", 
                "✓ Voice input opened in browser. Speak, then copy and paste the text here."))
            
            # Clean up temp file after 30 seconds
            def cleanup():
                import time
                time.sleep(30)
                try:
                    os.unlink(temp_file)
                except:
                    pass
            
            threading.Thread(target=cleanup, daemon=True).start()
            
        except Exception as e:
            self.root.after(0, lambda: self.add_chatbot_message(
                chat_display, "System", f"❌ Voice input error: {e}. Please type your question instead."))
    
    def add_chatbot_message(self, chat_display, sender, message):
        """Add a message to the chatbot display"""
        chat_display.config(state=tk.NORMAL)
        
        if sender == "Bot":
            chat_display.insert(tk.END, f"🤖 Bot: ", "bot_label")
            chat_display.insert(tk.END, f"{message}\n\n", "bot_text")
            chat_display.tag_config("bot_label", foreground="#00ffff", font=("Arial", 12, "bold"))
            chat_display.tag_config("bot_text", foreground="#ccffcc")
        elif sender == "You":
            chat_display.insert(tk.END, f"👤 You: ", "user_label")
            chat_display.insert(tk.END, f"{message}\n\n", "user_text")
            chat_display.tag_config("user_label", foreground="#ffff00", font=("Arial", 12, "bold"))
            chat_display.tag_config("user_text", foreground="#ffffcc")
        else:  # System
            chat_display.insert(tk.END, f"ℹ️ {message}\n\n", "system_text")
            chat_display.tag_config("system_text", foreground="#ff9900", font=("Arial", 11, "italic"))
        
        chat_display.see(tk.END)
        chat_display.config(state=tk.DISABLED)
    
    def process_chatbot_query(self, query, chat_display):
        """Process user query using Gemini AI"""
        try:
            # Create context from current plant info
            context = f"""You are a plant disease expert chatbot. The user is asking about:
Plant: {self.current_plant_info.get('plant_name', 'Unknown')}
Disease: {self.current_plant_info.get('disease', 'Unknown')}
Treatment Type: {self.treatment_type or 'general'}

Available information:
{self.current_plant_info}

User question: {query}

Provide a helpful, concise answer (2-3 sentences) about this specific plant and disease."""

            response = self.model.generate_content(context)
            answer = response.text.strip()
            
            self.root.after(0, lambda: self.add_chatbot_message(chat_display, "Bot", answer))
            
        except Exception as e:
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            self.root.after(0, lambda: self.add_chatbot_message(chat_display, "Bot", error_msg))
    
    def create_widgets(self):
        # Main container
        main_container = tk.Frame(self.root, bg="#000000")
        main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)
        
        # Title
        title_label = tk.Label(
            main_container,
            text="🌿 Plant Disease Detection & Treatment 🌿",
            font=("Arial Black", 32, "bold"),
            bg="#000000",
            fg="#00ff00"
        )
        title_label.pack(pady=(10, 20))
        
        # Treatment Selection Frame
        treatment_frame = tk.Frame(main_container, bg="#001a00", bd=2, relief=tk.RIDGE)
        treatment_frame.pack(fill=tk.X, pady=(0, 20))
        
        treatment_label = tk.Label(
            treatment_frame,
            text="SELECT TREATMENT TYPE:",
            font=("Arial Black", 14, "bold"),
            bg="#001a00",
            fg="#00ff00"
        )
        treatment_label.pack(pady=(15, 10))
        
        # Radio buttons frame
        radio_frame = tk.Frame(treatment_frame, bg="#001a00")
        radio_frame.pack(pady=(0, 15))
        
        self.treatment_var = tk.StringVar(value="chemical")
        
        chemical_radio = tk.Radiobutton(
            radio_frame,
            text="💊 Chemical Treatment",
            variable=self.treatment_var,
            value="chemical",
            font=("Arial", 13, "bold"),
            bg="#001a00",
            fg="#00ff00",
            selectcolor="#003300",
            activebackground="#001a00",
            activeforeground="#00ff00",
            cursor="hand2",
            command=self.clear_output
        )
        chemical_radio.pack(side=tk.LEFT, padx=20)
        
        organic_radio = tk.Radiobutton(
            radio_frame,
            text="🌱 Organic/Natural Treatment",
            variable=self.treatment_var,
            value="organic",
            font=("Arial", 13, "bold"),
            bg="#001a00",
            fg="#00ff00",
            selectcolor="#003300",
            activebackground="#001a00",
            activeforeground="#00ff00",
            cursor="hand2",
            command=self.clear_output
        )
        organic_radio.pack(side=tk.LEFT, padx=20)
        
        # Content Frame
        content_frame = tk.Frame(main_container, bg="#000000")
        content_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Left side - Image section
        left_frame = tk.Frame(content_frame, bg="#000000")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))
        
        # Select Image Button
        select_btn = tk.Button(
            left_frame,
            text="📁 SELECT IMAGE",
            font=("Arial", 16, "bold"),
            bg="#00ff00",
            fg="#000000",
            activebackground="#00cc00",
            activeforeground="#000000",
            cursor="hand2",
            bd=0,
            padx=40,
            pady=15,
            command=self.select_image
        )
        select_btn.pack(pady=(0, 20))
        
        # Image Display Frame
        image_outer_frame = tk.Frame(left_frame, bg="#00ff00", bd=0)
        image_outer_frame.pack(fill=tk.BOTH, expand=True)
        
        image_frame = tk.Frame(image_outer_frame, bg="#001a00", bd=0)
        image_frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        
        self.image_label = tk.Label(
            image_frame,
            text="NO IMAGE SELECTED",
            font=("Arial", 18, "bold"),
            bg="#001a00",
            fg="#006600"
        )
        self.image_label.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Button frame for Analyze, Weather, and Chatbot
        button_container = tk.Frame(left_frame, bg="#000000")
        button_container.pack(pady=(20, 0))
        
        # Analyze Button
        self.analyze_btn = tk.Button(
            button_container,
            text="🔍 ANALYZE PLANT",
            font=("Arial", 14, "bold"),
            bg="#00cc00",
            fg="#000000",
            activebackground="#009900",
            activeforeground="#000000",
            cursor="hand2",
            bd=0,
            padx=30,
            pady=12,
            command=self.analyze_image,
            state=tk.DISABLED
        )
        self.analyze_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # Weather Advisory Button (NEW!)
        self.weather_btn = tk.Button(
            button_container,
            text="🌤️ WEATHER ADVISORY",
            font=("Arial", 14, "bold"),
            bg="#ff9900",
            fg="#000000",
            activebackground="#cc7700",
            activeforeground="#000000",
            cursor="hand2",
            bd=0,
            padx=30,
            pady=12,
            command=self.open_weather_advisory_window,
            state=tk.DISABLED
        )
        self.weather_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # Chatbot Button
        self.chatbot_btn = tk.Button(
            button_container,
            text="💬 ASK CHATBOT",
            font=("Arial", 14, "bold"),
            bg="#0099ff",
            fg="#000000",
            activebackground="#0077cc",
            activeforeground="#000000",
            cursor="hand2",
            bd=0,
            padx=30,
            pady=12,
            command=self.open_chatbot_window,
            state=tk.DISABLED
        )
        self.chatbot_btn.pack(side=tk.LEFT)
        
        # Right side - Output section
        right_frame = tk.Frame(content_frame, bg="#000000")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(15, 0))
        
        # Output Title
        output_title = tk.Label(
            right_frame,
            text="ANALYSIS RESULT",
            font=("Arial Black", 18, "bold"),
            bg="#000000",
            fg="#00ff00"
        )
        output_title.pack(pady=(0, 15))
        
        # Output Frame
        output_outer_frame = tk.Frame(right_frame, bg="#00ff00", bd=0)
        output_outer_frame.pack(fill=tk.BOTH, expand=True)
        
        output_inner_frame = tk.Frame(output_outer_frame, bg="#001a00", bd=0)
        output_inner_frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(output_inner_frame, bg="#001a00", troughcolor="#000000")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
        
        self.output_text = tk.Text(
            output_inner_frame,
            font=("Segoe UI", 13),
            bg="#001a00",
            fg="#00ff00",
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            padx=20,
            pady=20,
            relief=tk.FLAT,
            spacing1=5,
            spacing3=5,
            insertbackground="#00ff00"
        )
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        scrollbar.config(command=self.output_text.yview)
        
        # Configure text tags
        self.output_text.tag_configure("heading", font=("Arial Black", 16, "bold"), foreground="#00ff00", spacing1=10, spacing3=8)
        self.output_text.tag_configure("plant_name", font=("Segoe UI", 15, "bold"), foreground="#66ff66", spacing3=10)
        self.output_text.tag_configure("disease_name", font=("Segoe UI", 14, "bold"), foreground="#ffff00", spacing1=6, spacing3=3)
        self.output_text.tag_configure("section_header", font=("Arial", 14, "bold"), foreground="#00ffff", spacing1=10, spacing3=5)
        self.output_text.tag_configure("treatment", font=("Segoe UI", 13), foreground="#00ff99", spacing3=3)
        self.output_text.tag_configure("normal", font=("Segoe UI", 13), foreground="#ccffcc")
        self.output_text.tag_configure("pesticide", font=("Segoe UI", 13, "bold"), foreground="#ff9900", spacing3=3)
        
        # Footer
        footer_label = tk.Label(
            main_container,
            text="Powered by Gemini AI + WeatherAPI + Browser Voice Recognition + Smart Chatbot",
            font=("Arial", 11, "bold"),
            bg="#000000",
            fg="#006600"
        )
        footer_label.pack(pady=(20, 10))
    
    def clear_output(self):
        """Clear output when treatment type is changed"""
        self.output_text.delete(1.0, tk.END)
    
    def select_image(self):
        file_path = filedialog.askopenfilename(
            title="Select Plant Image",
            filetypes=[
                ("Image Files", "*.png *.jpg *.jpeg *.webp *.gif *.bmp"),
                ("All Files", "*.*")
            ]
        )
        
        if file_path:
            self.selected_image_path = file_path
            self.display_selected_image(file_path)
            self.analyze_btn.config(state=tk.NORMAL)
            self.output_text.delete(1.0, tk.END)
    
    def display_selected_image(self, image_path):
        try:
            self.image_label.update()
            label_width = self.image_label.winfo_width()
            label_height = self.image_label.winfo_height()
            
            if label_width < 100:
                label_width = 400
            if label_height < 100:
                label_height = 300
            
            img = Image.open(image_path)
            img_ratio = img.width / img.height
            label_ratio = label_width / label_height
            
            if img_ratio > label_ratio:
                new_width = label_width - 40
                new_height = int(new_width / img_ratio)
            else:
                new_height = label_height - 40
                new_width = int(new_height * img_ratio)
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            self.display_image = ImageTk.PhotoImage(img)
            
            self.image_label.config(image=self.display_image, text="", bg="#001a00")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {str(e)}")
    
    def analyze_image(self):
        if not self.selected_image_path:
            messagebox.showwarning("Warning", "Please select an image first!")
            return
        
        self.treatment_type = self.treatment_var.get()
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, "🔄 Analyzing image...\n\n")
        self.analyze_btn.config(state=tk.DISABLED)
        self.chatbot_btn.config(state=tk.DISABLED)
        self.weather_btn.config(state=tk.DISABLED)
        
        thread = threading.Thread(target=self.perform_hybrid_analysis, daemon=True)
        thread.start()
    
    def perform_hybrid_analysis(self):
        """Multi-step analysis: Gemini identifies plant, then fetch from both databases"""
        try:
            self.root.after(0, self.update_output_simple, 
                "🔄 Step 1: Identifying plant with Gemini AI...\n\n")
            
            plant_info = self.identify_plant_with_gemini(self.selected_image_path)
            
            if plant_info is None:
                self.root.after(0, self.update_output_simple, 
                    "❌ Failed to identify plant. Please try another image.")
                return
            
            plant_name = plant_info.get('PLANT', 'Unknown')
            disease = plant_info.get('DISEASE', 'Unknown')
            
            self.root.after(0, self.update_output_simple, 
                f"✅ Plant identified: {plant_name}\n"
                f"✅ Condition: {disease}\n\n"
                f"🔄 Step 2: Searching plant disease database...\n\n")
            
            plant_match, plant_found = self.search_plant_database(plant_name, disease)
            
            self.root.after(0, self.update_output_simple, 
                f"✅ Plant identified: {plant_name}\n"
                f"✅ Condition: {disease}\n"
                f"{'✅' if plant_found else '⚠️'} Plant disease database: {'Match found' if plant_found else 'No exact match'}\n\n"
                f"🔄 Step 3: Searching pesticide solution database...\n\n")
            
            pesticide_match, pesticide_found = self.search_pesticide_solution(plant_name, disease)
            
            self.root.after(0, self.update_output_simple, 
                f"✅ Plant identified: {plant_name}\n"
                f"✅ Condition: {disease}\n"
                f"{'✅' if plant_found else '⚠️'} Plant disease database: {'Match found' if plant_found else 'No exact match'}\n"
                f"{'✅' if pesticide_found else '⚠️'} Pesticide solution database: {'Match found' if pesticide_found else 'No exact match'}\n\n"
                f"📊 Preparing comprehensive report...\n\n")
            
            # Store current analysis for chatbot and weather advisory
            self.current_plant_info = {
                'plant_name': plant_name,
                'disease': disease,
                'plant_match': plant_match,
                'pesticide_match': pesticide_match,
                'treatment_type': self.treatment_type
            }
            
            self.root.after(0, self.format_and_display_comprehensive, 
                plant_name, disease, plant_match, pesticide_match)
            
            # Enable chatbot and weather buttons
            self.root.after(0, lambda: self.chatbot_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.weather_btn.config(state=tk.NORMAL))
            
        except Exception as e:
            error_msg = f"❌ Error during analysis: {str(e)}"
            import traceback
            traceback.print_exc()
            self.root.after(0, self.update_output_simple, error_msg)
        
        finally:
            self.root.after(0, lambda: self.analyze_btn.config(state=tk.NORMAL))
    
    def format_and_display_comprehensive(self, plant_name, disease, plant_match, pesticide_match):
        """Format and display comprehensive results with clickable pesticide links"""
        self.output_text.delete(1.0, tk.END)
        
        # === PLANT IDENTIFICATION ===
        self.output_text.insert(tk.END, "🌱 PLANT IDENTIFIED\n", "heading")
        self.output_text.insert(tk.END, f"{plant_name}\n\n", "plant_name")
        
        # === DISEASE DETECTED ===
        self.output_text.insert(tk.END, "🦠 DISEASE/CONDITION DETECTED\n", "heading")
        
        if disease.lower() == "healthy":
            self.output_text.insert(tk.END, f"✅ {disease} - No disease detected!\n\n", "plant_name")
            
            if pesticide_match and pesticide_match.get('Disease'):
                pest_disease = pesticide_match.get('Disease')
                self.output_text.insert(tk.END, "ℹ️ Common Disease for this Plant:\n", "section_header")
                self.output_text.insert(tk.END, f"{pest_disease}\n", "normal")
                self.output_text.insert(tk.END, "(This information is for reference. Your plant appears healthy.)\n\n", "normal")
        else:
            self.output_text.insert(tk.END, f"⚠️ {disease}\n\n", "disease_name")
        
        # === SYMPTOMS ===
        if plant_match and plant_match.get('symptoms'):
            self.output_text.insert(tk.END, "⚠️ SYMPTOMS\n", "heading")
            self.output_text.insert(tk.END, f"{plant_match.get('symptoms')}\n\n", "normal")
        
        # === TREATMENT ===
        if disease.lower() != "healthy":
            if self.treatment_type == "chemical":
                self.output_text.insert(tk.END, "💊 CHEMICAL TREATMENT\n", "heading")
                
                has_treatment = False
                
                if plant_match and plant_match.get('chemical_treatment'):
                    has_treatment = True
                    self.output_text.insert(tk.END, "Primary Treatment:\n", "section_header")
                    self.output_text.insert(tk.END, f"{plant_match.get('chemical_treatment')}\n\n", "treatment")
                
                if plant_match and plant_match.get('chemical_fungicide'):
                    has_treatment = True
                    self.output_text.insert(tk.END, "Chemical Fungicide:\n", "section_header")
                    self.output_text.insert(tk.END, f"{plant_match.get('chemical_fungicide')}\n\n", "treatment")
                
                if plant_match and plant_match.get('foliar_spray'):
                    has_treatment = True
                    self.output_text.insert(tk.END, "Foliar Spray:\n", "section_header")
                    self.output_text.insert(tk.END, f"{plant_match.get('foliar_spray')}\n\n", "treatment")
                
                # Pesticide with clickable link
                if pesticide_match:
                    has_treatment = True
                    self.output_text.insert(tk.END, "🧪 RECOMMENDED PESTICIDE\n", "heading")
                    
                    pesticide_type = pesticide_match.get('Pesticide Type', 'N/A')
                    chemical_name = pesticide_match.get('Chemical Name', 'N/A')
                    
                    self.output_text.insert(tk.END, f"Type: ", "section_header")
                    self.output_text.insert(tk.END, f"{pesticide_type}\n", "pesticide")
                    
                    self.output_text.insert(tk.END, f"Chemical Name: ", "section_header")
                    
                    # Create clickable link for pesticide
                    if chemical_name != 'N/A':
                        search_url = f"https://www.google.com/search?q={chemical_name.replace(' ', '+')}+pesticide"
                        tag_name = f"pesticide_link_{id(chemical_name)}"
                        self.create_clickable_link(self.output_text, chemical_name, search_url, tag_name)
                        self.output_text.insert(tk.END, " (Click to search)\n\n", "normal")
                    else:
                        self.output_text.insert(tk.END, f"{chemical_name}\n\n", "pesticide")
                    
                    if pesticide_match.get('Disease'):
                        self.output_text.insert(tk.END, "For Disease: ", "section_header")
                        match_info = f"{pesticide_match.get('Disease', '')}\n\n"
                        self.output_text.insert(tk.END, match_info, "normal")
                
                if not has_treatment:
                    self.output_text.insert(tk.END, "⚠️ No specific chemical treatment found in database.\n", "normal")
                    self.output_text.insert(tk.END, "Recommendation: Consult with a local agricultural expert.\n\n", "normal")
            else:  # organic
                self.output_text.insert(tk.END, "🌱 ORGANIC TREATMENT\n", "heading")
                
                has_treatment = False
                
                if plant_match and plant_match.get('organic_treatment'):
                    has_treatment = True
                    self.output_text.insert(tk.END, f"{plant_match.get('organic_treatment')}\n\n", "treatment")
                
                if not has_treatment:
                    self.output_text.insert(tk.END, "⚠️ No specific organic treatment found in database.\n", "normal")
                    self.output_text.insert(tk.END, "General organic recommendations:\n", "section_header")
                    self.output_text.insert(tk.END, "• Use neem oil spray\n", "normal")
                    self.output_text.insert(tk.END, "• Apply compost tea\n", "normal")
                    self.output_text.insert(tk.END, "• Maintain proper plant spacing for air circulation\n", "normal")
                    self.output_text.insert(tk.END, "• Remove infected plant parts\n\n", "normal")
        else:
            self.output_text.insert(tk.END, "✅ PLANT HEALTH STATUS\n", "heading")
            self.output_text.insert(tk.END, "Your plant appears healthy! Here are some care tips:\n\n", "normal")
            
            self.output_text.insert(tk.END, "🌿 General Care Tips:\n", "section_header")
            self.output_text.insert(tk.END, "• Continue regular watering schedule\n", "normal")
            self.output_text.insert(tk.END, "• Ensure adequate sunlight\n", "normal")
            self.output_text.insert(tk.END, "• Monitor for early signs of disease\n", "normal")
            self.output_text.insert(tk.END, "• Maintain proper fertilization\n\n", "normal")
        
        # === PREVENTIVE MEASURES ===
        if plant_match and plant_match.get('preventive_measures'):
            self.output_text.insert(tk.END, "🛡️ PREVENTIVE MEASURES\n", "heading")
            self.output_text.insert(tk.END, f"{plant_match.get('preventive_measures')}\n\n", "normal")
        elif disease.lower() != "healthy":
            self.output_text.insert(tk.END, "🛡️ GENERAL PREVENTIVE MEASURES\n", "heading")
            self.output_text.insert(tk.END, "• Practice crop rotation\n", "normal")
            self.output_text.insert(tk.END, "• Remove infected plant debris\n", "normal")
            self.output_text.insert(tk.END, "• Ensure proper drainage\n", "normal")
            self.output_text.insert(tk.END, "• Use disease-resistant varieties\n", "normal")
            self.output_text.insert(tk.END, "• Avoid overhead watering\n\n", "normal")
        
        # === WEATHER ADVISORY PROMPT ===
        self.output_text.insert(tk.END, "🌤️ WEATHER-BASED DISEASE PREDICTION\n", "heading")
        self.output_text.insert(tk.END, "Click '🌤️ WEATHER ADVISORY' button to get weather-based disease predictions and spraying recommendations!\n\n", "normal")
        
        # === CHATBOT PROMPT ===
        self.output_text.insert(tk.END, "💬 NEED MORE HELP?\n", "heading")
        self.output_text.insert(tk.END, "Click the '💬 ASK CHATBOT' button to ask questions in your language!\n\n", "normal")
        
        # === DATABASE SOURCE INFO ===
        self.output_text.insert(tk.END, "ℹ️ DATA SOURCES\n", "heading")
        sources = []
        if plant_match:
            sources.append("✓ Plant Disease Database")
        if pesticide_match:
            sources.append("✓ Pesticide Solution Database")
        sources.append("✓ WeatherAPI.com (for weather-based predictions)")
        if not sources:
            sources.append("⚠️ Using AI identification only")
        
        self.output_text.insert(tk.END, "\n".join(sources) + "\n", "normal")
    
    def update_output_simple(self, text):
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, text)


if __name__ == "__main__":
    root = tk.Tk()
    app = PlantDeficiencyAnalyzer(root)
    root.mainloop()
