// js/uiHandlers.js

import { mapRenderer } from './mapRenderer.js';
import { dataManager } from './dataManager.js';

export const uiHandlers = (() => {
    let _mapCanvas = null;
    let _nodeList = null;
    let _warehouseLocationInput = null;
    let _submitButton = null;
    let _showAuctionResultBtn = null;
    let _zoomInBtn = null;
    let _zoomOutBtn = null;
    let _resetViewBtn = null;

    let isDragging = false;
    let lastX, lastY;

    let _lastSimRoute   = null;   // {route_map_ID:[…], warehouse_location:[x,y]}
    let _visibleRoutes  = {C0:true, C1:true, C2:true};   // checkbox state

    function renderNodeList() {
        _nodeList.innerHTML = '';
        const availableNodes = dataManager.getAvailableNodes();
        const selectedNodeIds = new Set(dataManager.getSelectedNodeIds());

        availableNodes.forEach(node => {
            const listItem = document.createElement('li');
            listItem.className = 'mdc-list-item';
            listItem.setAttribute('data-node-id', node.id);

            const listItemGraphic = document.createElement('span');
            listItemGraphic.className = 'mdc-list-item__graphic material-icons';
            listItemGraphic.setAttribute('aria-hidden', 'true');
            listItemGraphic.textContent = selectedNodeIds.has(node.id) ? 'check_box' : 'check_box_outline_blank';

            const listItemText = document.createElement('span');
            listItemText.className = 'mdc-list-item__text';
            listItemText.textContent = `${node.name} (${node.coords.x}, ${node.coords.y})`;

            listItem.appendChild(listItemGraphic);
            listItem.appendChild(listItemText);

            listItem.addEventListener('click', () => {
                dataManager.toggleNodeSelection(node.id);
                renderNodeList();
                drawEverything();
            });

            _nodeList.appendChild(listItem);
        });
    }

    let _lastSnapshots = [];
    function drawMapEssentials() {
        const availableNodes = dataManager.getAvailableNodes();
        const selectedNodeIds = new Set(dataManager.getSelectedNodeIds());
        const warehouseCoords = dataManager.getWarehouseLocation();
        console.warn(warehouseCoords)
        mapRenderer.drawMap(availableNodes, warehouseCoords, selectedNodeIds);
    }

    function drawEverything() {
        // 1) base dots & grid
        drawMapEssentials();

        // 2) simulated best route (black)
        if (_lastSimRoute) {
            mapRenderer.drawRoute(
                dataManager.getAvailableNodes(),
                {x:_lastSimRoute.warehouse_location[0],
                y:_lastSimRoute.warehouse_location[1]},
                _lastSimRoute.route_map_ID[0],          // one vehicle
                '#000000'
            );
        }

        // 3) auction snapshots
        if (typeof _lastSnapshots !== 'undefined') {
            const colors = ["#E63946","#457B9D","#2A9D8F","#F4A261","#6A4C93"];
            _lastSnapshots.forEach((snap, idx) => {
                const cid = `C${idx}`;
                if (!snap.route_map_ID || !_visibleRoutes[cid]) return;
                const wh = {x: snap.warehouse_location[0], y: snap.warehouse_location[1]};
                snap.route_map_ID.forEach(routeID =>
                    mapRenderer.drawRoute(
                        dataManager.getAvailableNodes(),
                        wh,
                        routeID,
                        colors[idx % colors.length]
                    )
                );
            });
        }
    }


    async function handleSubmit() {
        const warehouseLocationString = _warehouseLocationInput.value.trim();
        const selectedNodesData = dataManager.getSelectedNodesData();

        if (!warehouseLocationString || selectedNodesData.length === 0) {
            //alert('Enter the warehouse location and select at least one node.');
            return;
        }

        const warehouseCoords = dataManager.parseCoordinates(warehouseLocationString);
        if (!warehouseCoords) {
            alert('Wrong format for warehouse location. Please use "x,y" format (e.g., 10,20 or -5,30).');
            return;
        }
        dataManager.setWarehouseLocation(warehouseLocationString); // update the coordinatation of warehouse in dataManager

        const requestData = {
            warehouse: { x: warehouseCoords.x, y: warehouseCoords.y },
            nodes: selectedNodesData
        };

        // console.log('send data to the backend:', requestData);

        try {
            const response = await fetch('http://localhost:8001/calculate_route', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });
            if (result && result.route_map_ID) {
                _lastSimRoute = result;        // cache for persistence
                drawEverything();
            } else { alert('No result for the route'); }


            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            // console.info(result)

            if (result) {
                _lastSimRoute = result;      // cache it
                drawEverything();
            } else { alert('no result'); }


        } catch (error) {
            console.error('error solving the routing problem:', error);
            alert('error solving the routing problem');
        }
    }

    async function showAuctionResult() {
        // 1. kick off a new auction run
        const startResp = await fetch('http://localhost:8001/run_one_auction', {method: 'POST'});
        const startJson = await startResp.json();
        if (!startJson.started) {
            alert("Auction is already running — please wait.");
            return;
        }

        // 2. poll for live snapshots every 2 s
        const strokeColors = ["#E63946", "#457B9D", "#2A9D8F"];
        const pollId = setInterval(async () => {
            const r = await fetch('http://localhost:8001/api/carrier_routes')
                            .then(res => res.json());
            _lastSnapshots = r.snapshots;
            // redraw map
            drawEverything();
            r.snapshots.forEach((snap, idx) => {
                if (!snap.route_map_ID) return;
                const warehouse = {x: snap.warehouse_location[0],
                                y: snap.warehouse_location[1]};
                dataManager.setWarehouseLocation(`${warehouse.x},${warehouse.y}`);
                snap.route_map_ID.forEach(routeID => {
                    mapRenderer.drawRoute(
                        dataManager.getAvailableNodes(),
                        warehouse,
                        routeID,
                        strokeColors[idx % strokeColors.length]
                    );
                });
            });

            // 3. stop when finished
            if (r.finished && !r.running) {
                clearInterval(pollId);
                let lines = [`Initial total: ${r.profit_before_total+" €"}`,
                `Final total:   ${r.profit_after_total+" €"}`,
                    '-------------'];
                Object.keys(r.profit_before).forEach(cid => {
                    lines.push(`${cid}: ${r.profit_before[cid]+" €"}  →  ${r.profit_after[cid]+" €"}`);
                });
                alert(lines.join('\n'));
            }

        }, 2000);
    }



    function setupEventListeners() {
        _submitButton.addEventListener('click', handleSubmit);

        _showAuctionResultBtn.addEventListener('click', showAuctionResult);

        _zoomInBtn.addEventListener('click', () => {
            mapRenderer.setScale(mapRenderer.getScale() * 1.2);
            drawEverything();
        });

        _zoomOutBtn.addEventListener('click', () => {
            mapRenderer.setScale(mapRenderer.getScale() / 1.2);
            drawEverything();
        });

        _resetViewBtn.addEventListener('click', () => {
            mapRenderer.autoFitView(dataManager.getAvailableNodes(), dataManager.getWarehouseLocation());
            drawEverything();
        });

        _warehouseLocationInput.addEventListener('input', () => {
            dataManager.setWarehouseLocation(_warehouseLocationInput.value.trim());
            drawEverything();
        });


        // drag and move the map
        _mapCanvas.addEventListener('mousedown', (e) => {
            isDragging = true;
            lastX = e.clientX;
            lastY = e.clientY;
            _mapCanvas.style.cursor = 'grabbing';
        });

        _mapCanvas.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            const dx = e.clientX - lastX;
            const dy = e.clientY - lastY;
            mapRenderer.setOffset(dx, dy);
            lastX = e.clientX;
            lastY = e.clientY;
            drawEverything();
        });

        _mapCanvas.addEventListener('mouseup', () => {
            isDragging = false;
            _mapCanvas.style.cursor = 'grab';
        });

        _mapCanvas.addEventListener('mouseleave', () => {
            isDragging = false;
            _mapCanvas.style.cursor = 'grab';
        });

        // zoom in/ out
        _mapCanvas.addEventListener('wheel', (e) => {
            e.preventDefault();

            const zoomFactor = 1.1;
            const canvasRect = _mapCanvas.getBoundingClientRect();
            const mouseX = e.clientX - canvasRect.left;
            const mouseY = e.clientY - canvasRect.top;

            const currentOffset = mapRenderer.getOffset();
            const currentScale = mapRenderer.getScale();
            const worldXBeforeZoom = (mouseX - currentOffset.x) / currentScale;
            const worldYBeforeZoom = (mouseY - currentOffset.y) / currentScale;

            let newScale;
            if (e.deltaY < 0) { // roll up (zoom in)
                newScale = currentScale * zoomFactor;
            } else { // roll down (zoom out)
                newScale = currentScale / zoomFactor;
            }

            // set maximum zooming scale
            newScale = Math.max(0.01, Math.min(newScale, 10)); 

            mapRenderer.setScale(newScale);

            const newOffsetX = mouseX - (worldXBeforeZoom * newScale);
            const newOffsetY = mouseY - (worldYBeforeZoom * newScale);
            mapRenderer.setOffset(newOffsetX - currentOffset.x, newOffsetY - currentOffset.y); // setOffset 是增量操作

            drawEverything();
        });
    }

    function initUI(canvasElement, nodeListElement, warehouseInput, submitBtn, showAuctionResultBtn, zoomIn, zoomOut, resetView) {
        _mapCanvas = canvasElement;
        // wire carrier filter check‑boxes
        const filterDiv = document.getElementById('carrierFilters');
        filterDiv.querySelectorAll('input[type="checkbox"]').forEach(cb => {
            _visibleRoutes[cb.dataset.carrier] = cb.checked;      // initialise
            cb.addEventListener('change', () => {
                _visibleRoutes[cb.dataset.carrier] = cb.checked;
                drawEverything();
            });
        });
        _nodeList = nodeListElement;
        _warehouseLocationInput = warehouseInput;
        _submitButton = submitBtn;
        _showAuctionResultBtn = showAuctionResultBtn
        _zoomInBtn = zoomIn;
        _zoomOutBtn = zoomOut;
        _resetViewBtn = resetView;

        setupEventListeners();
    }

    return {
        initUI,
        renderNodeList,
        drawEverything // return for main.js
    };
})();