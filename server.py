from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


# ============================================================
# BASE KP CARS
# ============================================================

vehicles = [
    {
        "id": 1,
        "source": "mobile.de",
        "source_id": "TEST001",
        "url": "",
        "image_url": "",
        "vendeur": "",
        "ville": "",
        "pays": "Allemagne",
        "marque": "Renault",
        "modele": "Clio",
        "annee": 2011,
        "kilometrage": 124500,
        "prix_achat": 3900,
        "prix_vente": 6490
    },
    {
        "id": 2,
        "source": "mobile.de",
        "source_id": "TEST002",
        "url": "",
        "image_url": "",
        "vendeur": "",
        "ville": "",
        "pays": "Allemagne",
        "marque": "Renault",
        "modele": "Clio",
        "annee": 2010,
        "kilometrage": 138000,
        "prix_achat": 3200,
        "prix_vente": 5990
    },
    {
        "id": 3,
        "source": "mobile.de",
        "source_id": "TEST003",
        "url": "",
        "image_url": "",
        "vendeur": "",
        "ville": "",
        "pays": "Allemagne",
        "marque": "Renault",
        "modele": "Clio",
        "annee": 2009,
        "kilometrage": 149000,
        "prix_achat": 2800,
        "prix_vente": 5490
    },
    {
        "id": 4,
        "source": "mobile.de",
        "source_id": "TEST004",
        "url": "",
        "image_url": "",
        "vendeur": "",
        "ville": "",
        "pays": "Allemagne",
        "marque": "Renault",
        "modele": "Clio",
        "annee": 2012,
        "kilometrage": 112000,
        "prix_achat": 4500,
        "prix_vente": 6990
    }
]


# ============================================================
# OUTIL : CONSTRUIRE LE LIEN MOBILE.DE
# ============================================================

def build_source_url(source, source_id, url=""):

    if url:
        return url

    if source.lower() == "mobile.de" and source_id:
        return (
            "https://suchen.mobile.de/fahrzeuge/details.html?id="
            + str(source_id)
        )

    return ""


# ============================================================
# ANALYSE KP CARS
# ============================================================

def enrich_vehicle(vehicle):

    prix_achat = float(vehicle.get("prix_achat") or 0)
    prix_vente = float(vehicle.get("prix_vente") or 0)

    marge = prix_vente - prix_achat

    if prix_achat > 0:
        marge_pourcentage = (marge / prix_achat) * 100
    else:
        marge_pourcentage = 0

    score = 0

    # Marge
    if marge >= 3000:
        score += 40
    elif marge >= 2000:
        score += 30
    elif marge >= 1000:
        score += 20
    elif marge > 0:
        score += 10

    # Rentabilité
    if marge_pourcentage >= 30:
        score += 30
    elif marge_pourcentage >= 20:
        score += 20
    elif marge_pourcentage >= 10:
        score += 10

    # Kilométrage
    kilometrage = int(vehicle.get("kilometrage") or 0)

    if kilometrage <= 100000:
        score += 20
    elif kilometrage <= 150000:
        score += 10

    # Année
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

    vehicle["url"] = build_source_url(
        vehicle.get("source", ""),
        vehicle.get("source_id", ""),
        vehicle.get("url", "")
    )

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
        "vehicles": len(vehicles),
        "sources": [
            "mobile.de"
        ]
    })


# ============================================================
# SANTÉ
# ============================================================

@app.route("/api/health")
def health():

    return jsonify({
        "status": "healthy",
        "app": "KP Cars",
        "vehicles": len(vehicles)
    })


# ============================================================
# TOUS LES VÉHICULES
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
        "id": max(
            [v["id"] for v in vehicles],
            default=0
        ) + 1,

        "source": data.get("source", ""),
        "source_id": data.get("source_id", ""),
        "url": data.get("url", ""),
        "image_url": data.get("image_url", ""),
        "vendeur": data.get("vendeur", ""),
        "ville": data.get("ville", ""),
        "pays": data.get("pays", ""),

        "marque": data.get("marque", ""),
        "modele": data.get("modele", ""),
        "annee": data.get("annee", 0),
        "kilometrage": data.get("kilometrage", 0),

        "prix_achat": data.get("prix_achat", 0),
        "prix_vente": data.get("prix_vente", 0)
    }

    enrich_vehicle(vehicle)

    vehicles.append(vehicle)

    return jsonify(vehicle), 201


# ============================================================
# IMPORT D'UNE ANNONCE EXTERNE
# ============================================================

@app.route("/api/import/mobile", methods=["POST"])
def import_mobile():

    data = request.get_json() or {}

    source_id = data.get("mobileAdId") or data.get("source_id")

    if not source_id:
        return jsonify({
            "success": False,
            "error": "mobileAdId manquant"
        }), 400

    vehicle = {
        "id": max(
            [v["id"] for v in vehicles],
            default=0
        ) + 1,

        "source": "mobile.de",
        "source_id": source_id,

        "url": data.get("url", ""),

        "image_url": data.get(
            "image_url",
            data.get("image", "")
        ),

        "vendeur": data.get(
            "vendeur",
            data.get("seller", "")
        ),

        "ville": data.get(
            "ville",
            data.get("location", "")
        ),

        "pays": data.get(
            "pays",
            "Allemagne"
        ),

        "marque": data.get(
            "marque",
            data.get("make", "")
        ),

        "modele": data.get(
            "modele",
            data.get("model", "")
        ),

        "annee": data.get(
            "annee",
            data.get("year", 0)
        ),

        "kilometrage": data.get(
            "kilometrage",
            data.get("mileage", 0)
        ),

        "prix_achat": data.get(
            "prix_achat",
            data.get("price", 0)
        ),

        "prix_vente": data.get(
            "prix_vente",
            data.get("estimated_sale_price", 0)
        )
    }

    enrich_vehicle(vehicle)

    vehicles.append(vehicle)

    return jsonify({
        "success": True,
        "vehicle": vehicle
    }), 201


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

    marque = str(
        criteria.get("marque") or ""
    ).strip().lower()

    modele = str(
        criteria.get("modele") or ""
    ).strip().lower()

    pays = str(
        criteria.get("pays") or ""
    ).strip().lower()

    annee_min = criteria.get("annee_min")
    km_max = criteria.get("km_max")
    prix_max = criteria.get("prix_max")

    for vehicle in vehicles:

        # MARQUE
        if marque:
            if marque not in vehicle["marque"].lower():
                continue

        # MODÈLE
        if modele:
            if modele not in vehicle["modele"].lower():
                continue

        # ANNÉE
        if annee_min:
            if int(vehicle["annee"] or 0) < int(annee_min):
                continue

        # KILOMÉTRAGE
        if km_max:
            if int(vehicle["kilometrage"] or 0) > int(km_max):
                continue

        # PRIX
        if prix_max:
            if float(vehicle["prix_achat"] or 0) > float(prix_max):
                continue

        # PAYS
        if pays:
            if pays not in vehicle.get("pays", "").lower():
                continue

        results.append(
            enrich_vehicle(vehicle.copy())
        )

    # Meilleures opportunités en premier
    results.sort(
        key=lambda x: x.get("score", 0),
        reverse=True
    )

    return jsonify(results)


# ============================================================
# LANCEMENT
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
