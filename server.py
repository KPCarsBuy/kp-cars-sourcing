from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


# ============================================================
# BASE DE DONNÉES DE TEST KP CARS
# ============================================================

vehicles = [
    {
        "id": 1,
        "marque": "Renault",
        "modele": "Clio",
        "annee": 2011,
        "kilometrage": 124500,
        "prix_achat": 3900,
        "prix_vente": 6490,
        "source": "Allemagne",
        "url": "https://www.mobile.de/"
    },
    {
        "id": 2,
        "marque": "Renault",
        "modele": "Clio",
        "annee": 2010,
        "kilometrage": 138000,
        "prix_achat": 3200,
        "prix_vente": 5990,
        "source": "Allemagne",
        "url": "https://www.mobile.de/"
    },
    {
        "id": 3,
        "marque": "Renault",
        "modele": "Clio",
        "annee": 2009,
        "kilometrage": 149000,
        "prix_achat": 2800,
        "prix_vente": 5490,
        "source": "Allemagne",
        "url": "https://www.mobile.de/"
    },
    {
        "id": 4,
        "marque": "Renault",
        "modele": "Clio",
        "annee": 2012,
        "kilometrage": 112000,
        "prix_achat": 4500,
        "prix_vente": 6990,
        "source": "Allemagne",
        "url": "https://www.mobile.de/"
    },
    {
        "id": 5,
        "marque": "Volkswagen",
        "modele": "Golf",
        "annee": 2017,
        "kilometrage": 98000,
        "prix_achat": 10900,
        "prix_vente": 14990,
        "source": "Allemagne",
        "url": "https://www.mobile.de/"
    },
    {
        "id": 6,
        "marque": "Volkswagen",
        "modele": "Tiguan",
        "annee": 2018,
        "kilometrage": 105000,
        "prix_achat": 16900,
        "prix_vente": 21990,
        "source": "Allemagne",
        "url": "https://www.mobile.de/"
    },
    {
        "id": 7,
        "marque": "BMW",
        "modele": "320d",
        "annee": 2019,
        "kilometrage": 89000,
        "prix_achat": 18900,
        "prix_vente": 23990,
        "source": "Allemagne",
        "url": "https://www.mobile.de/"
    },
    {
        "id": 8,
        "marque": "Mercedes-Benz",
        "modele": "A45 AMG",
        "annee": 2020,
        "kilometrage": 78000,
        "prix_achat": 36950,
        "prix_vente": 44990,
        "source": "Allemagne",
        "url": "https://www.mobile.de/"
    },
    {
        "id": 9,
        "marque": "Audi",
        "modele": "A3",
        "annee": 2018,
        "kilometrage": 92000,
        "prix_achat": 13900,
        "prix_vente": 18490,
        "source": "Allemagne",
        "url": "https://www.mobile.de/"
    },
    {
        "id": 10,
        "marque": "Peugeot",
        "modele": "208",
        "annee": 2019,
        "kilometrage": 87000,
        "prix_achat": 8900,
        "prix_vente": 12990,
        "source": "Allemagne",
        "url": "https://www.mobile.de/"
    }
]


# ============================================================
# CALCUL DE L'OPPORTUNITÉ
# ============================================================

def enrich_vehicle(vehicle):

    prix_achat = float(vehicle.get("prix_achat") or 0)
    prix_vente = float(vehicle.get("prix_vente") or 0)

    marge = prix_vente - prix_achat

    if prix_achat > 0:
        marge_pourcentage = (marge / prix_achat) * 100
    else:
        marge_pourcentage = 0

    # Score simple KP Cars
    score = 0

    if marge >= 3000:
        score += 40
    elif marge >= 2000:
        score += 30
    elif marge >= 1000:
        score += 20
    elif marge > 0:
        score += 10

    if marge_pourcentage >= 30:
        score += 30
    elif marge_pourcentage >= 20:
        score += 20
    elif marge_pourcentage >= 10:
        score += 10

    kilometrage = int(vehicle.get("kilometrage") or 0)

    if kilometrage <= 100000:
        score += 20
    elif kilometrage <= 150000:
        score += 10

    annee = int(vehicle.get("annee") or 0)

    if annee >= 2018:
        score += 10

    vehicle["marge"] = round(marge, 2)
    vehicle["marge_pourcentage"] = round(marge_pourcentage, 1)
    vehicle["score"] = min(score, 100)

    if vehicle["score"] >= 80:
        vehicle["opportunite"] = "EXCELLENTE"
    elif vehicle["score"] >= 60:
        vehicle["opportunite"] = "TRÈS BONNE"
    elif vehicle["score"] >= 40:
        vehicle["opportunite"] = "INTÉRESSANTE"
    else:
        vehicle["opportunite"] = "À ÉTUDIER"

    return vehicle


