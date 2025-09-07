from flask import Flask, jsonify, request
import pronotepy
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "status": "API Pronote opérationnelle",
        "endpoints": {
            "/homework": "GET - Récupérer les devoirs",
            "/health": "GET - Vérifier le statut"
        },
        "version": "1.0.0"
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/homework')
def get_homework():
    try:
        # Récupérer les paramètres
        pronote_url = request.args.get('url') or os.getenv('PRONOTE_URL')
        username = request.args.get('username') or os.getenv('PRONOTE_USERNAME')
        password = request.args.get('password') or os.getenv('PRONOTE_PASSWORD')
        days = int(request.args.get('days', 7))
        
        # Vérifier les paramètres obligatoires
        if not all([pronote_url, username, password]):
            return jsonify({
                "error": "Paramètres manquants",
                "required": ["url", "username", "password"],
                "help": "Passez les paramètres en query string ou variables d'environnement"
            }), 400
        
        # Connexion à Pronote
        print(f"Tentative de connexion à {pronote_url} avec {username}")
        client = pronotepy.Client(pronote_url, username=username, password=password)
        
        if not client.logged_in:
            return jsonify({
                "error": "Échec de connexion à Pronote",
                "details": "Vérifiez vos identifiants et l'URL"
            }), 401
        
        print("✅ Connexion réussie à Pronote")
        
        # Récupérer les informations de l'élève
        student_info = {
            "name": client.info.name if hasattr(client.info, 'name') else "Non disponible",
            "class": getattr(client.info, 'class_name', 'Non disponible')
        }
        
        # Récupérer les devoirs
        homework_list = []
        
        for i in range(days):
            date = datetime.now() + timedelta(days=i)
            try:
                homework = client.homework(date)
                print(f"Date {date.strftime('%Y-%m-%d')}: {len(homework)} devoirs trouvés")
                
                for hw in homework:
                    homework_data = {
                        "id": getattr(hw, 'id', f"hw_{i}_{len(homework_list)}"),
                        "subject": hw.subject.name if hasattr(hw, 'subject') and hasattr(hw.subject, 'name') else "Matière inconnue",
                        "description": getattr(hw, 'description', 'Pas de description'),
                        "date": hw.date.strftime("%Y-%m-%d") if hasattr(hw, 'date') else date.strftime("%Y-%m-%d"),
                        "done": getattr(hw, 'done', False),
                        "difficulty": getattr(hw, 'difficulty', None),
                        "color": getattr(hw.subject, 'color', None) if hasattr(hw, 'subject') else None,
                        "teacher": getattr(hw.subject, 'teacher', {}).get('name', '') if hasattr(hw, 'subject') and hasattr(hw.subject, 'teacher') else '',
                        "retrieved_at": datetime.now().isoformat()
                    }
                    homework_list.append(homework_data)
                    
            except Exception as date_error:
                print(f"Erreur pour la date {date.strftime('%Y-%m-%d')}: {str(date_error)}")
                continue
        
        # Statistiques
        stats = {
            "total": len(homework_list),
            "completed": len([hw for hw in homework_list if hw['done']]),
            "pending": len([hw for hw in homework_list if not hw['done']]),
            "urgent": len([hw for hw in homework_list if hw['date'] == datetime.now().strftime('%Y-%m-%d')])
        }
        
        result = {
            "success": True,
            "student": student_info,
            "homework": homework_list,
            "stats": stats,
            "sync_date": datetime.now().isoformat(),
            "days_requested": days
        }
        
        print(f"✅ Récupération terminée: {len(homework_list)} devoirs")
        return jsonify(result)
        
    except pronotepy.exceptions.PronoteAPIError as e:
        print(f"❌ Erreur API Pronote: {str(e)}")
        return jsonify({
            "error": "Erreur API Pronote",
            "message": str(e),
            "type": "PronoteAPIError"
        }), 500
        
    except Exception as e:
        print(f"❌ Erreur générale: {str(e)}")
        return jsonify({
            "error": "Erreur serveur",
            "message": str(e),
            "type": "ServerError"
        }), 500

@app.route('/test-connection')
def test_connection():
    """Endpoint pour tester la connexion Pronote"""
    try:
        pronote_url = request.args.get('url') or os.getenv('PRONOTE_URL')
        username = request.args.get('username') or os.getenv('PRONOTE_USERNAME')
        password = request.args.get('password') or os.getenv('PRONOTE_PASSWORD')
        
        if not all([pronote_url, username, password]):
            return jsonify({
                "error": "Paramètres manquants pour le test"
            }), 400
        
        client = pronotepy.Client(pronote_url, username=username, password=password)
        
        if client.logged_in:
            return jsonify({
                "success": True,
                "message": "Connexion Pronote réussie",
                "student": client.info.name if hasattr(client.info, 'name') else "Nom non disponible"
            })
        else:
            return jsonify({
                "success": False,
                "message": "Échec de connexion"
            }), 401
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
