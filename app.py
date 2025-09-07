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
            "/test-connection": "GET - Tester la connexion",
            "/health": "GET - Vérifier le statut"
        },
        "version": "3.0.0 - Identifiants directs + ENT Support",
        "supported_methods": ["direct_credentials", "ent_connection"]
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "credentials_configured": bool(os.getenv('PRONOTE_USERNAME') and os.getenv('PRONOTE_PASSWORD')),
        "url_configured": bool(os.getenv('PRONOTE_URL'))
    })

@app.route('/test-connection')
def test_connection():
    """Test de connexion avec identifiants directs ou ENT"""
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
        
        # Tentative de connexion directe d'abord
        try:
            client = pronotepy.Client(pronote_url, username=username, password=password)
            connection_method = "direct"
        except Exception as direct_error:
            print(f"Connexion directe échouée: {direct_error}")
            
            # Essayer avec différents ENT de Normandie
            ent_functions = []
            
            # Importer les fonctions ENT disponibles
            try:
                from pronotepy.ent import cas_arsene76
                ent_functions.append(("cas_arsene76", cas_arsene76))
            except ImportError:
                pass
                
            try:
                from pronotepy.ent import cas_ent27  
                ent_functions.append(("cas_ent27", cas_ent27))
            except ImportError:
                pass
                
            try:
                from pronotepy.ent import ent_normandie
                ent_functions.append(("ent_normandie", ent_normandie))
            except ImportError:
                pass
            
            # Essayer chaque fonction ENT
            client = None
            connection_method = None
            
            for ent_name, ent_func in ent_functions:
                try:
                    print(f"Tentative avec {ent_name}")
                    client = pronotepy.Client(pronote_url, username=username, password=password, ent=ent_func)
                    if client.logged_in:
                        connection_method = f"ent_{ent_name}"
                        print(f"✅ Connexion réussie avec {ent_name}")
                        break
                except Exception as ent_error:
                    print(f"Échec {ent_name}: {ent_error}")
                    continue
            
            # Si aucune méthode n'a fonctionné
            if not client or not client.logged_in:
                return jsonify({
                    "success": False,
                    "message": "Échec de connexion avec toutes les méthodes",
                    "tried_methods": ["direct"] + [name for name, _ in ent_functions],
                    "help": "Vérifiez vos identifiants ou contactez votre établissement"
                }), 401
        
        # Test réussi
        if client.logged_in:
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
                "url": pronote_url
            })
        else:
            return jsonify({
                "success": False,
                "message": "Connexion échouée",
                "help": "Vérifiez vos identifiants"
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
        
        # Connexion (même logique que test-connection)
        client = None
        connection_method = None
        
        # Tentative connexion directe
        try:
            client = pronotepy.Client(pronote_url, username=username, password=password)
            connection_method = "direct"
            print("✅ Connexion directe réussie")
        except Exception as direct_error:
            print(f"Connexion directe échouée: {direct_error}")
            
            # Essayer avec ENT
            ent_functions = []
            
            try:
                from pronotepy.ent import cas_arsene76
                ent_functions.append(("cas_arsene76", cas_arsene76))
            except ImportError:
                pass
                
            try:
                from pronotepy.ent import cas_ent27  
                ent_functions.append(("cas_ent27", cas_ent27))
            except ImportError:
                pass
            
            # Essayer avec ENT Auvergne-Rhône-Alpes spécifiquement
            ent_functions = []
            
            # D'abord essayer les ENT spécifiques à votre région
            try:
                from pronotepy.ent import _cas
                # Fonction CAS spécifique pour Auvergne-Rhône-Alpes
                cas_ara = lambda: _cas("https://cas.ent.auvergnerhonealpes.fr/login")
                ent_functions.append(("cas_auvergne_rhone_alpes", cas_ara))
            except ImportError:
                pass
            
            # Essayer d'autres ENT CAS similaires
            try:
                from pronotepy.ent import occitanie_montpellier
                ent_functions.append(("occitanie_montpellier", occitanie_montpellier))
            except ImportError:
                pass
        
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
            "connection_method": connection_method
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

@app.route('/setup-help')
def setup_help():
    """Guide pour obtenir les identifiants"""
    return jsonify({
        "message": "Comment obtenir vos identifiants Pronote directs",
        "methods": [
            {
                "method": "Demande à l'établissement",
                "steps": [
                    "Contactez le secrétariat ou la vie scolaire",
                    "Demandez vos 'identifiants Pronote directs'",
                    "Expliquez que c'est pour l'application mobile",
                    "Ils vous fourniront: URL, nom d'utilisateur, mot de passe"
                ]
            },
            {
                "method": "Via l'ENT", 
                "steps": [
                    "Connectez-vous à Pronote via votre ENT",
                    "Cherchez 'Mes données' ou 'Mon compte'",
                    "Parfois les identifiants directs y sont affichés"
                ]
            }
        ],
        "what_to_ask": "Bonjour, j'aimerais accéder à Pronote directement sans passer par l'ENT pour utiliser l'application mobile. Pourriez-vous me communiquer mes identifiants Pronote directs (URL, nom d'utilisateur, mot de passe) ?",
        "auvergne_rhone_alpes_info": {
            "ent_url": "https://cas.ent.auvergnerhonealpes.fr/login",
            "pronote_url": "https://0010010f.index-education.net/pronote/eleve.html",
            "platform": "SKOLENGO",
            "exploitant": "KOSMOS"
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
