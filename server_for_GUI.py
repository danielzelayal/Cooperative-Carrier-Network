# server_for_GUI.py

from flask import Flask, request, jsonify, send_from_directory
import os
import json
import subprocess
#import time
import threading
import mimetypes 
from models.pickupDelivery import solve_PnD_problem
#from auction.core import CarrierModel


RUNNING_FLAG = {"running": False} 
profit_before = 0
profit_after  = 0

mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('text/html', '.html')
mimetypes.add_type('text/csv', '.csv')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'GUI'), static_url_path='/')
app.static_folder_agent = os.path.join(BASE_DIR, 'models')

print(f"DEBUG: BASE_DIR is: {BASE_DIR}")
print(f"DEBUG: app.static_folder is: {app.static_folder}")
print(f"DEBUG: app.static_folder_models is: {app.static_folder_agent}")

@app.route('/')
def index():
    return send_from_directory('GUI', 'index.html', mimetype='text/html')

@app.route('/<path:filename>')
def serve_static(filename):
    # service from GUI/
    file_path_in_gui = os.path.join(app.static_folder, filename)
    if os.path.isfile(file_path_in_gui):
        return send_from_directory(app.static_folder, filename)

    # service from project root
    file_path_in_base = os.path.join(BASE_DIR, filename)
    if os.path.isfile(file_path_in_base):
        return send_from_directory(BASE_DIR, filename)

    return "File not found", 404

@app.route('/models/<path:filename>')
def serve_models_static(filename):
    full_path = os.path.join(app.static_folder_agent, filename)
    print(f"DEBUG: Attempting to serve: {full_path}")
    if not os.path.exists(full_path):
        print(f"ERROR: File does not exist at: {full_path}")
        return "File not found", 404 
    return send_from_directory(app.static_folder_agent, filename)

@app.route('/calculate_route', methods=['POST'])
def calculate_route():
    """Simulate best route for user‑selected nodes using our Pickup‑and‑Delivery model."""
    payload = request.get_json()
    warehouse = payload.get("warehouse")      # {'x':…, 'y':…}
    nodes     = payload.get("nodes")          # [{'id':…, 'x':…, 'y':…}, …]

    if not warehouse or not nodes:
        return jsonify({"error": "Missing warehouse or nodes"}), 400
    
    # --- create temporary CSVs ---------------------------------
    import csv, tempfile
    tmp_dir = tempfile.mkdtemp()
    order_csv = os.path.join(tmp_dir, "orders.csv")
    tm_csv    = os.path.join(tmp_dir, "travelMatrix.csv")

    # Write orders: each node pair is just (pickup, delivery) => same id twice
    with open(order_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Order ID(pk)", "pickup", "delivery"])
        for idx, n in enumerate(nodes):
            w.writerow([f"O{idx:02}", n["id"], n["id"]])   # trivial pair

    # Use nodeUtilities to update the travel matrix incl. depot N99
    import models.nodeUtilities as nu
    nu.addWarehouseInfoToCSV(warehouse["x"], warehouse["y"])        # writes N99 line
    nu.writeTravelMatrix(nu.readNodeInformation("nodeInfoFromGUI.csv"), tm_csv)

    # --- solve with 1 vehicle ----------------------------------
    res = solve_PnD_problem(os.path.basename(order_csv), os.path.basename(tm_csv))
    res["warehouse_location"] = [warehouse["x"], warehouse["y"]]
    return jsonify(res)

    
@app.route('/show_auction_result', methods=['POST'])
def run_auction():

    # PATH
    PATH_C0 = "auction/carriers_info/C0_vrp.json"
    PATH_C1 = "auction/carriers_info/C1_vrp.json"
    PATH_C2 = "auction/carriers_info/C2_vrp.json"
    # os.path.dirname(os.path.abspath(__file__))
    # PATH_INPUT = os.path.join(PATH_MODELS, 'input')

    list_of_results:list[dict] = []
    with open(PATH_C0, "r") as f:
        list_of_results.append(json.load(f))

    with open(PATH_C1, "r") as f:
        list_of_results.append(json.load(f))

    with open(PATH_C2, "r") as f:
        list_of_results.append(json.load(f))

    print(list_of_results)

    try:
        return jsonify(list_of_results)
    except Exception as e:
        print("Error solving CVRP:", e)
        return jsonify({"error": f"Backend calculation failed: {str(e)}"}), 500

@app.route('/run_one_auction', methods=['POST'])
def run_one_auction():
    if RUNNING_FLAG["running"]:
        return jsonify({"started": False, "running": True})
    RUNNING_FLAG["running"] = True

    def _worker():
        subprocess.run(["python3", "-m", "auction.run_one", "20", "1.0"])
        RUNNING_FLAG["running"] = False

    threading.Thread(target=_worker, daemon=True).start()
    return jsonify({"started": True, "running": True})

@app.route('/api/carrier_routes', methods=['GET'])
def get_carrier_routes():
    result_list = []
    for i in range(3):
        path = f"auction/carriers_info/C{i}_vrp.json"
        result_list.append(json.load(open(path))) if os.path.exists(path) else result_list.append({})
    # read profit meta
    meta_path = "auction/carriers_info/_meta.json"
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {"finished": False,
                                                                        "profit_before_total": 0,
                                                                        "profit_after_total": 0,
                                                                        "profit_before": {},
                                                                        "profit_after": {}}
    meta["running"] = RUNNING_FLAG["running"]
    meta["snapshots"] = result_list
    return jsonify(meta)

if __name__ == '__main__':
    app.run(host='localhost', port=8001, debug=True) # debug=False when public the project