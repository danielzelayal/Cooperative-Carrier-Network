import math

class Node:
    def __init__(self, _id:str, _name:str, _x:int = 0, _y:int = 0):
        self.id = _id
        self.name = _name
        self.x = int(_x)
        self.y = int(_y)

    def measureDistanceFrom(self, anotherNode) -> int:
        distance = math.sqrt((self.x - anotherNode.x)**2 + (self.y - anotherNode.y) **2)
        if distance % 10 > 5:
            distance = int(distance) + 1
        else:
            distance = int(distance)
        return distance