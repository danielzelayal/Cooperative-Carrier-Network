// GUI/script/dataManager.js

export const dataManager = (() => {
    let _availableNodes = [];
    let _selectedNodes = new Set();
    let _warehouseLocation = null;

    function parseCoordinates(coordString) {
        const parts = coordString.split(',').map(part => parseFloat(part.trim()));
        if (parts.length == 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
            return { x: parts[0], y: parts[1] };
        }
        return null;
    }

    async function readNodesFromCSVFile(path = "/models/input/nodeInfo.csv") {        
        try {
            const response = await fetch(path);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status} - Could not load CSV file from ${path}`);
            }
            const csvText = await response.text();

            const result = Papa.parse(csvText, {
                header: true,
                skipEmptyLines: true,
                transformHeader: header => header.trim()
            });

            _availableNodes = result.data.map(
                row => ({
                    id: row.Node_ID,
                    name: row.Node_Name,
                    role: row.Node_Name.includes('+') ? 'pickup' : row.Node_Name.includes('-') ? 'delivery' : 'other',
                    coords: {
                        x: parseFloat(row.x),
                        y: parseFloat(row.y)
                    }
                })
            ).filter(node => !isNaN(node.coords.x) && !isNaN(node.coords.y));

            return _availableNodes;
        } catch (err) {
            console.error("error reading the csv file:", err);
            return [];
        }
    }

    function toggleNodeSelection(nodeId) {
        if (_selectedNodes.has(nodeId)) {
            _selectedNodes.delete(nodeId);
        } else {
            _selectedNodes.add(nodeId);
        }
    }

    function setWarehouseLocation(locationString) {
        _warehouseLocation = parseCoordinates(locationString);
    }

    return {
        readNodesFromCSVFile,
        getAvailableNodes: () => _availableNodes,
        getSelectedNodeIds: () => Array.from(_selectedNodes),
        getSelectedNodesData: () => {
            return Array.from(_selectedNodes).map(
                id => {
                    const node = _availableNodes.find(n => n.id === id);
                    return node ? { id: node.id, x: node.coords.x, y: node.coords.y } : null;
                }
            ).filter(Boolean); // removed nodes impossible to exist
        },
        toggleNodeSelection,
        getWarehouseLocation: () => _warehouseLocation,
        setWarehouseLocation,

        // served as APIs, open for others to use
        parseCoordinates
    };
})();