from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

import os
import json
import base64
import urllib.parse
import urllib.request
import statistics
from datetime import datetime

app = Flask(__name__)
CORS(app)


# ============================================================
# KP CARS — CONFIGURATION
# ============================================================

FRAIS_TRANSPORT = 750
FRAIS_ADMIN = 250
RESERVE_PREPARATION = 500

# Marge minimale que KP Cars souhaite conserver
MARGE_MINIMUM = 1000

# Marge de sécurité supplémentaire avant le prix maximum d'achat
BUFFER_SECURITE = 300


# ============================================================
# MOBILE.DE API
# ============================================================

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
# SOURCES / MÉTHODOLOGIE
# ============================================================

SOURCES = {
    "achat": "mobile.de Search API",
    "valorisation": "comparables du marché belge",
    "methodologie": (
        "Comparaison par marque, modèle, année, "
        "kilométrage, carburant, puissance et transmission."
    )
}


# ============================================================
# VEHICULES DE TEST
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
        "url": "",
        "carburant": "Essence",
        "puissance_kw": 55,
        "boite": "Manuelle"
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
        "url": "",
        "carburant": "Essence",
        "puissance_kw": 55,
        "boite": "Manuelle"
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
        "url": "",
        "carburant": "Essence",
        "puissance_kw": 55,
        "boite": "Manuelle"
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
        "url": "",
        "carburant": "Essence",
        "puissance_kw": 55,
        "boite": "Manuelle"
    }
]


# ============================================================
# UTILITAIRES
# ============================================================

