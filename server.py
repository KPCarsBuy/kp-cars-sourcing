from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

import os
import json
import base64
import urllib.parse
import urllib.request

app = Flask(__name__)
CORS(app)


# ============================================================
# CONFIGURATION KP CARS
# ============================================================

FRAIS_TRANSPORT = 750
FRAIS_ADMIN = 250
RESERVE_PREPARATION = 500

# Identifiants API mobile.de
MOBILE_API_USER = os.getenv("MOBILE_API_USER")
MOBILE_API_PASSWORD = os.getenv("MOBILE_API_PASSWORD")

COUNTRY_CODES = {
    "Allemagne": "DE",
    "Belgique": "BE",
    "France": "FR",
    "Pays-Bas": "NL",
    "Luxembourg": "LU"
}


# ============================================================
# VEHICULES DE TEST
# ============================================================
# Utilisés uniquement si les identifiants mobile.de
# ne sont pas encore configurés.
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

    prix_achat = float(
        vehicle.get("prix_achat") or 0
    )

    prix_vente = float(
        vehicle.get("prix_vente") or 0
    )

    transport = float(
        vehicle.get(
            "transport",
            FRAIS_TRANSPORT
        ) or 0
    )

    frais_admin = float(
        vehicle.get(
            "frais_admin",
            FRAIS_ADMIN
        ) or 0
    )

    preparation = float(
        vehicle.get(
            "preparation",
            RESERVE_PREPARATION
        ) or 0
    )

    # --------------------------------------------------------
    # COÛT TOTAL
    # --------------------------------------------------------

    cout_total = (
        prix_achat
        + transport
        + frais_admin
        + preparation
    )

    # --------------------------------------------------------
    # MARGE
    # --------------------------------------------------------

    marge_nette = prix_vente - cout_total

    # --------------------------------------------------------
    # ROI
    # --------------------------------------------------------

    if cout_total > 0:
        roi = (
            marge_nette
            / cout_total
        ) * 100
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

    # Année
    try:
        annee = int(
            vehicle.get("annee") or 0
        )
    except:
        annee = 0

    if annee >= 2015:
        score += 15

    elif annee >= 2012:
        score += 12

    elif annee >= 2010:
        score += 8

    elif annee >= 2008:
        score += 5

    # Kilométrage
    try:
        kilometrage = int(
            vehicle.get("kilometrage") or 0
        )
    except:
        kilometrage = 0

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
    # RESULTAT
    # --------------------------------------------------------

    result = dict(vehicle)

    result.update({
        "transport": round(
            transport,
            2
        ),

        "frais_admin": round(
            frais_admin,
            2
        ),

        "preparation": round(
            preparation,
            2
        ),

        "cout_total": round(
            cout_total,
            2
        ),

        "marge_nette": round(
            marge_nette,
            2
        ),

        "marge": round(
            marge_nette,
            2
        ),

        "roi": round(
            roi,
            2
        ),

        "score": min(
            score,
            100
        ),

        "opportunite": opportunite,

        "url": url
    })

    return result


# ============================================================
# SOURCING REEL MOBILE.DE
# ============================================================

