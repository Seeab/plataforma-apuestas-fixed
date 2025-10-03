# app.py - APP FLASK ACTUALIZADA PARA RENDER
import requests
from flask import Flask, request, jsonify, render_template_string
import os
import logging
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
            'User-Agent': 'BettingApp-Render/2.0'
        })
    
    def health_check(self):
        """Verificar estado de la API"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return True, data
            return False, None
        except Exception as e:
            logger.error(f"❌ Error en health check: {e}")
            return False, None
    
    def predict_match(self, home_team: str, away_team: str, division: str, house_margin: float = 0.12):
        """Obtener predicción desde la API de red neuronal"""
        try:
            data = {
                "home_team": home_team,
                "away_team": away_team,
                "division": division,
                "house_margin": house_margin
            }
            
            logger.info(f"🎯 Solicitando predicción: {home_team} vs {away_team} ({division})")
            
            response = self.session.post(
                f"{self.base_url}/predict", 
                json=data,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Predicción recibida exitosamente")
                return result
            else:
                error_msg = f"Error {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get('detail', error_msg)
                except:
                    pass
                logger.error(f"❌ Error en predicción: {error_msg}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("⏰ Timeout en la solicitud de predicción")
            return None
        except Exception as e:
            logger.error(f"❌ Error llamando a la API: {e}")
            return None
    
    def get_available_teams(self, division: Optional[str] = None):
        """Obtener equipos disponibles desde la API"""
        try:
            url = f"{self.base_url}/teams"
            if division:
                url += f"?division={division}"
                
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('teams', [])
            return []
        except Exception as e:
            logger.error(f"❌ Error obteniendo equipos: {e}")
            return []
    
    def get_available_divisions(self):
        """Obtener divisiones disponibles desde la API"""
        try:
            response = self.session.get(f"{self.base_url}/divisions", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('divisions', {})
            return {}
        except Exception as e:
            logger.error(f"❌ Error obteniendo divisiones: {e}")
            return {}
    
    def get_team_suggestions(self, team_name: str):
        """Obtener sugerencias de equipos"""
        try:
            response = self.session.get(f"{self.base_url}/team-suggestions/{team_name}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('suggestions', [])
            return []
        except Exception as e:
            logger.error(f"❌ Error obteniendo sugerencias: {e}")
            return []

# Inicializar cliente de API
api_client = APIClient(NEURAL_API_URL)

# HTML Template actualizado
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
                const response = await fetch('/api/status');
                const data = await response.json();
                
                const statusElement = document.getElementById('apiStatus');
                if (data.api_online && data.neural_model_loaded) {
                    statusElement.className = 'api-status api-online';
                    statusElement.innerHTML = '✅ Conectado a Red Neuronal - IA Lista para Predicciones';
                    apiOnline = true;
                    neuralModelLoaded = true;
                    updateSystemInfo(data);
                } else if (data.api_online) {
                    statusElement.className = 'api-status api-loading';
                    statusElement.innerHTML = '⚠️ API Conectada - Modelo de IA no cargado';
                    apiOnline = true;
                    neuralModelLoaded = false;
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
                document.getElementById('apiStatus').className = 'api-status api-offline';
                document.getElementById('apiStatus').innerHTML = '❌ Error de conexión - Modo demo';
                apiOnline = false;
                neuralModelLoaded = false;
                loadDivisions(); // Intentar cargar igual
            }
        }

        function updateSystemInfo(data) {
            document.getElementById('neuralStatus').textContent = 
                data.neural_model_loaded ? '✅ Modelo Cargado' : '❌ Modelo No Disponible';
            document.getElementById('teamsCount').textContent = data.available_teams || '-';
            document.getElementById('divisionsCount').textContent = data.available_divisions || '-';
            document.getElementById('apiUrl').textContent = data.neural_api_url || ''' + NEURAL_API_URL + ''';
        }

        // Cargar divisiones disponibles
        async function loadDivisions() {
            try {
                const response = await fetch('/api/divisions');
                const data = await response.json();
                
                if (data.success) {
                    availableDivisions = data.divisions;
                    const divisionSelect = document.getElementById('division');
                    divisionSelect.innerHTML = '<option value="">Selecciona una liga</option>';
                    
                    for (const [code, name] of Object.entries(availableDivisions)) {
                        const option = new Option(`${code} - ${name}`, code);
                        divisionSelect.add(option);
                    }
                    
                    divisionSelect.disabled = false;
                }
            } catch (error) {
                console.error('Error cargando divisiones:', error);
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
            
            // Limpiar sugerencias
            document.getElementById('homeSuggestions').innerHTML = '';
            document.getElementById('awaySuggestions').innerHTML = '';
            
            try {
                const response = await fetch(`/api/teams?division=${division}`);
                const data = await response.json();
                
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
                    predictBtn.disabled = !neuralModelLoaded;
                    
                    // Actualizar texto del botón según disponibilidad
                    predictBtn.textContent = neuralModelLoaded ? 
                        '🎯 Consultar Red Neuronal' : '❌ IA No Disponible';
                    
                }
            } catch (error) {
                console.error('Error cargando equipos:', error);
                homeSelect.innerHTML = '<option value="">Error cargando equipos</option>';
                awaySelect.innerHTML = '<option value="">Error cargando equipos</option>';
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
            
            if (!neuralModelLoaded) {
                alert('El modelo de IA no está disponible. Usando modo demo.');
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
                
                if (result.success) {
                    displayResults(result);
                    updateCharts(result);
                } else {
                    document.getElementById('results').innerHTML = `
                        <div class="loading">
                            <p>❌ Error: ${result.error || 'Error en la predicción'}</p>
                            ${result.suggestions ? `<p>💡 Sugerencias: ${result.suggestions.join(', ')}</p>` : ''}
                        </div>
                    `;
                }
            } catch (error) {
                document.getElementById('results').innerHTML = `
                    <div class="loading">
                        <p>❌ Error de conexión con la IA</p>
                        <p>Intenta nuevamente en unos momentos</p>
                    </div>
                `;
            } finally {
                predictBtn.disabled = !neuralModelLoaded;
                predictBtn.textContent = neuralModelLoaded ? '🎯 Consultar Red Neuronal' : '❌ IA No Disponible';
            }
        }
        
        function displayResults(result) {
            const probHome = (result.probabilities.home_win * 100).toFixed(1);
            const probDraw = (result.probabilities.draw * 100).toFixed(1);
            const probAway = (result.probabilities.away_win * 100).toFixed(1);
            
            document.getElementById('results').innerHTML = `
                <h3>${result.home_team} vs ${result.away_team}</h3>
                <p><strong>${result.division_full_name}</strong></p>
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
                    <p>💰 Margen de la Casa: ${result.actual_margin.toFixed(2)}%</p>
                    <p>🎯 House Edge: ${result.house_edge.toFixed(2)}%</p>
                    <p>💵 Margen configurado: ${(result.house_margin * 100).toFixed(1)}%</p>
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
        api_online, health_data = api_client.health_check()
        
        response_data = {
            'success': True,
            'api_online': api_online,
            'neural_model_loaded': health_data.get('model_loaded', False) if health_data else False,
            'neural_api_url': NEURAL_API_URL,
            'available_teams': health_data.get('available_teams_count', 0) if health_data else 0,
            'available_divisions': health_data.get('available_divisions_count', 0) if health_data else 0,
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error checking API status: {e}")
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
        divisions = api_client.get_available_divisions()
        if divisions:
            return jsonify({
                'success': True,
                'divisions': divisions,
                'total': len(divisions)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No se pudieron cargar las divisiones'
            })
    except Exception as e:
        logger.error(f"Error getting divisions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/teams')
def api_teams():
    """Obtener equipos disponibles desde la API de IA"""
    division = request.args.get('division', '')
    try:
        teams = api_client.get_available_teams(division)
        return jsonify({
            'success': True,
            'teams': teams,
            'total': len(teams),
            'division': division
        })
    except Exception as e:
        logger.error(f"Error getting teams: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/team-suggestions')
def api_team_suggestions():
    """Obtener sugerencias de equipos"""
    team_name = request.args.get('team_name', '')
    try:
        suggestions = api_client.get_team_suggestions(team_name)
        return jsonify({
            'success': True,
            'team_name': team_name,
            'suggestions': suggestions,
            'total': len(suggestions)
        })
    except Exception as e:
        logger.error(f"Error getting team suggestions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/predict', methods=['POST'])
def api_predict():
    """Obtener predicción desde la API de IA"""
    try:
        data = request.json
        
        # Validaciones básicas
        if not data.get('home_team') or not data.get('away_team') or not data.get('division'):
            return jsonify({
                'success': False,
                'error': 'Faltan datos requeridos: home_team, away_team, division'
            })
        
        if data['home_team'] == data['away_team']:
            return jsonify({
                'success': False,
                'error': 'Los equipos deben ser diferentes'
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
        'neural_api_connected': api_client.health_check()[0]
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🚀 Iniciando servidor Flask en puerto {port}")
    app.run(host="0.0.0.0", port=port, debug=False)