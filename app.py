# app.py - VERSIÓN CON FILTRADO CORRECTO DE EQUIPOS POR LIGA
import requests
from flask import Flask, request, jsonify, render_template_string
import os
import logging
import time
from typing import Dict, List, Optional

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuración - URL de tu API de red neuronal
NEURAL_API_URL = os.environ.get('NEURAL_API_URL', 'https://neural-api-predictor.onrender.com')
logger.info(f"🔗 Conectando a API de red neuronal: {NEURAL_API_URL}")

class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'BettingApp-Flask/3.0'
        })
        # Cache para equipos por división
        self.teams_by_division_cache = {}
    
    def make_request(self, endpoint, method='GET', data=None, timeout=10):
        """Método genérico para hacer requests"""
        try:
            url = f"{self.base_url}{endpoint}"
            logger.info(f"🌐 Request: {method} {url}")
            
            if method.upper() == 'GET':
                response = self.session.get(url, timeout=timeout)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, timeout=timeout)
            else:
                return None
                
            logger.info(f"📨 Response status: {response.status_code}")
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ Error {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"⏰ Timeout en {endpoint}")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"🔌 Connection error en {endpoint}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error en {endpoint}: {e}")
            return None
    
    def health_check(self):
        """Verificar estado de la API"""
        logger.info("🔍 Health check...")
        data = self.make_request('/health')
        if data:
            return True, data
        return False, None
    
    def get_divisions(self):
        """Obtener divisiones"""
        logger.info("🔍 Obteniendo divisiones...")
        data = self.make_request('/divisions')
        if data and data.get('success'):
            return data.get('divisions', {})
        return {}
    
    def get_all_teams(self):
        """Obtener TODOS los equipos"""
        logger.info("🔍 Obteniendo todos los equipos...")
        data = self.make_request('/teams')
        if data and data.get('success'):
            return data.get('teams', [])
        return []
    
    def get_teams_for_division(self, division):
        """Obtener equipos para una división específica usando la API"""
        logger.info(f"🔍 Obteniendo equipos para división: {division}")
        
        # Si ya tenemos los equipos en cache, devolverlos
        if division in self.teams_by_division_cache:
            teams = self.teams_by_division_cache[division]
            logger.info(f"✅ Equipos desde cache para {division}: {len(teams)} equipos")
            return teams
        
        # Intentar obtener equipos filtrados por división desde la API
        try:
            endpoint = f'/teams?division={division}'
            data = self.make_request(endpoint)
            
            if data and data.get('success') and data.get('teams'):
                teams = data.get('teams', [])
                
                # Si la API devuelve una lista filtrada (no todos los equipos), guardar en cache
                if len(teams) < 500:  # Asumimos que si son menos de 500, están filtrados
                    self.teams_by_division_cache[division] = teams
                    logger.info(f"✅ Equipos API para {division}: {len(teams)} equipos")
                    return teams
        except Exception as e:
            logger.error(f"❌ Error obteniendo equipos filtrados: {e}")
        
        # Si no hay equipos filtrados, obtener todos y filtrar localmente
        logger.info(f"🔍 Filtrando equipos localmente para: {division}")
        all_teams = self.get_all_teams()
        
        if not all_teams:
            logger.warning(f"⚠️ No se pudieron obtener equipos, usando demo para {division}")
            return self._get_demo_teams_for_division(division)
        
        # Filtrar equipos basado en conocimiento de la división
        filtered_teams = self._filter_teams_by_division(all_teams, division)
        
        if filtered_teams:
            self.teams_by_division_cache[division] = filtered_teams
            logger.info(f"✅ Equipos filtrados para {division}: {len(filtered_teams)} equipos")
            return filtered_teams
        else:
            logger.warning(f"⚠️ No se encontraron equipos para {division}, usando demo")
            return self._get_demo_teams_for_division(division)
    
    def _filter_teams_by_division(self, all_teams, division):
        """Filtrar equipos por división usando conocimiento específico del fútbol"""
        # Patrones de equipos por liga basados en el entrenamiento
        division_patterns = {
            'E0': ['Arsenal', 'Aston Villa', 'Bournemouth', 'Brentford', 'Brighton', 
                  'Chelsea', 'Crystal Palace', 'Everton', 'Fulham', 'Leeds', 
                  'Leicester', 'Liverpool', 'Man City', 'Man United', 'Newcastle', 
                  'Nottingham Forest', 'Southampton', 'Tottenham', 'West Ham', 'Wolves',
                  'Burnley', 'Sheffield United', 'Luton', 'Ipswich', 'Norwich'],
            
            'SP1': ['Almeria', 'Athletic Bilbao', 'Atlético Madrid', 'Barcelona', 
                   'Betis', 'Celta Vigo', 'Elche', 'Espanyol', 'Getafe', 'Girona',
                   'Mallorca', 'Osasuna', 'Rayo Vallecano', 'Real Madrid', 'Real Sociedad',
                   'Sevilla', 'Valencia', 'Valladolid', 'Villarreal', 'Cadiz',
                   'Alaves', 'Granada', 'Las Palmas', 'Málaga', 'Levante'],
            
            'I1': ['AC Milan', 'Atalanta', 'Bologna', 'Cremonese', 'Empoli', 
                  'Fiorentina', 'Inter', 'Juventus', 'Lazio', 'Lecce', 
                  'Monza', 'Napoli', 'Roma', 'Salernitana', 'Sampdoria', 
                  'Sassuolo', 'Spezia', 'Torino', 'Udinese', 'Verona'],
            
            'D1': ['Augsburg', 'Bayer Leverkusen', 'Bayern Munich', 'Bochum', 
                  'Borussia Dortmund', 'Borussia M.Gladbach', 'Eintracht Frankfurt', 
                  'Freiburg', 'Hertha Berlin', 'Hoffenheim', 'Köln', 'Mainz', 
                  'RB Leipzig', 'Schalke 04', 'Stuttgart', 'Union Berlin', 'Werder Bremen', 'Wolfsburg'],
            
            'F1': ['AC Ajaccio', 'Angers', 'Auxerre', 'Clermont Foot', 'Lens', 
                  'Lille', 'Lorient', 'Lyon', 'Marseille', 'Monaco', 
                  'Montpellier', 'Nantes', 'Nice', 'Paris SG', 'Reims', 
                  'Rennes', 'Strasbourg', 'Toulouse', 'Troyes'],
            
            'BRA': ['Flamengo', 'Palmeiras', 'Santos', 'Corinthians', 'São Paulo', 'Grêmio', 'Internacional'],
            'ARG': ['Boca Juniors', 'River Plate', 'Racing Club', 'San Lorenzo', 'Independiente', 'Estudiantes'],
            'MEX': ['América', 'Guadalajara', 'Cruz Azul', 'UNAM', 'Monterrey', 'Tigres'],
            'POR': ['Benfica', 'Porto', 'Sporting CP', 'Braga', 'Vitória Guimarães'],
            'NED': ['Ajax', 'PSV', 'Feyenoord', 'AZ Alkmaar', 'Twente'],
            'TUR': ['Galatasaray', 'Fenerbahçe', 'Beşiktaş', 'Trabzonspor', 'Başakşehir'],
            'RUS': ['Zenit', 'Spartak Moscow', 'CSKA Moscow', 'Lokomotiv Moscow', 'Dinamo Moscow'],
            'BEL': ['Anderlecht', 'Club Brugge', 'Genk', 'Standard Liège', 'Antwerp'],
            'SCO': ['Celtic', 'Rangers', 'Aberdeen', 'Hearts', 'Hibernian'],
            'AUT': ['Red Bull Salzburg', 'Rapid Vienna', 'Austria Vienna', 'Sturm Graz', 'LASK'],
            'DEN': ['Copenhagen', 'Midtjylland', 'Brondby', 'Aarhus', 'Vejle'],
            'SWE': ['Malmö FF', 'AIK', 'Hammarby', 'Djurgården', 'IFK Göteborg'],
            'NOR': ['Bodø/Glimt', 'Molde', 'Rosenborg', 'Viking', 'Lillestrøm'],
            'SUI': ['Young Boys', 'Basel', 'Zurich', 'Lugano', 'Servette'],
            'GRE': ['Olympiacos', 'Panathinaikos', 'AEK Athens', 'PAOK', 'Aris'],
            'UKR': ['Shakhtar Donetsk', 'Dynamo Kyiv', 'Dnipro-1', 'Zorya Luhansk', 'Vorskla Poltava'],
            'JAP': ['Kawasaki Frontale', 'Yokohama F. Marinos', 'Urawa Reds', 'FC Tokyo', 'Nagoya Grampus'],
            'USA': ['Los Angeles FC', 'Philadelphia Union', 'Austin FC', 'New York City FC', 'Seattle Sounders'],
            'CHN': ['Shanghai Port', 'Beijing Guoan', 'Shandong Taishan', 'Guangzhou', 'Tianjin Jinmen Tiger'],
            'IRL': ['Shamrock Rovers', 'Bohemians', 'Derry City', 'Dundalk', 'St Patrick\'s Athletic'],
            'FIN': ['HJK Helsinki', 'KuPS', 'SJK', 'Ilves', 'Honka'],
            'POL': ['Legia Warsaw', 'Lech Poznań', 'Raków Częstochowa', 'Pogoń Szczecin', 'Górnik Zabrze'],
            'ROM': ['FCSB', 'CFR Cluj', 'Rapid București', 'Universitatea Craiova', 'Farul Constanța']
        }
        
        # Obtener los patrones para esta división
        patterns = division_patterns.get(division, [])
        if not patterns:
            return []
        
        # Filtrar equipos que coincidan con los patrones
        filtered_teams = []
        for team in all_teams:
            team_lower = team.lower()
            # Buscar coincidencias exactas o parciales
            for pattern in patterns:
                pattern_lower = pattern.lower()
                if (pattern_lower == team_lower or 
                    pattern_lower in team_lower or 
                    team_lower in pattern_lower or
                    any(word in team_lower for word in pattern_lower.split())):
                    filtered_teams.append(team)
                    break
        
        # Eliminar duplicados y ordenar
        return sorted(list(set(filtered_teams)))
    
    def _get_demo_teams_for_division(self, division):
        """Equipos demo como fallback"""
        demo_teams = {
            'E0': ['Arsenal', 'Chelsea', 'Liverpool', 'Man City', 'Man United', 'Tottenham'],
            'SP1': ['Barcelona', 'Real Madrid', 'Atlético Madrid', 'Sevilla', 'Valencia', 'Villarreal'],
            'I1': ['Inter', 'Milan', 'Juventus', 'Roma', 'Napoli', 'Lazio'],
            'D1': ['Bayern Munich', 'Borussia Dortmund', 'RB Leipzig', 'Bayer Leverkusen'],
            'F1': ['PSG', 'Marseille', 'Lyon', 'Monaco', 'Lille'],
            'BRA': ['Flamengo', 'Palmeiras', 'Santos', 'Corinthians'],
            'ARG': ['Boca Juniors', 'River Plate', 'Racing Club', 'Independiente'],
            'MEX': ['América', 'Guadalajara', 'Cruz Azul', 'Monterrey'],
            'default': ['Equipo 1', 'Equipo 2', 'Equipo 3', 'Equipo 4', 'Equipo 5']
        }
        return demo_teams.get(division, demo_teams['default'])
    
    def get_team_suggestions(self, team_name):
        """Obtener sugerencias de equipos"""
        logger.info(f"🔍 Obteniendo sugerencias para: {team_name}")
        data = self.make_request(f'/team-suggestions/{team_name}')
        if data and data.get('success'):
            return data.get('suggestions', [])
        return []
    
    def predict_match(self, home_team, away_team, division, house_margin=0.12):
        """Obtener predicción"""
        logger.info(f"🎯 Predicción: {home_team} vs {away_team} ({division})")
        
        data = {
            "home_team": home_team,
            "away_team": away_team,
            "division": division,
            "year": 2024,
            "month": 5,
            "house_margin": house_margin
        }
        
        result = self.make_request('/predict', 'POST', data, timeout=15)
        return result