def search_mobile_api(data):

    # Si les identifiants ne sont pas configurés,
    # on retourne None pour utiliser les véhicules de test.

    if (
        not MOBILE_API_USER
        or not MOBILE_API_PASSWORD
    ):
        return None

    marque = str(
        data.get("marque") or ""
    ).strip()

    modele = str(
        data.get("modele") or ""
    ).strip()

    annee_min = data.get(
        "annee_min"
    )

    km_max = data.get(
        "km_max"
    )

    prix_max = data.get(
        "prix_max"
    )

    pays = str(
        data.get("pays") or ""
    ).strip()

    # --------------------------------------------------------
    # CLASSIFICATION
    # --------------------------------------------------------

    classification = (
        "refdata/classes/Car"
    )

    if marque:

        classification += (
            "/makes/"
            + urllib.parse.quote(
                marque.upper()
            )
        )

    if modele and marque:

        classification += (
            "/models/"
            + urllib.parse.quote(
                modele.upper()
            )
        )

    # --------------------------------------------------------
    # PARAMETRES RECHERCHE
    # --------------------------------------------------------

    params = {
        "classification": classification,
        "page.number": "1",
        "page.size": "100",
        "sort.field": "price",
        "sort.order": "ASCENDING"
    }

    if prix_max:

        params["price.max"] = str(
            prix_max
        )

    if km_max:

        params["mileage.max"] = str(
            km_max
        )

    if annee_min:

        params[
            "firstRegistrationDate.min"
        ] = str(annee_min) + "-01"

    if pays in COUNTRY_CODES:

        params["country"] = (
            COUNTRY_CODES[pays]
        )

    # --------------------------------------------------------
    # URL API
    # --------------------------------------------------------

    query = urllib.parse.urlencode(
        params
    )

    api_url = (
        "https://services.mobile.de/"
        "search-api/search?"
        + query
    )

    # --------------------------------------------------------
    # AUTHENTIFICATION
    # --------------------------------------------------------

    credentials = (
        MOBILE_API_USER
        + ":"
        + MOBILE_API_PASSWORD
    )

    encoded_credentials = (
        base64.b64encode(
            credentials.encode()
        ).decode()
    )

    # --------------------------------------------------------
    # REQUETE
    # --------------------------------------------------------

    request_api = urllib.request.Request(
        api_url,

        headers={
            "Accept":
                "application/vnd.de.mobile.api+json",

            "Authorization":
                "Basic "
                + encoded_credentials
        }
    )

    # --------------------------------------------------------
    # APPEL MOBILE.DE
    # --------------------------------------------------------

    try:

        with urllib.request.urlopen(
            request_api,
            timeout=20
        ) as response:

            raw = (
                response
                .read()
                .decode("utf-8")
            )

            payload = json.loads(
                raw
            )

    except Exception as error:

        print(
            "Erreur API mobile.de:",
            error
        )

        return []

    # --------------------------------------------------------
    # RECUPERATION DES ANNONCES
    # --------------------------------------------------------

    ads = payload.get(
        "ads",
        []
    )

    results = []

    # --------------------------------------------------------
    # CONVERSION DES ANNONCES
    # --------------------------------------------------------

    for ad in ads:

        source_id = str(
            ad.get(
                "mobileAdId",
                ""
            )
        )

        # Année
        annee = 0

        if ad.get(
            "firstRegistration"
        ):

            try:

                annee = int(
                    str(
                        ad.get(
                            "firstRegistration"
                        )
                    )[:4]
                )

            except:

                annee = 0

        # Kilométrage
        kilometrage = 0

        if ad.get(
            "mileage"
        ):

            try:

                kilometrage = int(
                    ad.get(
                        "mileage"
                    )
                )

            except:

                kilometrage = 0

        # Prix
        prix_achat = 0

        if ad.get(
            "price"
        ):

            try:

                prix_achat = float(
                    ad.get(
                        "price"
                    )
                )

            except:

                prix_achat = 0

        # ----------------------------------------------------
        # VEHICULE KP CARS
        # ----------------------------------------------------

        vehicle = {

            "source":
                "mobile.de",

            "source_id":
                source_id,

            "marque":
                ad.get(
                    "make",
                    marque
                ),

            "modele":
                ad.get(
                    "model",
                    modele
                ),

            "annee":
                annee,

            "kilometrage":
                kilometrage,

            "prix_achat":
                prix_achat,

            # Le prix de revente sera déterminé
            # par le système KP Cars plus tard.
            "prix_vente":
                0,

            "pays":
                pays or "Allemagne",

            "url":
                (
                    "https://suchen.mobile.de/"
                    "fahrzeuge/details.html?id="
                    + source_id
                )
        }

        results.append(
            enrich_vehicle(
                vehicle
            )
        )

    return results


# ============================================================
# API HEALTH
# ============================================================

@app.route(
    "/api/health",
    methods=["GET"]
)
def health():

    return jsonify({

        "app":
            "KP Cars",

        "status":
            "healthy",

        "vehicles":
            len(vehicles),

        "mobile_api_configured":
            bool(
                MOBILE_API_USER
                and MOBILE_API_PASSWORD
            )
    })


# ============================================================
# API SOURCE STATUS
# ============================================================

