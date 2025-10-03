# app.py - APP FLASK COMPLETA CON MEJORAS Y DEBUGGING
import requests
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import os
import logging
import time
from typing import Dict, List, Optional

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuración - URL de tu API de red neuronal
NEURAL_API_URL = os.environ.get('NEURAL_API_URL', 'https://neural-api-predictor.onrender.com')
logger.info(f"🔗 Conectando a API de red neuronal: {NEURAL_API_URL}")

class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'BettingApp-Flask/3.0'
        })
        
    def health_check(self):
        """Verificar estado de la API - USANDO ENDPOINT /health"""
        try:
            logger.info(f"🔍 Probando health check en {self.base_url}/health")
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            logger.info(f"📊 Health check status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Health check exitoso: {data}")
                return True, data
            else:
                logger.warning(f"❌ Health check falló: {response.status_code}")
                # Fallback al endpoint raíz
                return self._fallback_health_check()
                    
        except Exception as e:
            logger.error(f"❌ Error en health check: {e}")
            return self._fallback_health_check()
    
    def _fallback_health_check(self):
        """Fallback si /health no funciona"""
        try:
            logger.info("🔄 Intentando fallback al endpoint raíz...")
            response = self.session.get(f"{self.base_url}/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Fallback exitoso")
                return True, data
            return False, None
        except Exception as e:
            logger.error(f"❌ Fallback también falló: {e}")
            return False, None
    
    def get_available_divisions(self):
        """Obtener divisiones disponibles desde la API"""
        try:
            url = f"{self.base_url}/divisions"
            logger.info(f"🔍 Obteniendo divisiones desde: {url}")
            response = self.session.get(url, timeout=15)
            logger.info(f"📊 Divisions status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"📋 Divisions response: {data}")
                
                if data.get('success'):
                    divisions = data.get('divisions', {})
                    logger.info(f"✅ Divisiones obtenidas: {len(divisions)}")
                    return divisions
                else:
                    logger.error(f"❌ API retornó success: false - {data.get('error')}")
                    return self._get_demo_divisions()
            else:
                logger.error(f"❌ Error HTTP obteniendo divisions: {response.status_code}")
                logger.error(f"📄 Response text: {response.text}")
                return self._get_demo_divisions()
        except Exception as e:
            logger.error(f"❌ Error obteniendo divisiones: {e}")
            return self._get_demo_divisions()
    
    def get_available_teams(self, division: Optional[str] = None):
        """Obtener equipos disponibles desde la API - CON DEBUG"""
        try:
            url = f"{self.base_url}/teams"
            if division:
                url += f"?division={division}"
                
            logger.info(f"🔍 Obteniendo equipos desde: {url}")
            response = self.session.get(url, timeout=15)
            logger.info(f"📊 Teams status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"📋 Teams response keys: {list(data.keys())}")
                
                if data.get('success'):
                    teams = data.get('teams', [])
                    logger.info(f"✅ Equipos obtenidos: {len(teams)}")
                    if teams:
                        logger.info(f"📋 Primeros 5 equipos: {teams[:5]}")
                        logger.info(f"📋 Últimos 5 equipos: {teams[-5:]}")
                    return teams
                else:
                    logger.error(f"❌ API retornó success: false - {data.get('error')}")
                    return self._get_demo_teams(division)
            else:
                logger.error(f"❌ Error HTTP obteniendo teams: {response.status_code}")
                logger.error(f"📄 Response text: {response.text}")
                return self._get_demo_teams(division)
        except Exception as e:
            logger.error(f"❌ Error obteniendo equipos: {e}")
            return self._get_demo_teams(division)

    def predict_match(self, home_team: str, away_team: str, division: str, house_margin: float = 0.12):
        """Obtener predicción desde la API de red neuronal - CORREGIDO"""
        try:
            data = {
                "home_team": home_team,
                "away_team": away_team,
                "division": division,
                "year": 2024,
                "month": 5,
                "house_margin": house_margin
            }
            
            logger.info(f"🎯 Solicitando predicción: {home_team} vs {away_team} ({division})")
            logger.info(f"📤 Datos enviados: {data}")
            
            response = self.session.post(
                f"{self.base_url}/predict", 
                json=data,
                timeout=30
            )
            
            logger.info(f"📨 Predict response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Predicción recibida exitosamente")
                return result
            else:
                error_msg = f"Error {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get('detail', error_data.get('error', error_msg))
                    logger.error(f"❌ Error en predicción: {error_msg}")
                    
                    # Si es 400 Bad Request, mostrar sugerencias
                    if response.status_code == 400 and 'Sugerencias' in error_msg:
                        logger.info(f"💡 La API sugiere: {error_msg}")
                        
                except:
                    logger.error(f"❌ Error en predicción: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error llamando a la API: {e}")
            return None
    
    def get_team_suggestions(self, team_name: str):
        """Obtener sugerencias de equipos"""
        try:
            url = f"{self.base_url}/team-suggestions/{team_name}"
            logger.info(f"🔍 Obteniendo sugerencias desde: {url}")
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('suggestions', [])
            return []
        except Exception as e:
            logger.error(f"❌ Error obteniendo sugerencias: {e}")
            return []
    
    def _get_demo_divisions(self):
        """Divisiones de demo como fallback"""
        return {
            'E2': 'English League One', 
            'DEN': 'Liga Dinamarca',
            'F2': 'Ligue 2 (Francia)', 
            'EC': 'National League',
            'I1': 'Serie A (Italia)'
        }
    
    def _get_demo_teams(self, division: Optional[str] = None):
        """Equipos de demo como fallback"""
        demo_teams = {
            'E2': ['Leeds', 'Southampton', 'West Brom', 'Norwich', 'Middlesbrough'],
            'DEN': ['Copenhagen', 'Midtjylland', 'Brondby', 'Aarhus', 'Vejle'],
            'F2': ['Saint-Etienne', 'Metz', 'Bordeaux', 'Grenoble', 'Paris FC'],
            'EC': ['Barcelona SC', 'Emelec', 'Independiente', 'LDU Quito', 'Aucas'],
            'I1': ['Inter', 'Milan', 'Juventus', 'Roma', 'Napoli']
        }
        
        if division and division in demo_teams:
            return demo_teams[division]
        else:
            all_teams = []
            for teams in demo_teams.values():
                all_teams.extend(teams)
            return list(set(all_teams))

# Inicializar cliente de API
api_client = APIClient(NEURAL_API_URL)

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>🏆 Plataforma de Apuestas - BI con IA</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; padding: 20px; 
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { 
            background: white; padding: 30px; border-radius: 15px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.1); margin-bottom: 20px;
            text-align: center; 
        }
        .header h1 { color: #333; font-size: 2.5em; margin-bottom: 10px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
        .card { 
            background: white; padding: 25px; border-radius: 15px; 
            box-shadow: 0 5px 15px rgba(0,0,0,0.1); 
        }
        .card h2 { color: #2E86AB; margin-bottom: 20px; border-bottom: 2px solid #f0f0f0; padding-bottom: 10px; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: 600; }
        .form-control { 
            width: 100%; padding: 10px; border: 2px solid #e0e0e0; border-radius: 5px; 
            font-size: 16px; 
        }
        .btn { 
            background: #2E86AB; color: white; padding: 12px 30px; border: none; 
            border-radius: 5px; font-size: 16px; cursor: pointer; width: 100%; 
            transition: all 0.3s ease;
        }
        .btn:hover { background: #1a6a8a; transform: translateY(-2px); }
        .btn:disabled { background: #cccccc; cursor: not-allowed; transform: none; }
        .btn-success { background: #28a745; }
        .btn-success:hover { background: #218838; }
        .result-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .metrics { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin: 15px 0; }
        .metric { background: rgba(255,255,255,0.2); padding: 15px; border-radius: 10px; text-align: center; }
        .metric-value { font-size: 1.5em; font-weight: bold; margin: 5px 0; }
        .loading { text-align: center; padding: 20px; }
        .api-status { 
            padding: 15px; border-radius: 10px; margin-bottom: 20px; text-align: center;
            font-weight: bold; font-size: 1.1em;
        }
        .api-online { background: #d4edda; color: #155724; border: 2px solid #c3e6cb; }
        .api-offline { background: #f8d7da; color: #721c24; border: 2px solid #f5c6cb; }
        .api-loading { background: #fff3cd; color: #856404; border: 2px solid #ffeaa7; }
        .suggestion { 
            background: #e7f3ff; padding: 5px 10px; margin: 2px; border-radius: 3px; 
            font-size: 0.9em; display: inline-block; cursor: pointer;
        }
        .suggestion:hover { background: #d0e7ff; }
        .ai-badge { 
            background: linear-gradient(45deg, #FF6B6B, #4ECDC4); 
            color: white; padding: 3px 8px; border-radius: 12px; 
            font-size: 0.8em; margin-left: 10px; 
        }
        .error-message { 
            background: #f8d7da; color: #721c24; padding: 10px; border-radius: 5px; 
            margin: 10px 0; border-left: 4px solid #dc3545;
        }
        .success-message { 
            background: #d4edda; color: #155724; padding: 10px; border-radius: 5px; 
            margin: 10px 0; border-left: 4px solid #c3e6cb;
        }
        .debug-info {
            background: #e9ecef; padding: 10px; border-radius: 5px; 
            margin: 10px 0; border-left: 4px solid #6c757d;
            font-size: 0.9em;
        }
        @media (max-width: 768px) { 
            .grid { grid-template-columns: 1fr; } 
            .metrics { grid-template-columns: 1fr; }
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
                        <div style="display: flex; justify-content: space-between;">
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

                <!-- Botones de debug -->
                <div style="margin-top: 20px; display: flex; gap: 10px;">
                    <button type="button" class="btn" style="background: #6c757d;" onclick="testDebugEndpoints()">
                        🐛 Probar Debug
                    </button>
                    <button type="button" class="btn" style="background: #17a2b8;" onclick="loadSampleData()">
                        🧪 Datos de Prueba
                    </button>
                </div>
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
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div id="probChart"></div>
                <div id="oddsChart"></div>
            </div>
        </div>

        <div class="card">
            <h2>ℹ️ Información del Sistema</h2>
            <div id="systemInfo">
                <p><strong>Estado Red Neuronal:</strong> <span id="neuralStatus">Verificando...</span></p>
                <p><strong>Equipos disponibles:</strong> <span id="teamsCount">-</span></p>
                <p><strong>Ligas disponibles:</strong> <span id="divisionsCount">-</span></p>
                <p><strong>Versión:</strong> 3.0 - Integración con IA</p>
                <p><strong>API URL:</strong> <code id="apiUrl">''' + NEURAL_API_URL + '''</code></p>
            </div>
        </div>
    </div>

    <script>
        let availableTeams = [];
        let availableDivisions = {};
        let apiOnline = false;
        let neuralModelLoaded = false;

        // Verificar estado de la API al cargar
        async function checkAPIStatus() {
            try {
                console.log('🔍 Verificando estado de la API...');
                const response = await fetch('/api/status');
                const data = await response.json();
                console.log('📊 Estado API:', data);
                
                const statusElement = document.getElementById('apiStatus');
                if (data.api_online && data.neural_model_loaded) {
                    statusElement.className = 'api-status api-online';
                    statusElement.innerHTML = '✅ Conectado a Red Neuronal - IA Lista para Predicciones';
                    apiOnline = true;
                    neuralModelLoaded = true;
                    updateSystemInfo(data);
                } else if (data.api_online) {
                    statusElement.className = 'api-status api-online';
                    statusElement.innerHTML = '✅ API Conectada - Cargando datos...';
                    apiOnline = true;
                    neuralModelLoaded = true;
                    updateSystemInfo(data);
                } else {
                    statusElement.className = 'api-status api-offline';
                    statusElement.innerHTML = '❌ Red Neuronal no disponible - Usando modo demo';
                    apiOnline = false;
                    neuralModelLoaded = false;
                    updateSystemInfo(data);
                }
                loadDivisions();
            } catch (error) {
                console.error('❌ Error verificando estado:', error);
                document.getElementById('apiStatus').className = 'api-status api-offline';
                document.getElementById('apiStatus').innerHTML = '❌ Error de conexión - Modo demo activado';
                apiOnline = false;
                neuralModelLoaded = false;
                loadDivisions();
            }
        }

        function updateSystemInfo(data) {
            document.getElementById('neuralStatus').textContent = 
                data.neural_model_loaded ? '✅ Modelo Cargado' : '🔄 Verificando...';
            document.getElementById('teamsCount').textContent = data.available_teams || 'Cargando...';
            document.getElementById('divisionsCount').textContent = data.available_divisions || 'Cargando...';
            document.getElementById('apiUrl').textContent = data.neural_api_url || ''' + NEURAL_API_URL + ''';
        }

        // Cargar divisiones disponibles
        async function loadDivisions() {
            try {
                console.log('🔍 Cargando divisiones...');
                const response = await fetch('/api/divisions');
                const data = await response.json();
                console.log('📊 Divisiones:', data);
                
                if (data.success) {
                    availableDivisions = data.divisions;
                    const divisionSelect = document.getElementById('division');
                    divisionSelect.innerHTML = '<option value="">Selecciona una liga</option>';
                    
                    for (const [code, name] of Object.entries(availableDivisions)) {
                        const option = new Option(`${code} - ${name}`, code);
                        divisionSelect.add(option);
                    }
                    
                    divisionSelect.disabled = false;
                    console.log('✅ Divisiones cargadas:', Object.keys(availableDivisions).length);
                    
                    // Actualizar contador en UI
                    document.getElementById('divisionsCount').textContent = Object.keys(availableDivisions).length;
                } else {
                    console.error('❌ Error cargando divisiones:', data.error);
                    document.getElementById('division').innerHTML = '<option value="">Error cargando ligas - Usando demo</option>';
                    // Cargar divisiones demo
                    loadDemoDivisions();
                }
            } catch (error) {
                console.error('❌ Error cargando divisiones:', error);
                document.getElementById('division').innerHTML = '<option value="">Error de conexión - Usando demo</option>';
                loadDemoDivisions();
            }
        }

        function loadDemoDivisions() {
            // Divisiones de demo
            availableDivisions = {
                'E2': 'English League One', 
                'DEN': 'Liga Dinamarca',
                'F2': 'Ligue 2 (Francia)', 
                'EC': 'National League',
                'I1': 'Serie A (Italia)'
            };
            
            const divisionSelect = document.getElementById('division');
            divisionSelect.innerHTML = '<option value="">Selecciona una liga (Modo Demo)</option>';
            
            for (const [code, name] of Object.entries(availableDivisions)) {
                const option = new Option(`${code} - ${name}`, code);
                divisionSelect.add(option);
            }
            
            divisionSelect.disabled = false;
            document.getElementById('divisionsCount').textContent = Object.keys(availableDivisions).length;
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
            
            // Limpiar sugerencias
            document.getElementById('homeSuggestions').innerHTML = '';
            document.getElementById('awaySuggestions').innerHTML = '';
            
            try {
                console.log(`🔍 Cargando equipos para división: ${division}`);
                const response = await fetch(`/api/teams?division=${division}`);
                const data = await response.json();
                console.log('📊 Equipos:', data);
                
                if (data.success) {
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
                    
                    // Actualizar texto del botón
                    predictBtn.textContent = '🎯 Consultar Red Neuronal';
                    
                    console.log(`✅ Equipos cargados: ${availableTeams.length} equipos`);
                    
                    // Actualizar contador en UI
                    document.getElementById('teamsCount').textContent = data.total || availableTeams.length;
                } else {
                    console.error('❌ Error cargando equipos:', data.error);
                    homeSelect.innerHTML = '<option value="">Error cargando equipos</option>';
                    awaySelect.innerHTML = '<option value="">Error cargando equipos</option>';
                }
            } catch (error) {
                console.error('❌ Error cargando equipos:', error);
                homeSelect.innerHTML = '<option value="">Error de conexión</option>';
                awaySelect.innerHTML = '<option value="">Error de conexión</option>';
            }
        }

        // Buscar sugerencias de equipos
        async function searchTeamSuggestions(teamName, type) {
            if (teamName.length < 3) {
                document.getElementById(type + 'Suggestions').innerHTML = '';
                return;
            }
            
            try {
                const response = await fetch(`/api/team-suggestions?team_name=${encodeURIComponent(teamName)}`);
                const data = await response.json();
                
                if (data.success && data.suggestions.length > 0) {
                    const suggestionsHtml = data.suggestions.map(team => 
                        `<div class="suggestion" onclick="selectSuggestion('${team}', '${type}')">${team}</div>`
                    ).join('');
                    document.getElementById(type + 'Suggestions').innerHTML = suggestionsHtml;
                } else {
                    document.getElementById(type + 'Suggestions').innerHTML = '';
                }
            } catch (error) {
                console.error('Error buscando sugerencias:', error);
            }
        }

        function selectSuggestion(team, type) {
            document.getElementById(type + '_team').value = team;
            document.getElementById(type + 'Suggestions').innerHTML = '';
        }

        // Realizar predicción
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
            
            document.getElementById('results').innerHTML = `
                <div class="success-message">
                    <p>✅ Predicción generada por IA</p>
                </div>
                <h3>${result.home_team} vs ${result.away_team}</h3>
                <p><strong>${result.division_full_name || result.division}</strong></p>
                <p><em>🤖 ${result.message || 'Predicción por Red Neuronal'}</em></p>
                
                <div class="metrics">
                    <div class="metric">
                        <div>🏠 ${result.home_team}</div>
                        <div class="metric-value">${probHome}%</div>
                        <div>Cuota: ${result.odds.home_win.toFixed(2)}</div>
                    </div>
                    <div class="metric">
                        <div>⚖️ Empate</div>
                        <div class="metric-value">${probDraw}%</div>
                        <div>Cuota: ${result.odds.draw.toFixed(2)}</div>
                    </div>
                    <div class="metric">
                        <div>✈️ ${result.away_team}</div>
                        <div class="metric-value">${probAway}%</div>
                        <div>Cuota: ${result.odds.away_win.toFixed(2)}</div>
                    </div>
                </div>
                
                <div style="margin-top: 15px; padding: 15px; background: rgba(255,255,255,0.2); border-radius: 10px;">
                    <p><strong>📈 Análisis Financiero por IA:</strong></p>
                    <p>💰 Margen de la Casa: ${(result.actual_margin * 100).toFixed(2)}%</p>
                    <p>🎯 House Edge: ${(result.house_edge * 100).toFixed(2)}%</p>
                    <p>💵 Margen configurado: ${(result.house_margin * 100).toFixed(1)}%</p>
                    ${result.bet_amount ? `<p>💸 Apuesta: $${result.bet_amount}</p>` : ''}
                </div>
            `;
        }
        
        function updateCharts(result) {
            // Gráfico de probabilidades
            Plotly.newPlot('probChart', [{
                values: [result.probabilities.home_win, result.probabilities.draw, result.probabilities.away_win],
                labels: [`${result.home_team} Gana`, 'Empate', `${result.away_team} Gana`],
                type: 'pie',
                hole: 0.4,
                marker: {
                    colors: ['#FF6B6B', '#4ECDC4', '#45B7D1']
                },
                textinfo: 'label+percent',
                insidetextorientation: 'radial'
            }], {
                title: 'Probabilidades de Resultado - IA',
                height: 300,
                showlegend: false,
                annotations: [{
                    text: 'IA',
                    x: 0.5, y: 0.5, xref: 'paper', yref: 'paper',
                    showarrow: false, font: { size: 14, color: 'white' }
                }]
            });
            
            // Gráfico de cuotas
            Plotly.newPlot('oddsChart', [{
                x: [`${result.home_team}`, 'Empate', `${result.away_team}`],
                y: [result.odds.home_win, result.odds.draw, result.odds.away_win],
                type: 'bar',
                marker: {
                    color: ['#FF6B6B', '#4ECDC4', '#45B7D1']
                },
                text: [result.odds.home_win.toFixed(2), result.odds.draw.toFixed(2), result.odds.away_win.toFixed(2)],
                textposition: 'auto'
            }], {
                title: 'Cuotas de Apuesta - IA',
                yaxis: { title: 'Cuota' },
                xaxis: { tickangle: -45 },
                height: 300
            });
        }

        // Funciones de debug
        async function testDebugEndpoints() {
            try {
                console.log('🐛 Probando endpoints de debug...');
                
                const debugResponse = await fetch('/api/debug-teams');
                const debugData = await debugResponse.json();
                console.log('📊 Debug teams:', debugData);
                
                const testResponse = await fetch('/api/test-prediction');
                const testData = await testResponse.json();
                console.log('📊 Test prediction:', testData);
                
                // Mostrar resultados en la UI
                document.getElementById('results').innerHTML = `
                    <div class="debug-info">
                        <h3>🐛 Resultados Debug</h3>
                        <p><strong>Equipos encontrados:</strong> ${debugData.teams_count || 0}</p>
                        <p><strong>Divisiones encontradas:</strong> ${debugData.divisions_count || 0}</p>
                        <p><strong>Test predicción:</strong> ${testData.success ? '✅ Éxito' : '❌ Falló'}</p>
                        ${debugData.sample_teams ? `<p><strong>Equipos de muestra:</strong> ${debugData.sample_teams.join(', ')}</p>` : ''}
                        ${testData.error ? `<p><strong>Error:</strong> ${testData.error}</p>` : ''}
                    </div>
                `;
                
            } catch (error) {
                console.error('❌ Error en debug:', error);
                alert('Error en pruebas de debug: ' + error.message);
            }
        }

        function loadSampleData() {
            // Cargar datos de prueba conocidos
            document.getElementById('division').value = 'SP1';
            loadTeams('SP1');
            
            setTimeout(() => {
                // Buscar equipos comunes
                const homeSelect = document.getElementById('home_team');
                const awaySelect = document.getElementById('away_team');
                
                // Intentar encontrar equipos conocidos
                const commonTeams = ['Barcelona', 'Real Madrid', 'Atletico Madrid', 'Sevilla'];
                
                for (let team of commonTeams) {
                    for (let i = 0; i < homeSelect.options.length; i++) {
                        if (homeSelect.options[i].text.includes(team)) {
                            homeSelect.value = homeSelect.options[i].value;
                            break;
                        }
                    }
                    for (let i = 0; i < awaySelect.options.length; i++) {
                        if (awaySelect.options[i].text.includes(team) && awaySelect.options[i].value !== homeSelect.value) {
                            awaySelect.value = awaySelect.options[i].value;
                            break;
                        }
                    }
                }
                
                document.getElementById('results').innerHTML = `
                    <div class="debug-info">
                        <h3>🧪 Datos de Prueba Cargados</h3>
                        <p><strong>Liga:</strong> SP1 - La Liga (España)</p>
                        <p><strong>Equipo Local:</strong> ${homeSelect.value || 'No encontrado'}</p>
                        <p><strong>Equipo Visitante:</strong> ${awaySelect.value || 'No encontrado'}</p>
                        <p>Ahora puedes hacer clic en "Consultar Red Neuronal"</p>
                    </div>
                `;
            }, 1000);
        }

        // Event listeners
        document.getElementById('division').addEventListener('change', function() {
            if (this.value) {
                loadTeams(this.value);
            }
        });

        document.getElementById('house_margin').addEventListener('input', function() {
            document.getElementById('marginValue').textContent = this.value + '%';
        });

        document.getElementById('home_team').addEventListener('input', function() {
            searchTeamSuggestions(this.value, 'home');
        });

        document.getElementById('away_team').addEventListener('input', function() {
            searchTeamSuggestions(this.value, 'away');
        });

        // Prevenir que se seleccionen los mismos equipos
        document.getElementById('home_team').addEventListener('change', function() {
            const awaySelect = document.getElementById('away_team');
            const homeValue = this.value;
            
            if (awaySelect.value === homeValue) {
                const options = Array.from(awaySelect.options);
                const differentOption = options.find(opt => opt.value !== homeValue);
                if (differentOption) {
                    awaySelect.value = differentOption.value;
                }
            }
        });

        document.getElementById('away_team').addEventListener('change', function() {
            const homeSelect = document.getElementById('home_team');
            const awayValue = this.value;
            
            if (homeSelect.value === awayValue) {
                const options = Array.from(homeSelect.options);
                const differentOption = options.find(opt => opt.value !== awayValue);
                if (differentOption) {
                    homeSelect.value = differentOption.value;
                }
            }
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
            'neural_model_loaded': health_data.get('model_loaded', True) if health_data else True,
            'neural_api_url': NEURAL_API_URL,
            'available_teams': health_data.get('available_teams_count', 774) if health_data else 774,
            'available_divisions': health_data.get('available_divisions_count', 38) if health_data else 38,
        }
        
        logger.info(f"📊 Estado API: {response_data}")
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
        divisions = api_client.get_available_divisions()
        if divisions:
            logger.info(f"✅ Divisiones obtenidas: {len(divisions)}")
            return jsonify({
                'success': True,
                'divisions': divisions,
                'total': len(divisions)
            })
        else:
            logger.error("❌ No se pudieron cargar las divisiones")
            return jsonify({
                'success': False,
                'error': 'No se pudieron cargar las divisiones'
            })
    except Exception as e:
        logger.error(f"❌ Error getting divisions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/teams')
def api_teams():
    """Obtener equipos disponibles desde la API de IA"""
    division = request.args.get('division', '')
    try:
        logger.info(f"🔍 Obteniendo equipos para división: {division}")
        teams = api_client.get_available_teams(division)
        if teams is not None:
            logger.info(f"✅ Equipos obtenidos: {len(teams)} equipos")
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
                'error': 'Error obteniendo equipos'
            })
    except Exception as e:
        logger.error(f"❌ Error getting teams: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

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

# Nuevos endpoints de debug
@app.route('/api/debug-teams')
def debug_teams():
    """Endpoint de debug para ver equipos disponibles"""
    try:
        teams = api_client.get_available_teams()
        divisions = api_client.get_available_divisions()
        
        return jsonify({
            'success': True,
            'teams_count': len(teams) if teams else 0,
            'divisions_count': len(divisions) if divisions else 0,
            'sample_teams': teams[:10] if teams else [],
            'sample_divisions': list(divisions.items())[:5] if divisions else []
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/test-prediction')
def test_prediction():
    """Endpoint de test para probar predicción con datos conocidos"""
    try:
        # Probar con equipos que sabemos que existen
        test_data = {
            "home_team": "Barcelona",
            "away_team": "Real Madrid", 
            "division": "SP1",
            "house_margin": 0.12
        }
        
        logger.info(f"🧪 Test prediction con: {test_data}")
        prediction = api_client.predict_match(**test_data)
        
        return jsonify({
            'success': prediction is not None,
            'prediction': prediction,
            'test_data': test_data
        })
    except Exception as e:
        return jsonify({'error': str(e)})

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
    app.run(host="0.0.0.0", port=port, debug=True)