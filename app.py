from flask import Flask, jsonify, request
import pronotepy
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import json
import uuid as uuid_module

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "status": "API Pronote opérationnelle",
        "endpoints": {
            "/homework": "GET - Récupérer les devoirs avec QR Code",
            "/test-qr": "GET - Tester la connexion QR Code",
            "/health": "GET - Vérifier le statut"
        },
        "version": "2.1.0 - QR Code Support avec UUID"
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "qr_configured": bool(os.getenv('PRONOTE_QR_DATA'))
    })

@app.route('/test-qr')
def test_qr():
    """Test de connexion avec QR Code"""
    try:
        # Récupérer les données QR depuis les variables d'environnement
        qr_data_str = os.getenv('PRONOTE_QR_DATA')
        if not qr_data_str:
            return jsonify({
                "error": "QR_DATA non configuré",
                "help": "Ajoutez PRONOTE_QR_DATA dans les variables d'environnement"
            }), 400
        
        # Parser les données JSON
        qr_data = json.loads(qr_data_str)
        confirmation_code = request.args.get('code', '1234')
        
        # Générer un UUID unique pour cette session
        session_uuid = str(uuid_module.uuid4())
        
        print(f"Test connexion QR Code avec code: {confirmation_code}")
        print(f"UUID généré: {session_uuid}")
        print(f"URL: {qr_data.get('url')}")
        print(f"Login: {qr_data.get('login')[:10]}...")
        
        # Tentative de connexion avec UUID
        client = pronotepy.Client.qrcode_login(qr_data, confirmation_code, session_uuid)
        
        if client.logged_in:
            student_name = getattr(client.info, 'name', 'Nom non disponible')
            return jsonify({
                "success": True,
                "message": "Connexion QR Code réussie",
                "student": student_name,
                "url": qr_data.get('url'),
                "uuid": session_uuid
            })
        else:
            return jsonify({
                "success": False,
                "message": "Échec de connexion QR Code",
                "help": "Vérifiez le code de confirmation ou régénérez le QR Code"
            }), 401
            
    except json.JSONDecodeError:
        return jsonify({
            "error": "Format QR_DATA invalide",
            "help": "PRONOTE_QR_DATA doit être un JSON valide"
        }), 400
    except Exception as e:
        print(f"Erreur test QR: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "help": "Le QR Code a peut-être expiré (10 min), régénérez-le"
        }), 500

@app.route('/homework')
def get_homework():
    try:
        # Récupérer les données QR
        qr_data_str = os.getenv('PRONOTE_QR_DATA')
        if not qr_data_str:
            return jsonify({
                "error": "QR_DATA non configuré",
                "help": "Configurez PRONOTE_QR_DATA dans les variables d'environnement"
            }), 400
        
        qr_data = json.loads(qr_data_str)
        confirmation_code = request.args.get('code', '1234')
        days = int(request.args.get('days', 7))
        
        # Générer un UUID unique pour cette session
        session_uuid = str(uuid_module.uuid4())
        
        print(f"Récupération devoirs avec QR Code - {days} jours")
        print(f"UUID: {session_uuid}")
        
        # Connexion avec QR Code et UUID
        client = pronotepy.Client.qrcode_login(qr_data, confirmation_code, session_uuid)
        
        if not client.logged_in:
            return jsonify({
                "error": "Échec de connexion QR Code",
                "help": "Le QR Code a peut-être expiré ou le code de confirmation est incorrect"
            }), 401
        
        print("✅ Connexion QR Code réussie")
        
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
            "connection_method": "QR_CODE",
            "session_uuid": session_uuid
        }
        
        print(f"✅ Récupération terminée: {len(homework_list)} devoirs")
        return jsonify(result)
        
    except json.JSONDecodeError:
        return jsonify({
            "error": "Format QR_DATA invalide",
            "message": "Les données QR Code ne sont pas au format JSON valide"
        }), 400
        
    except pronotepy.exceptions.PronoteAPIError as e:
        print(f"❌ Erreur API Pronote: {str(e)}")
        return jsonify({
            "error": "Erreur API Pronote",
            "message": str(e),
            "type": "PronoteAPIError",
            "help": "Le QR Code a peut-être expiré, régénérez-le"
        }), 500
        
    except Exception as e:
        print(f"❌ Erreur générale: {str(e)}")
        return jsonify({
            "error": "Erreur serveur",
            "message": str(e),
            "type": "ServerError"
        }), 500

@app.route('/refresh-qr')
def refresh_qr():
    """Endpoint pour indiquer comment renouveler le QR Code"""
    return jsonify({
        "message": "Pour renouveler le QR Code:",
        "steps": [
            "1. Connectez-vous à Pronote via votre ENT",
            "2. Générez un nouveau QR Code",
            "3. Extrayez les nouvelles données JSON",
            "4. Mettez à jour la variable PRONOTE_QR_DATA sur Render",
            "5. Redémarrez le service Render"
        ],
        "current_qr_configured": bool(os.getenv('PRONOTE_QR_DATA')),
        "validity": "Les QR Codes expirent après 10 minutes"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