# ============================================================
# INITIALISATION
# ============================================================

for vehicle in vehicles:
    enrich_vehicle(vehicle)


# ============================================================
# ACCUEIL
# ============================================================

@app.route("/")
def home():
    return jsonify({
        "status": "online",
        "app": "KP Cars",
        "message": "KP Cars API opérationnelle",
        "vehicles": len(vehicles)
    })


# ============================================================
# LISTE DES VÉHICULES
# ============================================================

@app.route("/api/vehicles", methods=["GET"])
def get_vehicles():
    return jsonify(vehicles)


# ============================================================
# AJOUT D'UN VÉHICULE
# ============================================================

@app.route("/api/vehicles", methods=["POST"])
def add_vehicle():

    data = request.get_json() or {}

    vehicle = {
        "id": max([v["id"] for v in vehicles], default=0) + 1,
        "marque": data.get("marque", ""),
        "modele": data.get("modele", ""),
        "annee": data.get("annee", 0),
        "kilometrage": data.get("kilometrage", 0),
        "prix_achat": data.get("prix_achat", 0),
        "prix_vente": data.get("prix_vente", 0),
        "source": data.get("source", ""),
        "url": data.get("url", "")
    }

    enrich_vehicle(vehicle)

    vehicles.append(vehicle)

    return jsonify(vehicle), 201


# ============================================================
# SUPPRESSION
# ============================================================

@app.route("/api/vehicles/<int:vehicle_id>", methods=["DELETE"])
def delete_vehicle(vehicle_id):

    global vehicles

    vehicles = [
        vehicle
        for vehicle in vehicles
        if vehicle["id"] != vehicle_id
    ]

    return jsonify({
        "success": True
    })


# ============================================================
# MOTEUR DE SOURCING
# ============================================================

@app.route("/api/search", methods=["POST"])
def search():

    criteria = request.get_json() or {}

    results = []

    marque = str(criteria.get("marque") or "").strip().lower()
    modele = str(criteria.get("modele") or "").strip().lower()

    annee_min = criteria.get("annee_min")
    km_max = criteria.get("km_max")
    prix_max = criteria.get("prix_max")
    pays = str(criteria.get("pays") or "").strip().lower()

    for vehicle in vehicles:

        # -------------------------
        # MARQUE
        # -------------------------

        if marque:
            if marque not in vehicle["marque"].lower():
                continue

        # -------------------------
        # MODÈLE
        # -------------------------

        if modele:
            if modele not in vehicle["modele"].lower():
                continue

        # -------------------------
        # ANNÉE MINIMUM
        # -------------------------

        if annee_min:
            if int(vehicle["annee"] or 0) < int(annee_min):
                continue

        # -------------------------
        # KILOMÉTRAGE MAXIMUM
        # -------------------------

        if km_max:
            if int(vehicle["kilometrage"] or 0) > int(km_max):
                continue

        # -------------------------
        # PRIX MAXIMUM
        # -------------------------

        if prix_max:
            if float(vehicle["prix_achat"] or 0) > float(prix_max):
                continue

        # -------------------------
        # PAYS
        # -------------------------

        if pays:
            if pays not in vehicle["source"].lower():
                continue

        # -------------------------
        # AJOUT DU RÉSULTAT
        # -------------------------

        results.append(enrich_vehicle(vehicle.copy()))

    # Meilleures opportunités en premier
    results.sort(
        key=lambda vehicle: vehicle.get("score", 0),
        reverse=True
    )

    return jsonify(results)


# ============================================================
# SANTÉ DE L'API
# ============================================================

@app.route("/api/health")
def health():

    return jsonify({
        "status": "healthy",
        "app": "KP Cars",
        "vehicles": len(vehicles)
    })


# ============================================================
# LANCEMENT
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
