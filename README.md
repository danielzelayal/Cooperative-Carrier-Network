# Collaborative Carrier Networks
This project simulates carrier agents using an auction system (Vickrey) to exchange delivery tasks (nodes) based on profit and cost modeling. It uses Mesa for agent-based simulation and OR-Tools for route optimization. Agents interact through an HTTP auction service implemented with FastAPI.

## Author
[Daniel Zelaya](https://github.com/danielzelayal)
![Static Badge](https://img.shields.io/badge/status%3A-in_development-blue)
![GitHub stars](https://img.shields.io/github/stars/danielzelayal/Cooperative-Carrier-Network?style=social)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/Python-3.10-blue.svg)
![Dependencies](https://img.shields.io/badge/dependencies-up%20to%20date-brightgreen)

## Structure 
```
group06/
├── auction/
│   ├── run.py               # Main simulation runner
│   ├── agents.py            # Carrier and Auctioneer agents
│   ├── core.py              # Mesa model + tick control + output files
│   └── network/
│       └── auctioneer_service.py # FastAPI-based auctioneer service, also has Vickrey logic
│
├── models/
│   ├── pickupDelivery.py           # PnD route solving (OR-Tools)
│   ├── costModelBasedOnOrder.py         # Profit & revenue model
│   ├── nodeUtilities.py     # Node info handling (IDs, coordinates)
│   ├── input/
│   │   ├── nodeInfo.csv
│   │   └── nodeInfoFromGUI.csv
│   └── metadata/
│       ├── travelMatrix.csv
│       └── travelMatrixFromGUI.csv
│
├── GUI/
│   ├── index.html
│   ├── style.css
│   └── script/
│       ├── dataManager.js
│       ├── main.js
│       ├── mapRenderer.js
│       └── uiHandlers.js
│
├── server_for_GUI.py
│
├── .venv/                   # Python virtual environment
└── requirements.txt         # All dependencies
```

## 🧪 Setup Instructions

The models should run on a virtual environment to prevent conflicts

```bash
python3 -m venv .venv
source .venv/bin/activate
```

```bash
pip3 install -r requirements.txt
```
or
```bash
pip3 install mesa
pip3 install --pre "mesa[viz]"
```

```
pip3 install -U "mesa[rec]"
```

```
pip3 install flask fastapi uvicorn requests pydantic pandas ortools
```

```bash
pip3 freeze > requirements.txt
```

## 🚀 Running the Simulation

1. Start Auctioneer Servie
```bash
cd auction/network
python3 auctioneer_service.py
```

2. Start GUI
```bash
python3 server_for_GUI.py
```

3. Go to: http://localhost:8001/

4. Click Show Auction Result to visualize route changes and profit

## 💡 Features
- **Agent-based design**: carriers act independently but interact through auctions
- **Auction protocol:** carriers choose nodes to sell and evaluate buying from others
- **Cost model:** customizable per agent (a1, a2, b1, b2 parameters)
- **GUI integration ready:** all output structured for front-end use *ready?