# Inicializar cliente de API
api_client = APIClient(NEURAL_API_URL)

# HTML Template (el mismo que antes con las ganancias)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>🏆 Plataforma de Apuestas - BI con IA</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * { 
            margin: 0; padding: 0; box-sizing: border-box; 
        }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; 
            padding: 15px;
            line-height: 1.6;
        }
        .container { 
            max-width: 1200px; 
            margin: 0 auto;
        }
        .header { 
            background: white; 
            padding: 20px; 
            border-radius: 12px; 
            box-shadow: 0 8px 25px rgba(0,0,0,0.1); 
            margin-bottom: 20px;
            text-align: center; 
        }
        .header h1 { 
            color: #333; 
            font-size: clamp(1.8em, 4vw, 2.5em); 
            margin-bottom: 10px; 
        }
        .header p {
            font-size: clamp(0.9em, 2.5vw, 1.1em);
            color: #666;
        }
        .grid { 
            display: grid; 
            grid-template-columns: 1fr; 
            gap: 15px; 
            margin-bottom: 20px; 
        }
        .card { 
            background: white; 
            padding: 20px; 
            border-radius: 12px; 
            box-shadow: 0 5px 15px rgba(0,0,0,0.1); 
        }
        .card h2 { 
            color: #2E86AB; 
            margin-bottom: 15px; 
            border-bottom: 2px solid #f0f0f0; 
            padding-bottom: 8px;
            font-size: clamp(1.2em, 3vw, 1.5em);
        }
        .form-group { 
            margin-bottom: 12px; 
        }
        .form-group label { 
            display: block; 
            margin-bottom: 5px; 
            font-weight: 600;
            font-size: clamp(0.9em, 2.5vw, 1em);
        }
        .form-control { 
            width: 100%; 
            padding: 10px; 
            border: 2px solid #e0e0e0; 
            border-radius: 8px; 
            font-size: clamp(0.9em, 2.5vw, 1em);
            background: white;
        }
        .btn { 
            background: #2E86AB; 
            color: white; 
            padding: 12px 25px; 
            border: none; 
            border-radius: 8px; 
            font-size: clamp(0.9em, 2.5vw, 1em);
            cursor: pointer; 
            width: 100%; 
            transition: all 0.3s ease;
            font-weight: 600;
        }
        .btn:hover { 
            background: #1a6a8a; 
            transform: translateY(-2px); 
        }
        .btn:disabled { 
            background: #cccccc; 
            cursor: not-allowed; 
            transform: none; 
        }
        .result-card { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
        }
        .metrics { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); 
            gap: 8px; 
            margin: 12px 0; 
        }
        .metric { 
            background: rgba(255,255,255,0.2); 
            padding: 12px; 
            border-radius: 8px; 
            text-align: center; 
        }
        .metric-value { 
            font-size: clamp(1.2em, 3vw, 1.5em); 
            font-weight: bold; 
            margin: 5px 0; 
        }
        .metric div:first-child {
            font-size: clamp(0.8em, 2vw, 0.9em);
            margin-bottom: 5px;
        }
        .loading { 
            text-align: center; 
            padding: 20px; 
        }
        .api-status { 
            padding: 12px; 
            border-radius: 8px; 
            margin-bottom: 15px; 
            text-align: center;
            font-weight: bold; 
            font-size: clamp(0.9em, 2.5vw, 1em);
        }
        .api-online { 
            background: #d4edda; 
            color: #155724; 
            border: 2px solid #c3e6cb; 
        }
        .api-offline { 
            background: #f8d7da; 
            color: #721c24; 
            border: 2px solid #f5c6cb; 
        }
        .api-loading { 
            background: #fff3cd; 
            color: #856404; 
            border: 2px solid #ffeaa7; 
        }
        .suggestion { 
            background: #e7f3ff; 
            padding: 4px 8px; 
            margin: 2px; 
            border-radius: 4px; 
            font-size: clamp(0.8em, 2vw, 0.85em); 
            display: inline-block; 
            cursor: pointer;
        }
        .suggestion:hover { 
            background: #d0e7ff; 
        }
        .ai-badge { 
            background: linear-gradient(45deg, #FF6B6B, #4ECDC4); 
            color: white; 
            padding: 3px 8px; 
            border-radius: 12px; 
            font-size: clamp(0.7em, 2vw, 0.8em); 
            margin-left: 8px; 
        }
        .error-message { 
            background: #f8d7da; 
            color: #721c24; 
            padding: 10px; 
            border-radius: 6px; 
            margin: 10px 0; 
            border-left: 4px solid #dc3545;
            font-size: clamp(0.9em, 2.5vw, 1em);
        }
        .success-message { 
            background: #d4edda; 
            color: #155724; 
            padding: 10px; 
            border-radius: 6px; 
            margin: 10px 0; 
            border-left: 4px solid #c3e6cb;
            font-size: clamp(0.9em, 2.5vw, 1em);
        }
        .profit-analysis {
            background: rgba(255,255,255,0.15);
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
        }
        .profit-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .profit-item:last-child {
            border-bottom: none;
        }
        .profit-outcome {
            font-weight: 600;
        }
        .profit-amount {
            font-weight: bold;
            color: #4ECDC4;
        }
        .charts-container {
            display: grid;
            grid-template-columns: 1fr;
            gap: 15px;
            margin-top: 15px;
        }
        .chart {
            background: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        }
        .system-info p {
            margin-bottom: 8px;
            font-size: clamp(0.9em, 2.5vw, 1em);
        }
        .system-info strong {
            color: #2E86AB;
        }
        
        /* Tablet */
        @media (min-width: 768px) { 
            .grid { 
                grid-template-columns: 1fr 1fr; 
                gap: 20px; 
            }
            .charts-container {
                grid-template-columns: 1fr 1fr;
            }
            body {
                padding: 20px;
            }
        }
        
        /* Desktop */
        @media (min-width: 1024px) { 
            .grid { 
                gap: 25px; 
            }
            .card { 
                padding: 25px; 
            }
            .metrics {
                gap: 10px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏆 Plataforma de Apuestas - BI</h1>
            <p>Predicciones con Inteligencia Artificial - Conectado a Red Neuronal</p>
        </div>
        
        <div id="apiStatus" class="api-status api-loading">
            🔄 Verificando conexión con Red Neuronal...
        </div>
        
        <div class="grid">
            <div class="card">
                <h2>🎯 Predicción de Partidos 
                    <span class="ai-badge">Powered by AI</span>
                </h2>
                <form id="predictionForm">
                    <div class="form-group">
                        <label>Liga:</label>
                        <select class="form-control" id="division">
                            <option value="">Cargando ligas...</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label>Equipo Local:</label>
                        <select class="form-control" id="home_team" disabled>
                            <option value="">Primero selecciona una liga</option>
                        </select>
                        <div id="homeSuggestions" style="margin-top: 5px;"></div>
                    </div>
                    
                    <div class="form-group">
                        <label>Equipo Visitante:</label>
                        <select class="form-control" id="away_team" disabled>
                            <option value="">Primero selecciona una liga</option>
                        </select>
                        <div id="awaySuggestions" style="margin-top: 5px;"></div>
                    </div>
                    
                    <div class="form-group">
                        <label>Margen de la Casa (%):</label>
                        <input type="range" class="form-control" id="house_margin" min="5" max="25" value="12" step="1">
                        <div style="display: flex; justify-content: space-between; font-size: clamp(0.8em, 2vw, 0.9em);">
                            <span>5%</span>
                            <span id="marginValue">12%</span>
                            <span>25%</span>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label>Monto Apuesta ($):</label>
                        <input type="number" class="form-control" id="bet_amount" value="100" min="10" max="1000">
                    </div>
                    
                    <button type="button" class="btn" id="predictBtn" onclick="makePrediction()" disabled>
                        🎯 Consultar Red Neuronal
                    </button>
                </form>
            </div>
            
            <div class="card result-card">
                <h2>📊 Resultados de IA</h2>
                <div id="results">
                    <div class="loading">
                        <p>🤖 Conectado a red neuronal externa</p>
                        <p>Selecciona equipos para obtener predicciones con IA</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>📈 Análisis Visual por IA</h2>
            <div class="charts-container">
                <div class="chart" id="probChart"></div>
                <div class="chart" id="oddsChart"></div>
            </div>
        </div>

        <div class="card">
            <h2>ℹ️ Información del Sistema</h2>
            <div class="system-info" id="systemInfo">
                <p><strong>Estado Red Neuronal:</strong> <span id="neuralStatus">Verificando...</span></p>
                <p><strong>Equipos disponibles:</strong> <span id="teamsCount">-</span></p>
                <p><strong>Ligas disponibles:</strong> <span id="divisionsCount">-</span></p>
                <p><strong>Versión:</strong> 3.0 - Integración con IA</p>
                <p><strong>API URL:</strong> <code id="apiUrl" style="font-size: clamp(0.8em, 2vw, 0.9em);">''' + NEURAL_API_URL + '''</code></p>
            </div>
        </div>
    </div>

    <script>
        let availableTeams = [];
        let availableDivisions = {};
        let apiOnline = false;

        // Verificar estado de la API al cargar
        async function checkAPIStatus() {
            try {
                console.log('🔍 Verificando estado de la API...');
                const response = await fetch('/api/status');
                const data = await response.json();
                console.log('📊 Estado API:', data);
                
                const statusElement = document.getElementById('apiStatus');
                if (data.api_online) {
                    statusElement.className = 'api-status api-online';
                    statusElement.innerHTML = '✅ Conectado a Red Neuronal - IA Lista para Predicciones';
                    apiOnline = true;
                } else {
                    statusElement.className = 'api-status api-offline';
                    statusElement.innerHTML = '❌ Red Neuronal no disponible';
                    apiOnline = false;
                }
                updateSystemInfo(data);
                loadDivisions();
            } catch (error) {
                console.error('❌ Error verificando estado:', error);
                document.getElementById('apiStatus').className = 'api-status api-offline';
                document.getElementById('apiStatus').innerHTML = '❌ Error de conexión';
                apiOnline = false;
                loadDivisions();
            }
        }

        function updateSystemInfo(data) {
            document.getElementById('neuralStatus').textContent = 
                data.neural_model_loaded ? '✅ Modelo Cargado' : '❌ Modelo No Disponible';
            document.getElementById('teamsCount').textContent = data.available_teams || '0';
            document.getElementById('divisionsCount').textContent = data.available_divisions || '0';
        }

        // Cargar divisiones disponibles
        async function loadDivisions() {
            try {
                console.log('🔍 Cargando divisiones...');
                const response = await fetch('/api/divisions');
                const data = await response.json();
                console.log('📊 Divisiones response:', data);
                
                const divisionSelect = document.getElementById('division');
                
                if (data.success && Object.keys(data.divisions).length > 0) {
                    availableDivisions = data.divisions;
                    divisionSelect.innerHTML = '<option value="">Selecciona una liga</option>';
                    
                    for (const [code, name] of Object.entries(availableDivisions)) {
                        const option = new Option(`${code} - ${name}`, code);
                        divisionSelect.add(option);
                    }
                    
                    divisionSelect.disabled = false;
                    console.log('✅ Divisiones cargadas:', Object.keys(availableDivisions).length);
                    
                    document.getElementById('divisionsCount').textContent = Object.keys(availableDivisions).length;
                } else {
                    console.error('❌ Error cargando divisiones:', data.error);
                    divisionSelect.innerHTML = '<option value="">Error cargando ligas</option>';
                }
            } catch (error) {
                console.error('❌ Error cargando divisiones:', error);
                document.getElementById('division').innerHTML = '<option value="">Error de conexión</option>';
            }
        }

        // Cargar equipos cuando se selecciona una división
        async function loadTeams(division) {
            const homeSelect = document.getElementById('home_team');
            const awaySelect = document.getElementById('away_team');
            const predictBtn = document.getElementById('predictBtn');
            
            homeSelect.innerHTML = '<option value="">Cargando equipos...</option>';
            awaySelect.innerHTML = '<option value="">Cargando equipos...</option>';
            homeSelect.disabled = true;
            awaySelect.disabled = true;
            predictBtn.disabled = true;
            
            document.getElementById('homeSuggestions').innerHTML = '';
            document.getElementById('awaySuggestions').innerHTML = '';
            
            try {
                console.log(`🔍 Cargando equipos para división: ${division}`);
                const response = await fetch(`/api/teams?division=${division}`);
                const data = await response.json();
                console.log('📊 Equipos response:', data);
                
                if (data.success && data.teams && data.teams.length > 0) {
                    availableTeams = data.teams;
                    
                    homeSelect.innerHTML = '<option value="">Selecciona equipo local</option>';
                    awaySelect.innerHTML = '<option value="">Selecciona equipo visitante</option>';
                    
                    availableTeams.forEach(team => {
                        const homeOption = new Option(team, team);
                        const awayOption = new Option(team, team);
                        homeSelect.add(homeOption);
                        awaySelect.add(awayOption);
                    });
                    
                    homeSelect.disabled = false;
                    awaySelect.disabled = false;
                    predictBtn.disabled = false;
                    predictBtn.textContent = '🎯 Consultar Red Neuronal';
                    
                    console.log(`✅ Equipos cargados para ${division}: ${availableTeams.length} equipos`);
                    document.getElementById('teamsCount').textContent = data.total || availableTeams.length;
                } else {
                    console.error('❌ No se encontraron equipos para esta división:', data.error);
                    homeSelect.innerHTML = '<option value="">No hay equipos para esta liga</option>';
                    awaySelect.innerHTML = '<option value="">No hay equipos para esta liga</option>';
                }
            } catch (error) {
                console.error('❌ Error cargando equipos:', error);
                homeSelect.innerHTML = '<option value="">Error de conexión</option>';
                awaySelect.innerHTML = '<option value="">Error de conexión</option>';
            }
        }

        // Resto del código JavaScript igual...
        async function makePrediction() {
            const homeTeam = document.getElementById('home_team').value;
            const awayTeam = document.getElementById('away_team').value;
            const division = document.getElementById('division').value;
            const houseMargin = document.getElementById('house_margin').value / 100;
            const betAmount = document.getElementById('bet_amount').value;
            
            if (!homeTeam || !awayTeam || !division) {
                alert('Por favor completa todos los campos');
                return;
            }
            
            if (homeTeam === awayTeam) {
                alert('Los equipos deben ser diferentes');
                return;
            }
            
            const predictBtn = document.getElementById('predictBtn');
            predictBtn.disabled = true;
            predictBtn.textContent = '🔄 Consultando IA...';
            
            document.getElementById('results').innerHTML = `
                <div class="loading">
                    <p>🧠 Consultando red neuronal...</p>
                    <p><strong>${homeTeam}</strong> vs <strong>${awayTeam}</strong></p>
                    <p>🔍 Analizando patrones con IA...</p>
                </div>
            `;
            
            try {
                console.log('🎯 Enviando solicitud de predicción...');
                const response = await fetch('/api/predict', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        home_team: homeTeam,
                        away_team: awayTeam,
                        division: division,
                        house_margin: houseMargin,
                        bet_amount: parseFloat(betAmount)
                    })
                });
                
                const result = await response.json();
                console.log('📊 Resultado predicción:', result);
                
                if (result.success) {
                    displayResults(result);
                    updateCharts(result);
                } else {
                    document.getElementById('results').innerHTML = `
                        <div class="error-message">
                            <p>❌ Error: ${result.error || 'Error en la predicción'}</p>
                            ${result.suggestions ? `<p>💡 Sugerencias: ${result.suggestions.join(', ')}</p>` : ''}
                        </div>
                    `;
                }
            } catch (error) {
                console.error('❌ Error en predicción:', error);
                document.getElementById('results').innerHTML = `
                    <div class="error-message">
                        <p>❌ Error de conexión con la IA</p>
                        <p>Intenta nuevamente en unos momentos</p>
                    </div>
                `;
            } finally {
                predictBtn.disabled = false;
                predictBtn.textContent = '🎯 Consultar Red Neuronal';
            }
        }
        
        function displayResults(result) {
            const probHome = (result.probabilities.home_win * 100).toFixed(1);
            const probDraw = (result.probabilities.draw * 100).toFixed(1);
            const probAway = (result.probabilities.away_win * 100).toFixed(1);
            const betAmount = result.bet_amount || 100;
            
            // Calcular ganancias potenciales
            const profitHome = (betAmount * result.odds.home_win - betAmount).toFixed(2);
            const profitDraw = (betAmount * result.odds.draw - betAmount).toFixed(2);
            const profitAway = (betAmount * result.odds.away_win - betAmount).toFixed(2);
            
            document.getElementById('results').innerHTML = `
                <div class="success-message">
                    <p>✅ Predicción generada por IA</p>
                </div>
                <h3 style="margin-bottom: 10px; font-size: clamp(1.1em, 3vw, 1.3em);">${result.home_team} vs ${result.away_team}</h3>
                <p style="margin-bottom: 15px;"><strong>${result.division_full_name || result.division}</strong></p>
                <p style="margin-bottom: 15px; font-style: italic;"><em>🤖 ${result.message || 'Predicción por Red Neuronal'}</em></p>
                
                <div class="metrics">
                    <div class="metric">
                        <div>🏠 ${result.home_team}</div>
                        <div class="metric-value">${probHome}%</div>
                        <div style="font-size: clamp(0.8em, 2vw, 0.9em);">Cuota: ${result.odds.home_win.toFixed(2)}</div>
                    </div>
                    <div class="metric">
                        <div>⚖️ Empate</div>
                        <div class="metric-value">${probDraw}%</div>
                        <div style="font-size: clamp(0.8em, 2vw, 0.9em);">Cuota: ${result.odds.draw.toFixed(2)}</div>
                    </div>
                    <div class="metric">
                        <div>✈️ ${result.away_team}</div>
                        <div class="metric-value">${probAway}%</div>
                        <div style="font-size: clamp(0.8em, 2vw, 0.9em);">Cuota: ${result.odds.away_win.toFixed(2)}</div>
                    </div>
                </div>
                
                <div class="profit-analysis">
                    <p style="margin-bottom: 10px; font-weight: bold; text-align: center;">💰 Ganancias Potenciales (Apuesta: $${betAmount})</p>
                    <div class="profit-item">
                        <span class="profit-outcome">🏠 ${result.home_team} Gana:</span>
                        <span class="profit-amount">+$${profitHome}</span>
                    </div>
                    <div class="profit-item">
                        <span class="profit-outcome">⚖️ Empate:</span>
                        <span class="profit-amount">+$${profitDraw}</span>
                    </div>
                    <div class="profit-item">
                        <span class="profit-outcome">✈️ ${result.away_team} Gana:</span>
                        <span class="profit-amount">+$${profitAway}</span>
                    </div>
                </div>
                
                <div style="margin-top: 15px; padding: 12px; background: rgba(255,255,255,0.2); border-radius: 8px;">
                    <p style="margin-bottom: 8px; font-weight: bold;">📈 Análisis Financiero:</p>
                    <p style="margin-bottom: 5px;">💰 Margen de la Casa: ${result.actual_margin?.toFixed(2) || '0.00'}%</p>
                    <p style="margin-bottom: 5px;">💵 Margen configurado: ${(result.house_margin * 100).toFixed(1)}%</p>
                    <p style="margin-bottom: 5px;">🎯 House Edge: ${result.house_edge?.toFixed(2) || '0.00'}%</p>
                </div>
            `;
        }
        
        function updateCharts(result) {
            // Gráfico de probabilidades - Responsivo
            Plotly.newPlot('probChart', [{
                values: [result.probabilities.home_win, result.probabilities.draw, result.probabilities.away_win],
                labels: [`${result.home_team} Gana`, 'Empate', `${result.away_team} Gana`],
                type: 'pie',
                hole: 0.4,
                marker: {
                    colors: ['#FF6B6B', '#4ECDC4', '#45B7D1']
                },
                textinfo: 'label+percent',
                insidetextorientation: 'radial',
                textfont: {
                    size: Math.min(14, window.innerWidth / 30)
                }
            }], {
                title: {
                    text: 'Probabilidades de Resultado',
                    font: { size: Math.min(16, window.innerWidth / 25) }
                },
                height: Math.min(350, window.innerHeight * 0.4),
                showlegend: false,
                margin: { t: 40, b: 20, l: 20, r: 20 }
            });
            
            // Gráfico de cuotas - Responsivo
            Plotly.newPlot('oddsChart', [{
                x: [`${result.home_team}`, 'Empate', `${result.away_team}`],
                y: [result.odds.home_win, result.odds.draw, result.odds.away_win],
                type: 'bar',
                marker: {
                    color: ['#FF6B6B', '#4ECDC4', '#45B7D1']
                },
                text: [result.odds.home_win.toFixed(2), result.odds.draw.toFixed(2), result.odds.away_win.toFixed(2)],
                textposition: 'auto',
                textfont: {
                    size: Math.min(12, window.innerWidth / 35)
                }
            }], {
                title: {
                    text: 'Cuotas de Apuesta',
                    font: { size: Math.min(16, window.innerWidth / 25) }
                },
                yaxis: { 
                    title: {
                        text: 'Cuota',
                        font: { size: Math.min(14, window.innerWidth / 30) }
                    }
                },
                xaxis: { 
                    tickangle: -45,
                    tickfont: { size: Math.min(10, window.innerWidth / 40) }
                },
                height: Math.min(350, window.innerHeight * 0.4),
                margin: { t: 40, b: 60, l: 60, r: 20 }
            });
        }

        // Event listeners
        document.getElementById('division').addEventListener('change', function() {
            if (this.value) {
                loadTeams(this.value);
            } else {
                // Limpiar equipos si no hay división seleccionada
                const homeSelect = document.getElementById('home_team');
                const awaySelect = document.getElementById('away_team');
                const predictBtn = document.getElementById('predictBtn');
                
                homeSelect.innerHTML = '<option value="">Primero selecciona una liga</option>';
                awaySelect.innerHTML = '<option value="">Primero selecciona una liga</option>';
                homeSelect.disabled = true;
                awaySelect.disabled = true;
                predictBtn.disabled = true;
            }
        });

        document.getElementById('house_margin').addEventListener('input', function() {
            document.getElementById('marginValue').textContent = this.value + '%';
        });

        // Inicializar
        document.addEventListener('DOMContentLoaded', function() {
            console.log('🚀 Inicializando aplicación...');
            checkAPIStatus();
            document.getElementById('marginValue').textContent = document.getElementById('house_margin').value + '%';
        });
    </script>
