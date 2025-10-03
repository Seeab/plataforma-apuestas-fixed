# api_neural_network.py - DESPLIEGA EN UN NUEVO SERVICIO
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow import keras
from sklearn.preprocessing import StandardScaler, LabelEncoder
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import uvicorn
import pickle
import os
import json
from typing import Dict, List, Optional

# Configuración para evitar logs excesivos
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
tf.get_logger().setLevel('ERROR')

# Modelos de datos para la API
class PredictionRequest(BaseModel):
    home_team: str
    away_team: str
    division: str
    year: int = 2024
    month: int = 5
    house_margin: float = 0.12

class PredictionResponse(BaseModel):
    success: bool
    home_team: str
    away_team: str
    division_full_name: str
    probabilities: Dict[str, float]
    odds: Dict[str, float]
    house_margin: float
    actual_margin: float
    house_edge: float
    message: str = ""

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    available_teams_count: int
    available_divisions_count: int
    api_version: str

class TeamsResponse(BaseModel):
    success: bool
    teams: List[str]
    total: int
    division: str = ""

class DivisionsResponse(BaseModel):
    success: bool
    divisions: Dict[str, str]
    total: int

# Cargar el modelo entrenado y preprocesadores
class NeuralNetworkAPI:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.label_encoder_teams = None
        self.label_encoder_divisions = None
        self.team_mapping = {}
        self.division_mapping = {}
        self.available_teams = []
        self.is_loaded = False
        
        self.league_mapping = {
            'ARG': 'Primera Division Argentina',
            'AUT': 'Liga de Austria',
            'B1': 'Belgian Pro League',
            'BRA': 'Brasileirao',
            'CHN': 'Liga China',
            'D1': 'Bundesliga (Alemania)',
            'D2': 'Bundesliga 2 (Alemania)',
            'DEN': 'Liga Dinamarca',
            'E0': 'Premier League (Inglaterra)',
            'E1': 'English League Championship',
            'E2': 'English League One',
            'E3': 'English League Two',
            'EC': 'National League (5ta División Inglaterra)',
            'F1': 'Ligue 1 (Francia)',
            'F2': 'Ligue 2 (Francia)',
            'FIN': 'Liga Finlandia',
            'G1': 'Liga Grecia',
            'I1': 'Serie A (Italia)',
            'I2': 'Serie B (Italia)',
            'IRL': 'Liga Irlanda',
            'JAP': 'Liga Japonesa',
            'MEX': 'Liga MX (México)',
            'N1': 'Eredivisie (Países Bajos)',
            'NOR': 'Liga Noruega',
            'P1': 'Primeira Liga (Portugal)',
            'POL': 'Liga Polonia',
            'ROM': 'Liga Rumania',
            'RUS': 'Liga Rusa',
            'SC0': 'Scottish Premiership',
            'SC1': 'Segunda Division Escocia',
            'SC2': 'Tercera Division Escocia',
            'SC3': 'Cuarta Division Escocia',
            'SP1': 'La Liga (España)',
            'SP2': 'La Liga 2 (España)',
            'SUI': 'Liga de Suiza',
            'SWE': 'Liga de Suecia',
            'T1': 'Liga de Turquia',
            'USA': 'Major League Soccer (USA/Canadá)'
        }
    
    def load_model(self, model_path='model.h5', scaler_path='model_scaler.pkl', 
                   encoders_path='model_encoders.pkl'):
        """Carga el modelo y preprocesadores entrenados"""
        try:
            print("🚀 Cargando modelo de red neuronal...")
            print(f"📁 Buscando archivos:")
            print(f"   • Modelo: {model_path}")
            print(f"   • Scaler: {scaler_path}")
            print(f"   • Encoders: {encoders_path}")
            
            # Verificar que los archivos existan
            if not os.path.exists(model_path):
                print(f"❌ Archivo de modelo no encontrado: {model_path}")
                print(f"   Archivos en directorio: {os.listdir('.')}")
                return False
            if not os.path.exists(scaler_path):
                print(f"❌ Archivo de scaler no encontrado: {scaler_path}")
                print(f"   Archivos en directorio: {os.listdir('.')}")
                return False
            if not os.path.exists(encoders_path):
                print(f"❌ Archivo de encoders no encontrado: {encoders_path}")
                print(f"   Archivos en directorio: {os.listdir('.')}")
                return False
            
            print("✅ Todos los archivos encontrados")
            
            # Cargar modelo
            print("🧠 Cargando modelo de red neuronal...")
            self.model = keras.models.load_model(model_path)
            print("✅ Modelo de red neuronal cargado")
            
            # Cargar scaler
            print("⚖️ Cargando scaler...")
            with open(scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)
            print("✅ Scaler cargado")
            
            # Cargar encoders y mapeos
            print("🔤 Cargando encoders...")
            with open(encoders_path, 'rb') as f:
                encoders_data = pickle.load(f)
                self.label_encoder_teams = encoders_data['label_encoder_teams']
                self.label_encoder_divisions = encoders_data['label_encoder_divisions']
                self.team_mapping = encoders_data['team_mapping']
                self.division_mapping = encoders_data['division_mapping']
                self.available_teams = encoders_data['available_teams']
            
            print("✅ Encoders y mapeos cargados")
            self.is_loaded = True
            
            print(f"📊 Resumen de datos cargados:")
            print(f"   • Equipos disponibles: {len(self.available_teams)}")
            print(f"   • Divisiones disponibles: {len(self.division_mapping)}")
            if self.available_teams:
                print(f"   • Primeros 5 equipos: {self.available_teams[:5]}")
            if self.division_mapping:
                print(f"   • Primeras 5 divisiones: {list(self.division_mapping.keys())[:5]}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error cargando el modelo: {str(e)}")
            import traceback
            traceback.print_exc()
            self.is_loaded = False
            return False
    
    def find_similar_teams(self, team_name):
        """Encuentra equipos con nombres similares"""
        if not self.available_teams:
            return []
        team_name_lower = team_name.lower()
        similar_teams = [team for team in self.available_teams if team_name_lower in team.lower()]
        return similar_teams
    
    def get_division_full_name(self, division_abbr):
        return self.league_mapping.get(division_abbr, division_abbr)
    
    def get_teams_by_division(self, division):
        """Obtiene equipos filtrados por división"""
        if not self.is_loaded:
            return []
        
        # Por simplicidad, devolvemos todos los equipos
        # En una implementación real filtrarías por división
        return self.available_teams
    
    def predict(self, home_team, away_team, division, year=2024, month=5, house_margin=0.12):
        """Realiza predicción usando el modelo cargado"""
        if not self.is_loaded:
            raise HTTPException(status_code=503, detail="Modelo no cargado. Servicio no disponible.")
        
        # Verificar equipos
        if home_team not in self.team_mapping:
            similar = self.find_similar_teams(home_team)
            error_msg = f"Equipo local '{home_team}' no encontrado"
            if similar:
                error_msg += f". Sugerencias: {', '.join(similar[:3])}"
            raise HTTPException(status_code=400, detail=error_msg)
        
        if away_team not in self.team_mapping:
            similar = self.find_similar_teams(away_team)
            error_msg = f"Equipo visitante '{away_team}' no encontrado"
            if similar:
                error_msg += f". Sugerencias: {', '.join(similar[:3])}"
            raise HTTPException(status_code=400, detail=error_msg)
        
        if division not in self.division_mapping:
            available_divs = list(self.division_mapping.keys())
            raise HTTPException(
                status_code=400, 
                detail=f"División '{division}' no encontrada. Divisiones disponibles: {', '.join(available_divs[:10])}"
            )
        
        # Preparar características para predicción
        try:
            features = np.array([[
                year, month,
                12, 10,  # HomeShots, AwayShots promedio
                5, 4,    # HomeTarget, AwayTarget promedio  
                12, 14,  # HomeFouls, AwayFouls promedio
                6, 5,    # HomeCorners, AwayCorners promedio
                2, 2,    # HomeYellow, AwayYellow promedio
                self.team_mapping[home_team],
                self.team_mapping[away_team],
                self.division_mapping[division]
            ]])
            
            # Escalar y predecir
            features_scaled = self.scaler.transform(features)
            probabilities = self.model.predict(features_scaled, verbose=0)[0]
            
            # Calcular cuotas
            fair_odds = 1 / probabilities
            odds = fair_odds * (1 - house_margin)
            
            # Calcular márgenes
            implied_prob_sum = sum(1/odd for odd in odds)
            actual_margin = (implied_prob_sum - 1) * 100
            house_edge = actual_margin
            
            return {
                'home_team': home_team,
                'away_team': away_team,
                'division_full_name': self.get_division_full_name(division),
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
                'house_margin': house_margin,
                'actual_margin': float(actual_margin),
                'house_edge': float(house_edge)
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error en la predicción: {str(e)}")

# Instanciar el predictor
predictor_api = NeuralNetworkAPI()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Iniciando API de Red Neuronal...")
    
    # Listar archivos disponibles
    import glob
    model_files = glob.glob("*.h5") + glob.glob("*.pkl")
    print(f"📄 Archivos encontrados: {model_files}")
    
    # Cargar con los nombres correctos
    success = predictor_api.load_model(
        model_path='model.h5',
        scaler_path='model_scaler.pkl', 
        encoders_path='model_encoders.pkl'
    )
    
    if success:
        print("🎉 API lista para recibir solicitudes")
    else:
        print("❌ API iniciada en modo limitado (sin modelo)")
    
    yield
    # Shutdown
    print("🔴 Apagando API de Red Neuronal...")

app = FastAPI(
    title="Neural Network Betting Predictor API",
    description="API para predicciones de partidos de fútbol usando Red Neuronal",
    version="1.0.0",
    lifespan=lifespan
)

# Configurar CORS para permitir requests desde Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Neural Network Betting Predictor API", 
        "status": "online",
        "model_loaded": predictor_api.is_loaded,
        "endpoints": {
            "health": "/health",
            "predict": "/predict (POST)",
            "teams": "/teams",
            "divisions": "/divisions"
        }
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        model_loaded=predictor_api.is_loaded,
        available_teams_count=len(predictor_api.available_teams) if predictor_api.is_loaded else 0,
        available_divisions_count=len(predictor_api.division_mapping) if predictor_api.is_loaded else 0,
        api_version="1.0.0"
    )

