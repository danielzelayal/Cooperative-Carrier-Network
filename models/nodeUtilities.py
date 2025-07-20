import csv, os, pandas as pd

from models import node

# define path
PATH_MODELS = os.path.dirname(os.path.abspath(__file__))
PATH_INPUT = os.path.join(PATH_MODELS, 'input')
PATH_METADATA = os.path.join(PATH_MODELS, 'metadata')

def addWarehouseInfoToCSV(warehouse_x:int, warehouse_y:int):

    PATH_ORIGINAL_CSV = os.path.join(PATH_INPUT, 'nodeInfo.csv')
    PATH_UPDATED_CSV = os.path.join(PATH_INPUT, 'nodeInfoFromGUI.csv')

    df = pd.read_csv(PATH_ORIGINAL_CSV)
    df.loc[len(df)] = ['N99', 'WAREHOUSE', warehouse_x, warehouse_y]
    df.to_csv(PATH_UPDATED_CSV, index=False)

def readNodeInformation(file_name = "nodeInfo.csv") -> list[node.Node]:

    PATH_FILE = os.path.join(PATH_INPUT, file_name)

    with open(PATH_FILE) as csv_file:
        node_info = list(csv.reader(csv_file))

    nodes:list[node.Node] = []

    for every_node in node_info[1:]:
        nodes.append(
            node.Node(every_node[0], every_node[1], every_node[2], every_node[3])
            )
    
    return nodes

def writeTravelMatrix(nodes:list[node.Node], file_name = "travelMatrix.csv"):

    PATH_MATRIX = os.path.join(PATH_METADATA, file_name)
    def getAllNodeID() -> list[str]:

        node_ID:list[str] = []
        
        for every_node in nodes:
            node_ID.append(every_node.id)

        return node_ID
    
    # create a folder if not exist
    os.makedirs(os.path.dirname(PATH_MATRIX), exist_ok=True)

    node_ID = getAllNodeID()

    with open(PATH_MATRIX, 'w', newline='') as csvFile:
        spamwriter = csv.writer(csvFile, quoting=csv.QUOTE_MINIMAL)
        spamwriter.writerow(["Distance"] + node_ID)

        for every_node in nodes:
            distance:list[float] = []
            for _ in nodes:
                distance.append(every_node.measureDistanceFrom(_))

            spamwriter.writerow([every_node.id] + distance)

def produceDemandList(selected_nodes:list[dict]) -> list[int]:

    selected_nodes_index = []
    demandList = [0]* getNumberOfNodes('nodeInfoFromGUI.csv')

    for every_node in selected_nodes:
        node_index = int(every_node["id"][1:])
        selected_nodes_index.append(node_index)

    for i in selected_nodes_index:
        demandList[i] = -1
    demandList[-1] = len(selected_nodes_index)

    return demandList

# TODO
def convertDictionaryIntoNodes(selected_nodes:list[dict]) -> list[node.Node]:
    pass

def getNodeIDWithIndex(index:int = 0) -> str:
    nodes = readNodeInformation("nodeInfoFromGUI.csv")
    return(nodes[index].id)


def getNodeWithNodeID(ID:str) -> node.Node:
    nodes = readNodeInformation("nodeInfoFromGUI.csv")
    for i in nodes:
        if i.id == ID:
            return i
        
def getNumberOfNodes(file_name = 'nodeInfo.csv'):
    PATH_UPDATED_CSV = os.path.join(PATH_INPUT, file_name)
    with open(PATH_UPDATED_CSV) as csv_file:
        return len(list(csv.reader(csv_file)))-1