</body>
</html>
'''

# Las rutas de la API permanecen igual...
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def api_status():
    """Verificar estado de la conexión con la API de IA"""
    try:
        logger.info("🔍 Verificando estado de la API de red neuronal...")
        api_online, health_data = api_client.health_check()
        
        response_data = {
            'success': True,
            'api_online': api_online,
            'neural_model_loaded': health_data.get('model_loaded', False) if health_data else False,
            'neural_api_url': NEURAL_API_URL,
            'available_teams': health_data.get('available_teams_count', 0) if health_data else 0,
            'available_divisions': health_data.get('available_divisions_count', 0) if health_data else 0,
        }
        
        logger.info(f"📊 Estado API: Online={api_online}, Modelo={response_data['neural_model_loaded']}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"❌ Error checking API status: {e}")
        return jsonify({
            'success': False,
            'api_online': False,
            'neural_model_loaded': False,
            'error': str(e)
        })

@app.route('/api/divisions')
def api_divisions():
    """Obtener divisiones disponibles desde la API de IA"""
    try:
        logger.info("🔍 Obteniendo divisiones...")
        divisions = api_client.get_divisions()
        
        if divisions:
            logger.info(f"✅ Divisiones obtenidas: {len(divisions)}")
            return jsonify({
                'success': True,
                'divisions': divisions,
                'total': len(divisions)
            })
        else:
            logger.error("❌ No se pudieron obtener las divisiones")
            return jsonify({
                'success': False,
                'error': 'No se pudieron cargar las divisiones',
                'divisions': {},
                'total': 0
            })
            
    except Exception as e:
        logger.error(f"❌ Error getting divisions: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'divisions': {},
            'total': 0
        })

@app.route('/api/teams')
def api_teams():
    """Obtener equipos FILTRADOS por división"""
    division = request.args.get('division', '')
    try:
        logger.info(f"🔍 Obteniendo equipos para división: {division}")
        teams = api_client.get_teams_for_division(division)
        
        if teams is not None:
            logger.info(f"✅ Equipos filtrados para {division}: {len(teams)} equipos")
            return jsonify({
                'success': True,
                'teams': teams,
                'total': len(teams),
                'division': division
            })
        else:
            logger.error("❌ Error obteniendo equipos")
            return jsonify({
                'success': False,
                'error': 'Error obteniendo equipos',
                'teams': [],
                'total': 0
            })
            
    except Exception as e:
        logger.error(f"❌ Error getting teams: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'teams': [],
            'total': 0
        })

# Las demás rutas permanecen igual...
@app.route('/api/team-suggestions')
def api_team_suggestions():
    """Obtener sugerencias de equipos"""
    team_name = request.args.get('team_name', '')
    try:
        logger.info(f"🔍 Obteniendo sugerencias para: {team_name}")
        suggestions = api_client.get_team_suggestions(team_name)
        return jsonify({
            'success': True,
            'team_name': team_name,
            'suggestions': suggestions,
            'total': len(suggestions)
        })
    except Exception as e:
        logger.error(f"❌ Error getting team suggestions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/predict', methods=['POST'])
def api_predict():
    """Obtener predicción desde la API de IA"""
    try:
        data = request.json
        logger.info(f"🎯 Recibida solicitud de predicción: {data}")
        
        # Validaciones básicas
        if not data.get('home_team') or not data.get('away_team') or not data.get('division'):
            error_msg = 'Faltan datos requeridos: home_team, away_team, division'
            logger.error(f"❌ {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg
            })
        
        if data['home_team'] == data['away_team']:
            error_msg = 'Los equipos deben ser diferentes'
            logger.error(f"❌ {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg
            })
        
        # Obtener predicción de la API de red neuronal
        house_margin = data.get('house_margin', 0.12)
        prediction = api_client.predict_match(
            data['home_team'],
            data['away_team'], 
            data['division'],
            house_margin
        )
        
        if prediction:
            prediction['success'] = True
            prediction['bet_amount'] = float(data.get('bet_amount', 100))
            return jsonify(prediction)
        else:
            return jsonify({
                'success': False, 
                'error': 'La red neuronal no está disponible en este momento'
            })
            
    except Exception as e:
        logger.error(f"Error in prediction: {e}")
        return jsonify({
            'success': False, 
            'error': f'Error interno: {str(e)}'
        })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy', 
        'neural_api_connected': api_client.health_check()[0],
        'neural_api_url': NEURAL_API_URL
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🚀 Iniciando servidor Flask en puerto {port}")
    app.run(host="0.0.0.0", port=port, debug=False)