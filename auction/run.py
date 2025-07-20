import time
from core import CarrierModel

if __name__ == "__main__":
    model = CarrierModel(n_carriers=3)
    for _ in range(20):   # run 20 times
        model.step()
        #print(f"Finished cycle {model.tick // 5}, "
        #      f"last winner: {model.last_auction_result.get('winner')}")
        #time.sleep(0.5)