@app.post("/predict", response_model=PredictionResponse)
async def predict_match(request: PredictionRequest):
    """Endpoint para predecir partidos"""
    try:
        result = predictor_api.predict(
            home_team=request.home_team,
            away_team=request.away_team,
            division=request.division,
            year=request.year,
            month=request.month,
            house_margin=request.house_margin
        )
        
        return PredictionResponse(
            success=True,
            home_team=result['home_team'],
            away_team=result['away_team'],
            division_full_name=result['division_full_name'],
            probabilities=result['probabilities'],
            odds=result['odds'],
            house_margin=result['house_margin'],
            actual_margin=result['actual_margin'],
            house_edge=result['house_edge'],
            message="Predicción realizada exitosamente por la red neuronal"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@app.get("/teams", response_model=TeamsResponse)
async def get_available_teams(division: Optional[str] = None):
    """Obtener lista de equipos disponibles"""
    if not predictor_api.is_loaded:
        raise HTTPException(status_code=503, detail="Modelo no cargado")
    
    teams = predictor_api.get_teams_by_division(division) if division else predictor_api.available_teams
    
    return TeamsResponse(
        success=True,
        teams=sorted(teams),
        total=len(teams),
        division=division or "all"
    )

@app.get("/divisions", response_model=DivisionsResponse)
async def get_available_divisions():
    """Obtener lista de divisiones disponibles"""
    if not predictor_api.is_loaded:
        # Si el modelo no está cargado, devolver divisiones básicas
        basic_divisions = {
            'SP1': 'La Liga (España)',
            'E0': 'Premier League (Inglaterra)',
            'I1': 'Serie A (Italia)',
            'D1': 'Bundesliga (Alemania)',
            'F1': 'Ligue 1 (Francia)'
        }
        return DivisionsResponse(
            success=True,
            divisions=basic_divisions,
            total=len(basic_divisions)
        )
    
    divisions_with_names = {
        div: predictor_api.get_division_full_name(div) 
        for div in predictor_api.division_mapping.keys()
    }
    
    return DivisionsResponse(
        success=True,
        divisions=divisions_with_names,
        total=len(divisions_with_names)
    )

@app.get("/team-suggestions/{team_name}")
async def get_team_suggestions(team_name: str):
    """Obtener sugerencias de equipos similares"""
    if not predictor_api.is_loaded:
        raise HTTPException(status_code=503, detail="Modelo no cargado")
    
    suggestions = predictor_api.find_similar_teams(team_name)
    return {
        "success": True,
        "team_name": team_name,
        "suggestions": suggestions[:10],  # Limitar a 10 sugerencias
        "total_suggestions": len(suggestions)
    }

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )