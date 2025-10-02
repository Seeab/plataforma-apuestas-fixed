# app.py - VERSIÓN CON FILTRADO POR LIGA
import pandas as pd
import numpy as np
from flask import Flask, request, jsonify, render_template_string
import warnings
import os

warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

print("🚀 Iniciando plataforma optimizada para Render...")

# =============================================================================
# 1. CLASE CON FILTRADO POR LIGA
# =============================================================================
class BettingPredictor:
    def __init__(self):
        # Mapeo completo de ligas y sus equipos
        self.league_teams = {
            'SP1': [  # La Liga (España)
                'Real Madrid', 'Barcelona', 'Atletico Madrid', 'Sevilla',
                'Valencia', 'Villarreal', 'Real Betis', 'Athletic Bilbao',
                'Real Sociedad', 'Celta Vigo'
            ],
            'E0': [  # Premier League (Inglaterra)
                'Manchester United', 'Liverpool', 'Manchester City', 'Chelsea',
                'Arsenal', 'Tottenham', 'Newcastle', 'Brighton',
                'West Ham', 'Aston Villa'
            ],
            'I1': [  # Serie A (Italia)
                'Juventus', 'AC Milan', 'Inter Milan', 'Napoli',
                'Roma', 'Lazio', 'Atalanta', 'Fiorentina',
                'Bologna', 'Torino'
            ],
            'D1': [  # Bundesliga (Alemania)
                'Bayern Munich', 'Borussia Dortmund', 'RB Leipzig', 'Bayer Leverkusen',
                'Eintracht Frankfurt', 'Wolfsburg', 'Borussia Monchengladbach',
                'Hertha Berlin', 'Hoffenheim', 'Mainz'
            ],
            'F1': [  # Ligue 1 (Francia)
                'PSG', 'Marseille', 'Lyon', 'Monaco',
                'Lille', 'Rennes', 'Nice', 'Lens',
                'Nantes', 'Toulouse'
            ]
        }
        
        self.league_mapping = {
            'SP1': 'La Liga (España)',
            'E0': 'Premier League (Inglaterra)', 
            'I1': 'Serie A (Italia)',
            'D1': 'Bundesliga (Alemania)',
            'F1': 'Ligue 1 (Francia)'
        }

    def get_division_full_name(self, division_abbr):
        return self.league_mapping.get(division_abbr, division_abbr)

    def get_teams_by_league(self, league):
        """Obtiene equipos filtrados por liga"""
        return self.league_teams.get(league, [])

    def get_all_teams(self):
        """Obtiene todos los equipos únicos (para inicialización)"""
        all_teams = set()
        for teams in self.league_teams.values():
            all_teams.update(teams)
        return sorted(list(all_teams))

    def predict_match(self, home_team, away_team, division, house_margin=0.12):
        """Predicción simplificada para demo"""
        # Verificar que los equipos pertenezcan a la liga seleccionada
        league_teams = self.get_teams_by_league(division)
        if home_team not in league_teams or away_team not in league_teams:
            return None

        # Simular probabilidades basadas en equipos conocidos
        base_probs = self._calculate_base_probabilities(home_team, away_team)
        
        # Aplicar pequeño ruido para variedad
        noise = np.random.normal(0, 0.05, 3)
        probabilities = np.clip(base_probs + noise, 0.1, 0.8)
        probabilities = probabilities / probabilities.sum()  # Normalizar

        # Calcular cuotas con margen
        fair_odds = 1 / probabilities
        odds = fair_odds * (1 - house_margin)

        # Verificación del margen real
        implied_prob_sum = sum(1/odd for odd in odds)
        actual_margin = (implied_prob_sum - 1) * 100

        return {
            'probabilities': {
                'home_win': float(probabilities[0]),
                'draw': float(probabilities[1]),
                'away_win': float(probabilities[2])
            },
            'odds': {
                'home_win': float(odds[0]),
                'draw': float(odds[1]),
                'away_win': float(odds[2])
            },
            'division_full_name': self.get_division_full_name(division),
            'house_margin': house_margin,
            'actual_margin': float(actual_margin)
        }

    def _calculate_base_probabilities(self, home_team, away_team):
        """Calcula probabilidades base según equipos"""
        # Equipos fuertes por liga (para demo más realista)
        strong_teams = {
            'SP1': ['Real Madrid', 'Barcelona', 'Atletico Madrid'],
            'E0': ['Manchester City', 'Liverpool', 'Arsenal'],
            'I1': ['Inter Milan', 'AC Milan', 'Juventus'],
            'D1': ['Bayern Munich', 'Borussia Dortmund'],
            'F1': ['PSG']
        }
        
        # Determinar qué liga pertenecen los equipos
        home_league = None
        away_league = None
        
        for league, teams in self.league_teams.items():
            if home_team in teams:
                home_league = league
            if away_team in teams:
                away_league = league
        
        # Si son de la misma liga, usar lógica de esa liga
        if home_league == away_league:
            strong_in_league = strong_teams.get(home_league, [])
            
            if home_team in strong_in_league and away_team not in strong_in_league:
                return np.array([0.60, 0.25, 0.15])  # Local fuerte favorito
            elif away_team in strong_in_league and home_team not in strong_in_league:
                return np.array([0.25, 0.25, 0.50])  # Visitante fuerte favorito
            elif home_team in strong_in_league and away_team in strong_in_league:
                return np.array([0.40, 0.30, 0.30])  # Partido de titanes
            else:
                return np.array([0.45, 0.30, 0.25])  # Partido equilibrado
        else:
            # Partido entre ligas diferentes (ej: Champions League)
            return np.array([0.35, 0.30, 0.35])  # Más incierto

# =============================================================================
# 2. APLICACIÓN FLASK ACTUALIZADA
# =============================================================================
app = Flask(__name__)
predictor = BettingPredictor()

# HTML Template actualizado con JavaScript para filtrado
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>🏆 Plataforma de Apuestas - BI</title>
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
        }
        .btn:hover { background: #1a6a8a; }
        .btn:disabled { background: #cccccc; cursor: not-allowed; }
        .result-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .metrics { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin: 15px 0; }
        .metric { background: rgba(255,255,255,0.2); padding: 15px; border-radius: 10px; text-align: center; }
        .metric-value { font-size: 1.5em; font-weight: bold; margin: 5px 0; }
        .loading { text-align: center; padding: 20px; }
        .league-info { 
            background: #e8f4f8; padding: 10px; border-radius: 5px; 
            margin-bottom: 15px; border-left: 4px solid #2E86AB;
        }
        @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏆 Plataforma de Apuestas - BI</h1>
            <p>Predicciones en Tiempo Real + Business Intelligence</p>
        </div>
        
        <div class="grid">
            <div class="card">
                <h2>🎯 Predicción de Partidos</h2>
                <form id="predictionForm">
                    <div class="form-group">
                        <label>Liga:</label>
                        <select class="form-control" id="division" onchange="updateTeams()">
                            <option value="SP1">La Liga (España)</option>
                            <option value="E0">Premier League (Inglaterra)</option>
                            <option value="I1">Serie A (Italia)</option>
                            <option value="D1">Bundesliga (Alemania)</option>
                            <option value="F1">Ligue 1 (Francia)</option>
                        </select>
                    </div>
                    
                    <div class="league-info" id="leagueInfo">
                        <strong id="currentLeague">La Liga (España)</strong> - 
                        <span id="teamCount">10 equipos disponibles</span>
                    </div>
                    
                    <div class="form-group">
                        <label>Equipo Local:</label>
                        <select class="form-control" id="home_team">
                            <!-- equipos se cargan dinámicamente -->
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Equipo Visitante:</label>
                        <select class="form-control" id="away_team">
                            <!-- equipos se cargan dinámicamente -->
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Monto Apuesta ($):</label>
                        <input type="number" class="form-control" id="bet_amount" value="100" min="10" max="1000">
                    </div>
                    <button type="button" class="btn" id="predictBtn" onclick="makePrediction()">
                        🎯 Calcular Predicción
                    </button>
                </form>
            </div>
            
            <div class="card result-card">
                <h2>📊 Resultados</h2>
                <div id="results">
                    <div class="loading">
                        <p>Selecciona una liga y equipos para calcular predicción</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>📈 Análisis Visual</h2>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div id="probChart"></div>
                <div id="oddsChart"></div>
            </div>
        </div>

        <div class="card">
            <h2>ℹ️ Información del Sistema</h2>
            <div id="systemInfo">
                <p><strong>Estado:</strong> <span id="status">Conectado</span></p>
                <p><strong>Ligas disponibles:</strong> 5</p>
                <p><strong>Equipos por liga:</strong> 10</p>
                <p><strong>Versión:</strong> 2.1 - Con filtrado por liga</p>
            </div>
        </div>
    </div>

    <script>
        // Datos de equipos por liga
        const leagueTeams = {
            'SP1': ['Real Madrid', 'Barcelona', 'Atletico Madrid', 'Sevilla', 'Valencia', 'Villarreal', 'Real Betis', 'Athletic Bilbao', 'Real Sociedad', 'Celta Vigo'],
            'E0': ['Manchester United', 'Liverpool', 'Manchester City', 'Chelsea', 'Arsenal', 'Tottenham', 'Newcastle', 'Brighton', 'West Ham', 'Aston Villa'],
            'I1': ['Juventus', 'AC Milan', 'Inter Milan', 'Napoli', 'Roma', 'Lazio', 'Atalanta', 'Fiorentina', 'Bologna', 'Torino'],
            'D1': ['Bayern Munich', 'Borussia Dortmund', 'RB Leipzig', 'Bayer Leverkusen', 'Eintracht Frankfurt', 'Wolfsburg', 'Borussia Monchengladbach', 'Hertha Berlin', 'Hoffenheim', 'Mainz'],
            'F1': ['PSG', 'Marseille', 'Lyon', 'Monaco', 'Lille', 'Rennes', 'Nice', 'Lens', 'Nantes', 'Toulouse']
        };

        const leagueNames = {
            'SP1': 'La Liga (España)',
            'E0': 'Premier League (Inglaterra)',
            'I1': 'Serie A (Italia)',
            'D1': 'Bundesliga (Alemania)',
            'F1': 'Ligue 1 (Francia)'
        };

        function updateTeams() {
            const leagueSelect = document.getElementById('division');
            const homeSelect = document.getElementById('home_team');
            const awaySelect = document.getElementById('away_team');
            const leagueInfo = document.getElementById('leagueInfo');
            const currentLeague = document.getElementById('currentLeague');
            const teamCount = document.getElementById('teamCount');
            
            const selectedLeague = leagueSelect.value;
            const teams = leagueTeams[selectedLeague] || [];
            const leagueName = leagueNames[selectedLeague];
            
            // Actualizar información de la liga
            currentLeague.textContent = leagueName;
            teamCount.textContent = `${teams.length} equipos disponibles`;
            
            // Limpiar selects
            homeSelect.innerHTML = '';
            awaySelect.innerHTML = '';
            
            // Llenar con equipos de la liga seleccionada
            teams.forEach(team => {
                const homeOption = new Option(team, team);
                const awayOption = new Option(team, team);
                homeSelect.add(homeOption);
                awaySelect.add(awayOption);
            });
            
            // Resetear resultados
            document.getElementById('results').innerHTML = `
                <div class="loading">
                    <p>Selecciona equipos diferentes y haz click en Calcular Predicción</p>
                </div>
            `;
            
            // Resetear gráficos
            document.getElementById('probChart').innerHTML = '';
            document.getElementById('oddsChart').innerHTML = '';
        }

        function makePrediction() {
            const homeTeam = document.getElementById('home_team').value;
            const awayTeam = document.getElementById('away_team').value;
            const league = document.getElementById('division').value;
            
            if (homeTeam === awayTeam) {
                alert('⚠️ Por favor selecciona equipos diferentes');
                return;
            }

            const data = {
                home_team: homeTeam,
                away_team: awayTeam,
                division: league,
                bet_amount: document.getElementById('bet_amount').value
            };
            
            document.getElementById('results').innerHTML = `
                <div class="loading">
                    <p>🔄 Calculando predicción para ${homeTeam} vs ${awayTeam}...</p>
                </div>
            `;
            
            // Deshabilitar botón temporalmente
            const predictBtn = document.getElementById('predictBtn');
            predictBtn.disabled = true;
            predictBtn.textContent = '🔄 Calculando...';
            
            fetch('/api/predict', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    displayResults(result);
                    updateCharts(result);
                } else {
                    document.getElementById('results').innerHTML = `
                        <div class="loading">
                            <p>❌ Error: ${result.error || 'Error en la predicción'}</p>
                        </div>
                    `;
                }
            })
            .catch(error => {
                document.getElementById('results').innerHTML = `
                    <div class="loading">
                        <p>❌ Error de conexión</p>
                    </div>
                `;
            })
            .finally(() => {
                // Re-habilitar botón
                predictBtn.disabled = false;
                predictBtn.textContent = '🎯 Calcular Predicción';
            });
        }
        
        function displayResults(result) {
            const probHome = (result.probabilities.home_win * 100).toFixed(1);
            const probDraw = (result.probabilities.draw * 100).toFixed(1);
            const probAway = (result.probabilities.away_win * 100).toFixed(1);
            
            document.getElementById('results').innerHTML = `
                <h3>${result.home_team} vs ${result.away_team}</h3>
                <p><strong>${result.division_full_name}</strong></p>
                
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
                    <p><strong>📈 Análisis Financiero:</strong></p>
                    <p>💰 Margen de la Casa: ${result.actual_margin.toFixed(2)}%</p>
                    <p>💵 Ganancia Esperada: $${(result.bet_amount * result.actual_margin / 100).toFixed(2)}</p>
                    <p>🎯 House Edge: ${result.house_edge.toFixed(2)}%</p>
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
                }
            }], {
                title: 'Probabilidades de Resultado',
                height: 300,
                showlegend: true
            });
            
            // Gráfico de cuotas
            Plotly.newPlot('oddsChart', [{
                x: [`${result.home_team}`, 'Empate', `${result.away_team}`],
                y: [result.odds.home_win, result.odds.draw, result.odds.away_win],
                type: 'bar',
                marker: {
                    color: ['#FF6B6B', '#4ECDC4', '#45B7D1']
                }
            }], {
                title: 'Cuotas de Apuesta',
                yaxis: { title: 'Cuota' },
                height: 300
            });
        }

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

        // Inicializar al cargar la página
        document.addEventListener('DOMContentLoaded', function() {
            updateTeams();
        });
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/predict', methods=['POST'])
def api_predict():
    try:
        data = request.json
        
        # Validar que los equipos sean diferentes
        if data['home_team'] == data['away_team']:
            return jsonify({
                'success': False, 
                'error': 'Los equipos deben ser diferentes'
            })
        
        prediction = predictor.predict_match(
            data['home_team'],
            data['away_team'],
            data['division']
        )
        
        if prediction:
            implied_prob_sum = sum(1/odd for odd in prediction['odds'].values())
            house_edge = (implied_prob_sum - 1) * 100
            
            return jsonify({
                'success': True,
                'home_team': data['home_team'],
                'away_team': data['away_team'],
                'division_full_name': prediction['division_full_name'],
                'probabilities': prediction['probabilities'],
                'odds': prediction['odds'],
                'actual_margin': prediction.get('actual_margin', 0),
                'house_edge': float(house_edge),
                'bet_amount': float(data.get('bet_amount', 100))
            })
        else:
            return jsonify({
                'success': False, 
                'error': 'Los equipos seleccionados no pertenecen a esta liga'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/teams/<league>')
def api_teams(league):
    """API para obtener equipos por liga"""
    try:
        teams = predictor.get_teams_by_league(league)
        return jsonify(teams)
    except Exception as e:
        return jsonify([])

@app.route('/api/status')
def status():
    return jsonify({
        'status': 'online',
        'version': '2.1-with-league-filter',
        'leagues_available': len(predictor.league_mapping),
        'environment': 'production'
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': str(pd.Timestamp.now())})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"✅ Servidor iniciado en puerto {port}")
    app.run(host="0.0.0.0", port=port, debug=False)