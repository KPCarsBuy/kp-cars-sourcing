from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ============================================================
# CONFIGURATION KP CARS
# ============================================================

FRAIS_TRANSPORT = 750
FRAIS_ADMIN = 250
RESERVE_PREPARATION = 500


# ============================================================
# VEHICULES DE TEST
# IMPORTANT : ce sont des données de démonstration.
# Ce ne sont PAS de vraies annonces mobile.de.
# ============================================================

vehicles = [
    {
        "source": "mobile.de",
        "source_id": "TEST001",
        "marque": "Renault",
        "modele": "Clio",
        "annee": 2011,
        "kilometrage": 124500,
        "prix_achat": 3900,
        "prix_vente": 6490,
        "pays": "Allemagne",
        "url": ""
    },
    {
        "source": "mobile.de",
        "source_id": "TEST002",
        "marque": "Renault",
        "modele": "Clio",
        "annee": 2010,
        "kilometrage": 118000,
        "prix_achat": 4200,
        "prix_vente": 6990,
        "pays": "Allemagne",
        "url": ""
    },
    {
        "source": "mobile.de",
        "source_id": "TEST003",
        "marque": "Renault",
        "modele": "Clio",
        "annee": 2012,
        "kilometrage": 108500,
        "prix_achat": 4500,
        "prix_vente": 7490,
        "pays": "Allemagne",
        "url": ""
    },
    {
        "source": "mobile.de",
        "source_id": "TEST004",
        "marque": "Renault",
        "modele": "Clio",
        "annee": 2009,
        "kilometrage": 139000,
        "prix_achat": 3200,
        "prix_vente": 5990,
        "pays": "Allemagne",
        "url": ""
    }
]


# ============================================================
# URL MOBILE.DE
# ============================================================

def build_source_url(source, source_id, url=""):
    """
    Construit uniquement une vraie URL mobile.de
    lorsqu'on possède un véritable identifiant numérique.
    Les véhicules TEST restent sans lien.
    """

    if url:
        return url

    if (
        str(source).lower() == "mobile.de"
        and str(source_id).isdigit()
    ):
        return (
            "https://suchen.mobile.de/fahrzeuge/details.html?id="
            + str(source_id)
        )

    return ""


# ============================================================
# CALCUL KP CARS
# ============================================================

def enrich_vehicle(vehicle):

    prix_achat = float(vehicle.get("prix_achat") or 0)
    prix_vente = float(vehicle.get("prix_vente") or 0)

    transport = float(
        vehicle.get("transport", FRAIS_TRANSPORT) or 0
    )

    frais_admin = float(
        vehicle.get("frais_admin", FRAIS_ADMIN) or 0
    )

    preparation = float(
        vehicle.get("preparation", RESERVE_PREPARATION) or 0
    )

    # --------------------------------------------------------
    # COÛT RÉEL D'ACQUISITION
    # --------------------------------------------------------

    cout_total = (
        prix_achat
        + transport
        + frais_admin
        + preparation
    )

    # --------------------------------------------------------
    # MARGE NETTE
    # --------------------------------------------------------

    marge_nette = prix_vente - cout_total

    # --------------------------------------------------------
    # ROI
    # --------------------------------------------------------

    if cout_total > 0:
        roi = (marge_nette / cout_total) * 100
    else:
        roi = 0

    # --------------------------------------------------------
    # SCORE KP CARS
    # --------------------------------------------------------

    score = 0

    # Marge
    if marge_nette >= 2000:
        score += 40
    elif marge_nette >= 1500:
        score += 35
    elif marge_nette >= 1000:
        score += 30
    elif marge_nette >= 700:
        score += 20
    elif marge_nette >= 400:
        score += 10

    # ROI
    if roi >= 35:
        score += 30
    elif roi >= 25:
        score += 25
    elif roi >= 20:
        score += 20
    elif roi >= 15:
        score += 15
    elif roi >= 10:
        score += 10

    # Age
    annee = int(vehicle.get("annee") or 0)

    if annee >= 2015:
        score += 15
    elif annee >= 2012:
        score += 12
    elif annee >= 2010:
        score += 8
    elif annee >= 2008:
        score += 5

    # Kilométrage
    kilometrage = int(vehicle.get("kilometrage") or 0)

    if kilometrage <= 100000:
        score += 15
    elif kilometrage <= 125000:
        score += 12
    elif kilometrage <= 150000:
        score += 8
    elif kilometrage <= 175000:
        score += 4

    # --------------------------------------------------------
    # OPPORTUNITÉ
    # --------------------------------------------------------

    if score >= 80:
        opportunite = "EXCEPTIONNELLE"
    elif score >= 65:
        opportunite = "TRÈS BONNE"
    elif score >= 50:
        opportunite = "BONNE"
    elif score >= 35:
        opportunite = "MOYENNE"
    else:
        opportunite = "FAIBLE"

    # --------------------------------------------------------
    # URL
    # --------------------------------------------------------

    url = build_source_url(
        vehicle.get("source", ""),
        vehicle.get("source_id", ""),
        vehicle.get("url", "")
    )

    # --------------------------------------------------------
    # RESULTAT FINAL
    # --------------------------------------------------------

    result = dict(vehicle)

    result.update({
        "transport": round(transport, 2),
        "frais_admin": round(frais_admin, 2),
        "preparation": round(preparation, 2),
        "cout_total": round(cout_total, 2),
        "marge_nette": round(marge_nette, 2),
        "marge": round(marge_nette, 2),
        "roi": round(roi, 2),
        "score": min(score, 100),
        "opportunite": opportunite,
        "url": url
    })

    return result