@app.route(
    "/api/source-status",
    methods=["GET"]
)
def source_status():

    configured = bool(
        MOBILE_API_USER
        and MOBILE_API_PASSWORD
    )

    return jsonify({

        "source":
            "mobile.de",

        "mode":
            "LIVE"
            if configured
            else "DEMO",

        "configured":
            configured
    })


# ============================================================
# API VEHICLES
# ============================================================

@app.route(
    "/api/vehicles",
    methods=["GET"]
)
def get_vehicles():

    return jsonify([

        enrich_vehicle(
            vehicle
        )

        for vehicle in vehicles

    ])


# ============================================================
# API SEARCH
# ============================================================

@app.route(
    "/api/search",
    methods=["POST"]
)
def search():

    data = (
        request
        .get_json(
            silent=True
        )
        or {}
    )

    # --------------------------------------------------------
    # TENTATIVE DE SOURCING REEL
    # --------------------------------------------------------

    live_results = (
        search_mobile_api(
            data
        )
    )

    # Si mobile.de est configuré,
    # on retourne les vraies annonces.

    if live_results is not None:

        return jsonify(
            live_results
        )

    # --------------------------------------------------------
    # MODE DEMO
    # --------------------------------------------------------

    marque = str(
        data.get(
            "marque"
        ) or ""
    ).strip().lower()

    modele = str(
        data.get(
            "modele"
        ) or ""
    ).strip().lower()

    annee_min = data.get(
        "annee_min"
    )

    km_max = data.get(
        "km_max"
    )

    prix_max = data.get(
        "prix_max"
    )

    pays = str(
        data.get(
            "pays"
        ) or ""
    ).strip().lower()

    results = []

    # --------------------------------------------------------
    # FILTRAGE DEMO
    # --------------------------------------------------------

    for vehicle in vehicles:

        # Marque

        if marque:

            if marque not in str(
                vehicle.get(
                    "marque",
                    ""
                )
            ).lower():

                continue

        # Modèle

        if modele:

            if modele not in str(
                vehicle.get(
                    "modele",
                    ""
                )
            ).lower():

                continue

        # Année

        if annee_min:

            try:

                if int(
                    vehicle.get(
                        "annee",
                        0
                    )
                ) < int(
                    annee_min
                ):

                    continue

            except:

                pass

        # Kilométrage

        if km_max:

            try:

                if int(
                    vehicle.get(
                        "kilometrage",
                        0
                    )
                ) > int(
                    km_max
                ):

                    continue

            except:

                pass

        # Prix

        if prix_max:

            try:

                if float(
                    vehicle.get(
                        "prix_achat",
                        0
                    )
                ) > float(
                    prix_max
                ):

                    continue

            except:

                pass

        # Pays

        if pays:

            if pays not in str(
                vehicle.get(
                    "pays",
                    ""
                )
            ).lower():

                continue

        results.append(
            enrich_vehicle(
                vehicle
            )
        )

    # --------------------------------------------------------
    # TRI
    # --------------------------------------------------------

    results.sort(

        key=lambda x: (

            x.get(
                "score",
                0
            ),

            x.get(
                "marge_nette",
                0
            )

        ),

        reverse=True
    )

    return jsonify(
        results
    )


# ============================================================
# IMPORT MOBILE.DE
# ============================================================

@app.route(
    "/api/import/mobile",
    methods=["POST"]
)
def import_mobile():

    data = (
        request
        .get_json(
            silent=True
        )
        or {}
    )

    mobile_ad_id = str(
        data.get(
            "mobileAdId"
        ) or ""
    ).strip()

    if not mobile_ad_id:

        return jsonify({

            "success":
                False,

            "error":
                "mobileAdId obligatoire"

        }), 400

    url = (
        "https://suchen.mobile.de/"
        "fahrzeuge/details.html?id="
        + mobile_ad_id
    )

    return jsonify({

        "success":
            True,

        "mobileAdId":
            mobile_ad_id,

        "url":
            url

    })


# ============================================================
# ROOT
# ============================================================

@app.route(
    "/",
    methods=["GET"]
)
def root():

    return send_from_directory(
        ".",
        "index.html"
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=5000,

        debug=False

    )
