from flask import Flask, jsonify, request
import pronotepy
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)

def cas_auvergne_rhone_alpes():
    """Fonction CAS spécifique pour Auvergne-Rhône-Alpes"""
    try:
        from pronotepy.ent.generic_func import _cas
        return _cas("https://cas.ent.auvergnerhonealpes.fr/login")
    except ImportError:
        # Fallback si l'import ne fonctionne pas
        return None

@app.route('/')
def home():
    return jsonify({
        "status": "API Pronote opérationnelle",
        "endpoints": {
            "/homework": "GET - Récupérer les devoirs",
            "/test-connection": "GET - Tester la connexion",
            "/health": "GET - Vérifier le statut"
        },
        "version": "3.1.0 - ENT Auvergne-Rhône-Alpes",
        "ent_configured": "CAS Auvergne-Rhône-Alpes"
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "credentials_configured": bool(os.getenv('PRONOTE_USERNAME') and os.getenv('PRONOTE_PASSWORD')),
        "url_configured": bool(os.getenv('PRONOTE_URL')),
        "ent_region": "Auvergne-Rhône-Alpes"
    })

@app.route('/test-connection')
def test_connection():
    """Test de connexion avec ENT Auvergne-Rhône-Alpes"""
    try:
        # Récupérer les paramètres
        pronote_url = request.args.get('url') or os.getenv('PRONOTE_URL')
        username = request.args.get('username') or os.getenv('PRONOTE_USERNAME') 
        password = request.args.get('password') or os.getenv('PRONOTE_PASSWORD')
        
        # Vérifier les paramètres obligatoires
        if not all([pronote_url, username, password]):
            return jsonify({
                "error": "Paramètres manquants",
                "required": ["url", "username", "password"],
                "help": "Configurez PRONOTE_URL, PRONOTE_USERNAME, PRONOTE_PASSWORD"
            }), 400
        
        print(f"Test connexion à {pronote_url} avec {username}")
        
        # Essayer d'abord la connexion directe
        try:
            print("Tentative de connexion directe...")
            client = pronotepy.Client(pronote_url, username=username, password=password)
            if client.logged_in:
                print("✅ Connexion directe réussie")
                connection_method = "direct"
            else:
                client = None
        except Exception as direct_error:
            print(f"Connexion directe échouée: {direct_error}")
            client = None
        
        # Si la connexion directe échoue, essayer avec l'ENT
        if not client or not client.logged_in:
            print("Tentative avec ENT Auvergne-Rhône-Alpes...")
            try:
                ent_func = cas_auvergne_rhone_alpes()
                if ent_func:
                    client = pronotepy.Client(pronote_url, username=username, password=password, ent=ent_func)
                    if client.logged_in:
                        print("✅ Connexion ENT réussie")
                        connection_method = "ent_auvergne_rhone_alpes"
                    else:
                        client = None
                else:
                    print("Fonction ENT non disponible")
                    client = None
            except Exception as ent_error:
                print(f"Échec ENT Auvergne-Rhône-Alpes: {ent_error}")
                client = None
        
        # Vérifier le résultat final
        if client and client.logged_in:
            student_name = getattr(client.info, 'name', 'Nom non disponible')
            student_class = getattr(client.info, 'class_name', 'Classe non disponible')
            
            return jsonify({
                "success": True,
                "message": "Connexion réussie",
                "student": {
                    "name": student_name,
                    "class": student_class
                },
                "connection_method": connection_method,
                "url": pronote_url,
                "ent_tested": "Auvergne-Rhône-Alpes"
            })
        else:
            return jsonify({
                "success": False,
                "message": "Échec de connexion avec toutes les méthodes",
                "tried_methods": ["direct", "ent_auvergne_rhone_alpes"],
                "help": "Vérifiez vos identifiants ENT ou contactez votre établissement",
                "debug_info": {
                    "url": pronote_url,
                    "username": username[:3] + "***" if username else None
                }
            }), 401
            
    except Exception as e:
        print(f"Erreur test connexion: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "help": "Erreur lors du test de connexion"
        }), 500

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
                "help": "Configurez PRONOTE_URL, PRONOTE_USERNAME, PRONOTE_PASSWORD"
            }), 400
        
        print(f"Récupération devoirs - {days} jours")
        
        # Établir la connexion (même logique que test-connection)
        client = None
        connection_method = None
        
        # Tentative connexion directe
        try:
            client = pronotepy.Client(pronote_url, username=username, password=password)
            if client.logged_in:
                connection_method = "direct"
                print("✅ Connexion directe réussie")
            else:
                client = None
        except Exception as direct_error:
            print(f"Connexion directe échouée: {direct_error}")
            client = None
        
        # Tentative avec ENT si nécessaire
        if not client or not client.logged_in:
            try:
                ent_func = cas_auvergne_rhone_alpes()
                if ent_func:
                    client = pronotepy.Client(pronote_url, username=username, password=password, ent=ent_func)
                    if client.logged_in:
                        connection_method = "ent_auvergne_rhone_alpes"
                        print("✅ Connexion ENT réussie")
                    else:
                        client = None
            except Exception as ent_error:
                print(f"Échec ENT: {ent_error}")
                client = None
        
        if not client or not client.logged_in:
            return jsonify({
                "error": "Échec de connexion",
                "help": "Impossible de se connecter avec les identifiants fournis"
            }), 401
        
        # Récupérer les informations de l'élève
        student_info = {
            "name": getattr(client.info, 'name', 'Non disponible'),
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
            "days_requested": days,
            "connection_method": connection_method,
            "ent_region": "Auvergne-Rhône-Alpes"
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

@app.route('/debug-ent')
def debug_ent():
    """Endpoint de debug pour l'ENT"""
    try:
        ent_func = get_cas_auvergne_rhone_alpes()
        return jsonify({
            "ent_function_available": ent_func is not None,
            "ent_url": "https://cas.ent.auvergnerhonealpes.fr/login",
            "pronotepy_version": pronotepy.__version__ if hasattr(pronotepy, '__version__') else "unknown",
            "environment_vars": {
                "PRONOTE_URL": bool(os.getenv('PRONOTE_URL')),
                "PRONOTE_USERNAME": bool(os.getenv('PRONOTE_USERNAME')),
                "PRONOTE_PASSWORD": bool(os.getenv('PRONOTE_PASSWORD'))
            }
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "help": "Erreur lors du debug ENT"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
