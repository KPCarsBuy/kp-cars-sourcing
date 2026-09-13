from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

vehicles = []


@app.route("/")
def home():
    return jsonify({
        "status": "online",
        "app": "KP Cars",
        "message": "KP Cars API opérationnelle"
    })


@app.route("/api/vehicles", methods=["GET"])
def get_vehicles():
    return jsonify(vehicles)


@app.route("/api/vehicles", methods=["POST"])
def add_vehicle():
    data = request.get_json()

    vehicle = {
        "id": len(vehicles) + 1,
        "marque": data.get("marque", ""),
        "modele": data.get("modele", ""),
        "annee": data.get("annee", ""),
        "kilometrage": data.get("kilometrage", 0),
        "prix_achat": data.get("prix_achat", 0),
        "prix_vente": data.get("prix_vente", 0),
        "source": data.get("source", ""),
        "url": data.get("url", "")
    }

    vehicle["marge"] = (
        float(vehicle["prix_vente"] or 0)
        - float(vehicle["prix_achat"] or 0)
    )

    vehicles.append(vehicle)

    return jsonify(vehicle), 201


@app.route("/api/vehicles/<int:vehicle_id>", methods=["DELETE"])
def delete_vehicle(vehicle_id):
    global vehicles

    vehicles = [
        vehicle for vehicle in vehicles
        if vehicle["id"] != vehicle_id
    ]

    return jsonify({"success": True})


@app.route("/api/search", methods=["POST"])
def search():
    criteria = request.get_json()

    results = []

    for vehicle in vehicles:
        if criteria.get("marque"):
            if criteria["marque"].lower() not in vehicle["marque"].lower():
                continue

        if criteria.get("modele"):
            if criteria["modele"].lower() not in vehicle["modele"].lower():
                continue

        if criteria.get("annee_min"):
            if int(vehicle["annee"] or 0) < int(criteria["annee_min"]):
                continue

        if criteria.get("km_max"):
            if int(vehicle["kilometrage"] or 0) > int(criteria["km_max"]):
                continue

        if criteria.get("prix_max"):
            if float(vehicle["prix_achat"] or 0) > float(criteria["prix_max"]):
                continue

        results.append(vehicle)

    return jsonify(results)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
