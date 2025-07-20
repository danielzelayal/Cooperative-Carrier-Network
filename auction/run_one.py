"""
Run one auction simulation and write JSON meta data.

    python -m auction.run_one 20        # 20 ticks (≈ 10 auctions)

Output file:  auction/carriers_info/_meta.json
Schema:
{
  "ticks": 50,
  "profit_before_total": 1234.5,
  "profit_after_total":  1456.7,
  "profit_before": { "C0": 456.7, "C1": 321.0, "C2": 456.8 },
  "profit_after":  { "C0": 678.9, "C1": 400.4, "C2": 377.4 },
  "finished": true
}
"""
import sys, json, os, time
from auction.core import CarrierModel

ticks = int(sys.argv[1]) if len(sys.argv) > 1 else 20
delay  = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
model = CarrierModel(n_carriers=3)

def carrier_profits(model):
    return {c.carrier_id: c.cost_model.profit_information[0]
            for c in model.carriers}

profit_before = carrier_profits(model)

for _ in range(ticks):
    model.step()
    if delay:
        time.sleep(delay) #to visualize better real time route changes

profit_after = carrier_profits(model)
meta = {
    "ticks": ticks,
    "profit_before_total": round(sum(profit_before.values()), 2),
    "profit_after_total":  round(sum(profit_after.values()),  2),
    "profit_before": {k: round(v, 2) for k, v in profit_before.items()},
    "profit_after":  {k: round(v, 2) for k, v in profit_after.items()},
    "finished": True
}

os.makedirs("auction/carriers_info", exist_ok=True)
json.dump(meta,
          open("auction/carriers_info/_meta.json", "w"),
          indent=2)