def safe_float(value, default=0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except:
        return default


def safe_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except:
        return default


def normalize_text(value):
    return str(value or "").strip().lower()


def build_source_url(source, source_id, url=""):

    if url:
        return url

    if (
        normalize_text(source) == "mobile.de"
        and str(source_id).isdigit()
    ):
        return (
            "https://suchen.mobile.de/"
            "fahrzeuge/details.html?id="
            + str(source_id)
        )

    return ""


# ============================================================
# MARCHÉ BELGE — COMPARABLES
# ============================================================
#
# IMPORTANT :
# Ces valeurs ne sont PAS présentées comme des données
# live AutoScout24.
#
# Le moteur utilise uniquement des comparables explicitement
# fournis à l'API.
#
# Cela permet ensuite de connecter une vraie source de
# comparables sans inventer de prix.
#
# Format :
#
# {
#   marque,
#   modele,
#   annee,
#   kilometrage,
#   prix,
#   carburant,
#   puissance_kw,
#   boite
# }
#
# ============================================================

market_comparables = []


# ============================================================
# AJOUTER UN COMPARABLE BELGE
# ============================================================

@app.route(
    "/api/market/comparable",
    methods=["POST"]
)
def add_market_comparable():

    data = request.get_json(
        silent=True
    ) or {}

    required = [
        "marque",
        "modele",
        "annee",
        "kilometrage",
        "prix"
    ]

    for field in required:

        if field not in data:

            return jsonify({
                "success": False,
                "error":
                    "Champ obligatoire : "
                    + field
            }), 400

    comparable = {
        "marque":
            str(data.get("marque")).strip(),

        "modele":
            str(data.get("modele")).strip(),

        "annee":
            safe_int(data.get("annee")),

        "kilometrage":
            safe_int(data.get("kilometrage")),

        "prix":
            safe_float(data.get("prix")),

        "carburant":
            str(
                data.get("carburant")
                or ""
            ).strip(),

        "puissance_kw":
            safe_float(
                data.get(
                    "puissance_kw"
                )
            ),

        "boite":
            str(
                data.get("boite")
                or ""
            ).strip()
    }

    market_comparables.append(
        comparable
    )

    return jsonify({
        "success": True,
        "comparable": comparable,
        "total_comparables":
            len(market_comparables)
    })


# ============================================================
# LISTE DES COMPARABLES
# ============================================================

@app.route(
    "/api/market/comparables",
    methods=["GET"]
)
def get_market_comparables():

    return jsonify({
        "source":
            "Comparables marché belge KP Cars",

        "count":
            len(market_comparables),

        "comparables":
            market_comparables
    })


# ============================================================
# CALCUL DE SIMILARITÉ
# ============================================================

def comparable_similarity(vehicle, comparable):

    score = 0

    # --------------------------------------------------------
    # MARQUE
    # --------------------------------------------------------

    if normalize_text(
        vehicle.get("marque")
    ) == normalize_text(
        comparable.get("marque")
    ):

        score += 30

    else:

        return 0

    # --------------------------------------------------------
    # MODELE
    # --------------------------------------------------------

    if normalize_text(
        vehicle.get("modele")
    ) == normalize_text(
        comparable.get("modele")
    ):

        score += 30

    else:

        return 0

    # --------------------------------------------------------
    # ANNEE
    # --------------------------------------------------------

    vehicle_year = safe_int(
        vehicle.get("annee")
    )

    comp_year = safe_int(
        comparable.get("annee")
    )

    year_difference = abs(
        vehicle_year - comp_year
    )

    if year_difference == 0:
        score += 15

    elif year_difference == 1:
        score += 12

    elif year_difference == 2:
        score += 9

    elif year_difference == 3:
        score += 5

    else:
        score += 1

    # --------------------------------------------------------
    # KILOMETRAGE
    # --------------------------------------------------------

    vehicle_km = safe_int(
        vehicle.get("kilometrage")
    )

    comp_km = safe_int(
        comparable.get("kilometrage")
    )

    if vehicle_km > 0 and comp_km > 0:

        km_difference = abs(
            vehicle_km - comp_km
        )

        if km_difference <= 10000:
            score += 15

        elif km_difference <= 25000:
            score += 12

        elif km_difference <= 40000:
            score += 8

        elif km_difference <= 60000:
            score += 4

    # --------------------------------------------------------
    # CARBURANT
    # --------------------------------------------------------

    vehicle_fuel = normalize_text(
        vehicle.get("carburant")
    )

    comp_fuel = normalize_text(
        comparable.get("carburant")
    )

    if (
        vehicle_fuel
        and comp_fuel
        and vehicle_fuel == comp_fuel
    ):

        score += 5

    # --------------------------------------------------------
    # BOITE
    # --------------------------------------------------------

    vehicle_gearbox = normalize_text(
        vehicle.get("boite")
    )

    comp_gearbox = normalize_text(
        comparable.get("boite")
    )

    if (
        vehicle_gearbox
        and comp_gearbox
        and vehicle_gearbox == comp_gearbox
    ):

        score += 5

    return score


# ============================================================
# ESTIMATION DU MARCHÉ BELGE
# ============================================================

def estimate_belgian_value(vehicle):

    # --------------------------------------------------------
    # Recherche des comparables
    # --------------------------------------------------------

    scored = []

    for comparable in market_comparables:

        similarity = comparable_similarity(
            vehicle,
            comparable
        )

        if similarity >= 60:

            scored.append({
                "prix":
                    safe_float(
                        comparable.get("prix")
                    ),

                "similarity":
                    similarity,

                "comparable":
                    comparable
            })

    # --------------------------------------------------------
    # Aucun comparable
    # --------------------------------------------------------

    if not scored:

        return {

            "estimation_disponible":
                False,

            "prix_marche_bas":
                None,

            "prix_marche_central":
                None,

            "prix_marche_haut":
                None,

            "prix_revente_conseille":
                None,

            "confiance":
                "INSUFFISANTE",

            "nombre_comparables":
                0,

            "source":
                "Aucun comparable belge fourni",

            "message":
                (
                    "Impossible de calculer une vraie "
                    "valeur de marché sans comparable "
                    "belge. KP Cars ne fabrique pas "
                    "de prix."
                )
        }

    # --------------------------------------------------------
    # Pondération
    # --------------------------------------------------------

    weighted_values = []

    for item in scored:

        weight = (
            item["similarity"]
            / 100
        )

        weighted_values.append(
            (
                item["prix"],
                weight
            )
        )

    total_weight = sum(
        weight
        for _, weight
        in weighted_values
    )

    if total_weight <= 0:

        return {
            "estimation_disponible": False,
            "confiance": "INSUFFISANTE",
            "nombre_comparables": 0
        }

    weighted_average = (
        sum(
            price * weight
            for price, weight
            in weighted_values
        )
        / total_weight
    )

    # --------------------------------------------------------
    # Distribution des prix
    # --------------------------------------------------------

    prices = [
        item["prix"]
        for item in scored
    ]

    prices.sort()

    if len(prices) >= 3:

        median_price = statistics.median(
            prices
        )

        low_price = prices[
            max(
                0,
                int(
                    len(prices)
                    * 0.20
                )
            )
        ]

        high_index = min(
            len(prices) - 1,
            int(
                len(prices)
                * 0.80
            )
        )

        high_price = prices[
            high_index
        ]

    else:

        median_price = weighted_average

        low_price = weighted_average * 0.90

        high_price = weighted_average * 1.10

    # --------------------------------------------------------
    # Prix conseillé
    # --------------------------------------------------------
    #
    # AutoScout24 explique qu'un prix d'annonce
    # contient généralement une marge de négociation.
    #
    # On ne prend donc pas automatiquement le maximum.
    #
    # --------------------------------------------------------

    prix_revente_conseille = (
        median_price * 0.97
    )

    # --------------------------------------------------------
    # CONFIANCE
    # --------------------------------------------------------

    if len(scored) >= 10:

        confiance = "ÉLEVÉE"

    elif len(scored) >= 5:

        confiance = "BONNE"

    elif len(scored) >= 3:

        confiance = "MOYENNE"

    else:

        confiance = "FAIBLE"

    return {

        "estimation_disponible":
            True,

        "prix_marche_bas":
            round(
                low_price,
                0
            ),

        "prix_marche_central":
            round(
                median_price,
                0
            ),

        "prix_marche_haut":
            round(
                high_price,
                0
            ),

        "prix_revente_conseille":
            round(
                prix_revente_conseille,
                0
            ),

        "confiance":
            confiance,

        "nombre_comparables":
            len(scored),

        "source":
            "Comparables marché belge KP Cars",

        "methode":
            (
                "Comparaison pondérée selon "
                "marque, modèle, année, "
                "kilométrage, carburant, "
                "puissance et transmission."
            )
    }


# ============================================================
# ANALYSE DE RENTABILITÉ
# ============================================================

def calculate_profitability(
    vehicle,
    valuation=None
):

    prix_achat = safe_float(
        vehicle.get(
            "prix_achat"
        )
    )

    transport = safe_float(
        vehicle.get(
            "transport",
            FRAIS_TRANSPORT
        )
    )

    frais_admin = safe_float(
        vehicle.get(
            "frais_admin",
            FRAIS_ADMIN
        )
    )

    preparation = safe_float(
        vehicle.get(
            "preparation",
            RESERVE_PREPARATION
        )
    )

    cout_total = (
        prix_achat
        + transport
        + frais_admin
        + preparation
    )

    # --------------------------------------------------------
    # PRIX DE REVENTE
    # --------------------------------------------------------

    prix_vente = safe_float(
        vehicle.get(
            "prix_vente"
        )
    )

    if (
        valuation
        and valuation.get(
            "estimation_disponible"
        )
    ):

        prix_vente = safe_float(
            valuation.get(
                "prix_revente_conseille"
            )
        )

    # --------------------------------------------------------
    # MARGE
    # --------------------------------------------------------

    marge = (
        prix_vente
        - cout_total
    )

    # --------------------------------------------------------
    # ROI
    # --------------------------------------------------------

    if cout_total > 0:

        roi = (
            marge
            / cout_total
        ) * 100

    else:

        roi = 0

    # --------------------------------------------------------
    # PRIX MAXIMUM D'ACHAT
    # --------------------------------------------------------

    prix_max_achat = None

    if (
        valuation
        and valuation.get(
            "estimation_disponible"
        )
    ):

        valeur_revente = safe_float(
            valuation.get(
                "prix_revente_conseille"
            )
        )

        prix_max_achat = (
            valeur_revente
            - transport
            - frais_admin
            - preparation
            - MARGE_MINIMUM
            - BUFFER_SECURITE
        )

        prix_max_achat = max(
            0,
            round(
                prix_max_achat,
                0
            )
        )

    # --------------------------------------------------------
    # DECISION
    # --------------------------------------------------------

    if (
        valuation
        and valuation.get(
            "estimation_disponible"
        )
    ):

        confiance = valuation.get(
            "confiance",
            "INSUFFISANTE"
        )

        if marge >= 2000 and roi >= 30:
            decision = "ACHETER"

        elif marge >= 1500 and roi >= 25:
            decision = "ACHETER"

        elif marge >= 1000 and roi >= 20:
            decision = "NÉGOCIER"

        elif marge >= 700 and roi >= 15:
            decision = "NÉGOCIER"

        else:
            decision = "PASSER"

    else:

        decision = "À ANALYSER"

        confiance = "INSUFFISANTE"

    return {

        "prix_achat":
            round(
                prix_achat,
                0
            ),

        "transport":
            round(
                transport,
                0
            ),

        "frais_admin":
            round(
                frais_admin,
                0
            ),

        "preparation":
            round(
                preparation,
                0
            ),

        "cout_total":
            round(
                cout_total,
                0
            ),

        "prix_vente":
            round(
                prix_vente,
                0
            ),

        "marge_nette":
            round(
                marge,
                0
            ),

        "roi":
            round(
                roi,
                2
            ),

        "prix_max_achat_kp_cars":
            prix_max_achat,

        "decision":
            decision,

        "confiance":
            confiance
    }


# ============================================================
# SCORE KP CARS
# ============================================================

def calculate_score(
    vehicle,
    profitability,
    valuation
):

    score = 0

    marge = safe_float(
        profitability.get(
            "marge_nette"
        )
    )

    roi = safe_float(
        profitability.get(
            "roi"
        )
    )

    # --------------------------------------------------------
    # MARGE
    # --------------------------------------------------------

    if marge >= 2500:
        score += 35

    elif marge >= 2000:
        score += 30

    elif marge >= 1500:
        score += 25

    elif marge >= 1000:
        score += 20

    elif marge >= 700:
        score += 10

    # --------------------------------------------------------
    # ROI
    # --------------------------------------------------------

    if roi >= 35:
        score += 30

    elif roi >= 30:
        score += 27

    elif roi >= 25:
        score += 24

    elif roi >= 20:
        score += 20

    elif roi >= 15:
        score += 15

    elif roi >= 10:
        score += 8

    # --------------------------------------------------------
    # ANNÉE
    # --------------------------------------------------------

    annee = safe_int(
        vehicle.get(
            "annee"
        )
    )

    current_year = datetime.now().year

    age = (
        current_year
        - annee
    )

    if age <= 5:
        score += 15

    elif age <= 8:
        score += 12

    elif age <= 12:
        score += 8

    elif age <= 16:
        score += 4

    # --------------------------------------------------------
    # KILOMETRAGE
    # --------------------------------------------------------

    km = safe_int(
        vehicle.get(
            "kilometrage"
        )
    )

    if km <= 80000:
        score += 15

    elif km <= 100000:
        score += 13

    elif km <= 125000:
        score += 10

    elif km <= 150000:
        score += 7

    elif km <= 175000:
        score += 3

    # --------------------------------------------------------
    # CONFIANCE
    # --------------------------------------------------------

    confiance = valuation.get(
        "confiance",
        "INSUFFISANTE"
    )

    if confiance == "ÉLEVÉE":
        score += 5

    elif confiance == "BONNE":
        score += 3

    # --------------------------------------------------------
    # OPPORTUNITÉ
    # --------------------------------------------------------

    score = min(
        score,
        100
    )

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

    return {
        "score":
            score,

        "opportunite":
            opportunite
    }


# ============================================================
# ENRICHISSEMENT VEHICULE
# ============================================================

def enrich_vehicle(vehicle):

    valuation = estimate_belgian_value(
        vehicle
    )

    profitability = calculate_profitability(
        vehicle,
        valuation
    )

    score_data = calculate_score(
        vehicle,
        profitability,
        valuation
    )

    result = dict(
        vehicle
    )

    result.update(
        profitability
    )

    result.update(
        score_data
    )

    result["valuation"] = valuation

    result["url"] = build_source_url(
        vehicle.get(
            "source",
            ""
        ),
        vehicle.get(
            "source_id",
            ""
        ),
        vehicle.get(
            "url",
            ""
        )
    )

    return result


# ============================================================
# MOBILE.DE — SOURCING LIVE
# ============================================================

def search_mobile_api(data):

    if (
        not MOBILE_API_USER
        or not MOBILE_API_PASSWORD
    ):

        return None

    marque = str(
        data.get(
            "marque"
        ) or ""
    ).strip()

    modele = str(
        data.get(
            "modele"
        ) or ""
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
        data.get(
            "pays"
        ) or ""
    ).strip()

    # --------------------------------------------------------
    # CLASSIFICATION MOBILE.DE
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
    # PARAMETRES
    # --------------------------------------------------------

    params = {

        "classification":
            classification,

        "page.number":
            "1",

        "page.size":
            "100",

        "sort.field":
            "price",

        "sort.order":
            "ASCENDING"
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
        ] = (
            str(
                annee_min
            )
            + "-01"
        )

    if pays in COUNTRY_CODES:

        params["country"] = (
            COUNTRY_CODES[pays]
        )

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

    api_request = (
        urllib.request.Request(

            api_url,

            headers={

                "Accept":
                    "application/vnd.de.mobile.api+json",

                "Authorization":
                    "Basic "
                    + encoded_credentials
            }
        )
    )

    # --------------------------------------------------------
    # APPEL
    # --------------------------------------------------------

    try:

        with urllib.request.urlopen(
            api_request,
            timeout=20
        ) as response:

            raw = (
                response
                .read()
                .decode(
                    "utf-8"
                )
            )

            payload = json.loads(
                raw
            )

    except Exception as error:

        print(
            "Erreur mobile.de:",
            error
        )

        return []

    ads = payload.get(
        "ads",
        []
    )

    results = []

    # --------------------------------------------------------
    # CONVERSION
    # --------------------------------------------------------

    for ad in ads:

        source_id = str(
            ad.get(
                "mobileAdId",
                ""
            )
        )

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

        kilometrage = safe_int(
            ad.get(
                "mileage"
            )
        )

        prix_achat = 0

        price_data = ad.get(
            "price"
        )

        if isinstance(
            price_data,
            dict
        ):

            prix_achat = safe_float(

                price_data.get(
                    "consumerPriceGross"
                )

                or price_data.get(
                    "consumerPriceNet"
                )

                or price_data.get(
                    "dealerPriceGross"
                )
            )

        else:

            prix_achat = safe_float(
                price_data
            )

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

            "prix_vente":
                0,

            "pays":
                pays or "Allemagne",

            "url":
                (
                    "https://suchen.mobile.de/"
                    "fahrzeuge/details.html?id="
                    + source_id
                ),

            "carburant":
                ad.get(
                    "fuel",
                    ""
                ),

            "puissance_kw":
                safe_float(
                    ad.get(
                        "power"
                    )
                ),

            "boite":
                ad.get(
                    "transmission",
                    ""
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
            ),

        "market_comparables":
            len(
                market_comparables
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
            configured,

        "market_valuation":
            (
                "ACTIVE"
                if len(
                    market_comparables
                ) > 0
                else "WAITING_FOR_COMPARABLES"
            )
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
# API VALUATION
# ============================================================

@app.route(
    "/api/valuation",
    methods=["POST"]
)
def valuation_api():

    data = (
        request
        .get_json(
            silent=True
        )
        or {}
    )

    valuation = (
        estimate_belgian_value(
            data
        )
    )

    profitability = (
        calculate_profitability(
            data,
            valuation
        )
    )

    score = (
        calculate_score(
            data,
            profitability,
            valuation
        )
    )

    return jsonify({

        "vehicle":
            data,

        "valuation":
            valuation,

        "profitability":
            profitability,

        "score":
            score,

        "sources":
            SOURCES
    })


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
    # LIVE MOBILE.DE
    # --------------------------------------------------------

    live_results = (
        search_mobile_api(
            data
        )
    )

    if live_results is not None:

        return jsonify(
            live_results
        )

    # --------------------------------------------------------
    # MODE DEMO
    # --------------------------------------------------------

    marque = normalize_text(
        data.get(
            "marque"
        )
    )

    modele = normalize_text(
        data.get(
            "modele"
        )
    )

    annee_min = data.get(
        "annee_min"
    )

    km_max = data.get(
        "km_max"
    )

    prix_max = data.get(
        "prix_max"
    )

    pays = normalize_text(
        data.get(
            "pays"
        )
    )

    results = []

    for vehicle in vehicles:

        if marque:

            if marque not in normalize_text(
                vehicle.get(
                    "marque"
                )
            ):

                continue

        if modele:

            if modele not in normalize_text(
                vehicle.get(
                    "modele"
                )
            ):

                continue

        if annee_min:

            if safe_int(
                vehicle.get(
                    "annee"
                )
            ) < safe_int(
                annee_min
            ):

                continue

        if km_max:

            if safe_int(
                vehicle.get(
                    "kilometrage"
                )
            ) > safe_int(
                km_max
            ):

                continue

        if prix_max:

            if safe_float(
                vehicle.get(
                    "prix_achat"
                )
            ) > safe_float(
                prix_max
            ):

                continue

        if pays:

            if pays not in normalize_text(
                vehicle.get(
                    "pays"
                )
            ):

                continue

        results.append(
            enrich_vehicle(
                vehicle
            )
        )

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