# ============================================================
# API HEALTH
# ============================================================

@app.route("/api/health", methods=["GET"])
def health():

    return jsonify({
        "app": "KP Cars",
        "status": "healthy",
        "vehicles": len(vehicles)
    })


# ============================================================
# API VEHICLES
# ============================================================

@app.route("/api/vehicles", methods=["GET"])
def get_vehicles():

    return jsonify([
        enrich_vehicle(vehicle)
        for vehicle in vehicles
    ])


# ============================================================
# API SEARCH
# ============================================================

@app.route("/api/search", methods=["POST"])
def search():

    data = request.get_json(silent=True) or {}

    marque = str(data.get("marque") or "").strip().lower()
    modele = str(data.get("modele") or "").strip().lower()

    annee_min = data.get("annee_min")
    km_max = data.get("km_max")
    prix_max = data.get("prix_max")

    pays = str(data.get("pays") or "").strip().lower()

    results = []

    for vehicle in vehicles:

        # ----------------------------------------------------
        # MARQUE
        # ----------------------------------------------------

        if marque:
            if marque not in str(
                vehicle.get("marque", "")
            ).lower():
                continue

        # ----------------------------------------------------
        # MODELE
        # ----------------------------------------------------

        if modele:
            if modele not in str(
                vehicle.get("modele", "")
            ).lower():
                continue

        # ----------------------------------------------------
        # ANNÉE MINIMUM
        # ----------------------------------------------------

        if annee_min:
            try:
                if int(vehicle.get("annee", 0)) < int(annee_min):
                    continue
            except:
                pass

        # ----------------------------------------------------
        # KILOMÉTRAGE MAXIMUM
        # ----------------------------------------------------

        if km_max:
            try:
                if int(vehicle.get("kilometrage", 0)) > int(km_max):
                    continue
            except:
                pass

        # ----------------------------------------------------
        # PRIX ACHAT MAXIMUM
        # ----------------------------------------------------

        if prix_max:
            try:
                if float(vehicle.get("prix_achat", 0)) > float(prix_max):
                    continue
            except:
                pass

        # ----------------------------------------------------
        # PAYS
        # ----------------------------------------------------

        if pays:
            if pays not in str(
                vehicle.get("pays", "")
            ).lower():
                continue

        # ----------------------------------------------------
        # AJOUT
        # ----------------------------------------------------

        results.append(
            enrich_vehicle(vehicle)
        )

    # --------------------------------------------------------
    # TRI : MEILLEURES OPPORTUNITÉS EN PREMIER
    # --------------------------------------------------------

    results.sort(
        key=lambda x: (
            x.get("score", 0),
            x.get("marge_nette", 0)
        ),
        reverse=True
    )

    return jsonify(results)


# ============================================================
# IMPORT MOBILE.DE
# ============================================================

@app.route("/api/import/mobile", methods=["POST"])
def import_mobile():

    data = request.get_json(silent=True) or {}

    mobile_ad_id = str(
        data.get("mobileAdId") or ""
    ).strip()

    if not mobile_ad_id:
        return jsonify({
            "success": False,
            "error": "mobileAdId obligatoire"
        }), 400

    url = (
        "https://suchen.mobile.de/fahrzeuge/details.html?id="
        + mobile_ad_id
    )

    return jsonify({
        "success": True,
        "mobileAdId": mobile_ad_id,
        "url": url
    })


# ============================================================
# ROOT
# ============================================================

@app.route("/", methods=["GET"])
def root():
    return send_from_directory(".", "index.html")


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
