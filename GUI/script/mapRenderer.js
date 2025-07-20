// js/mapRenderer.js

export const mapRenderer = (() => {
    let ctx = null;
    let canvas = null;
    let scale = 1;
    let offsetX = 0;
    let offsetY = 0;

    function init(canvasElement) {
        canvas = canvasElement;
        ctx = canvas.getContext('2d');
    }

    function worldToScreen(worldX, worldY) {
        return {
            x: (worldX * scale) + offsetX,
            y: (worldY * scale) + offsetY
        };
    }

    function drawNode(screenCoords, label, color, radius, isSelected = false) {
        if (!ctx) return;
        ctx.beginPath();
        ctx.arc(screenCoords.x, screenCoords.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.strokeStyle = 'black';
        ctx.lineWidth = 1;
        ctx.stroke();

        ctx.fillStyle = 'black';
        ctx.font = '12px Arial';
        ctx.textAlign = 'center';
        let displayLabel = label;
        /*if (label.includes('+')) {
            displayLabel += ' (P)';
        } else if (label.includes('-')) {
            displayLabel += ' (D)';
        }*/
        ctx.fillText(displayLabel, screenCoords.x, screenCoords.y - radius - 5);

        if (isSelected) {
            ctx.beginPath();
            ctx.arc(screenCoords.x, screenCoords.y, radius + 3, 0, Math.PI * 2);
            ctx.strokeStyle = 'rgba(0, 255, 0, 0.5)';
            ctx.lineWidth = 2;
            ctx.stroke();
        }
    }

    function drawArrow(fromScreen, toScreen, ctx, color) {
        const headlen = 10;
        const angle = Math.atan2(toScreen.y - fromScreen.y, toScreen.x - fromScreen.x);
        ctx.strokeStyle = color;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(toScreen.x, toScreen.y);
        ctx.lineTo(toScreen.x - headlen * Math.cos(angle - Math.PI / 6), toScreen.y - headlen * Math.sin(angle - Math.PI / 6));
        ctx.moveTo(toScreen.x, toScreen.y);
        ctx.lineTo(toScreen.x - headlen * Math.cos(angle + Math.PI / 6), toScreen.y - headlen * Math.sin(angle + Math.PI / 6));
        ctx.stroke();
    }

    function drawMap(availableNodes, warehouseCoords, selectedNodes = null) {
        if (!ctx || !canvas) return;

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // grid
        ctx.strokeStyle = '#e0e0e0';
        ctx.lineWidth = 0.5;

        const worldMinX = (-offsetX) / scale;
        const worldMinY = (-offsetY) / scale;
        const worldMaxX = (canvas.width - offsetX) / scale;
        const worldMaxY = (canvas.height - offsetY) / scale;

        for (let y = Math.floor(worldMinY / 50) * 50; y <= worldMaxY; y += 50) {
            const screenY = worldToScreen(0, y).y;
            ctx.beginPath();
            ctx.moveTo(0, screenY);
            ctx.lineTo(canvas.width, screenY);
            ctx.stroke();
        }
        for (let x = Math.floor(worldMinX / 50) * 50; x <= worldMaxX; x += 50) {
            const screenX = worldToScreen(x, 0).x;
            ctx.beginPath();
            ctx.moveTo(screenX, 0);
            ctx.lineTo(screenX, canvas.height);
            ctx.stroke();
        }

        // warehouse
        if (warehouseCoords) {
            const screenCoords = worldToScreen(warehouseCoords.x, warehouseCoords.y);
            drawNode(screenCoords, 'Warehouse', 'blue', 8);
        }

        // nodes
        availableNodes.forEach(node => {
            var isSelected = false
            if (selectedNodes){
                isSelected = selectedNodes.has(node.id);
            }
            const screenCoords = worldToScreen(node.coords.x, node.coords.y);
            drawNode(screenCoords, node.name, isSelected ? 'green' : 'red', 6, isSelected);
        });
    }

    function drawRoute(availableNodes, warehouseCoords, route = null, strokeStyle = '#2196F3'){
        // route
        if (route && route.length > 1) {
            let currentWorldCoordsMap = new Map(availableNodes.map(node => [node.id, node.coords]));
            
            // include customed warehouse location into currentWorldCoordsMap
            currentWorldCoordsMap.set('N99', warehouseCoords);

            // warehouse
            if (warehouseCoords) {
                const screenCoords = worldToScreen(warehouseCoords.x, warehouseCoords.y);
                drawNode(screenCoords, 'Warehouse', 'blue', 8);
            }

            // draw lines to connect every two nodes
            for (let i = 1; i < route.length; i++) {
                const previousNodeId = route[i - 1];
                const currentNodeId = route[i];

                const previousWorldCoords = currentWorldCoordsMap.get(previousNodeId);
                const currentWorldCoords = currentWorldCoordsMap.get(currentNodeId);

                if (previousWorldCoords && currentWorldCoords) {
                    const previousScreenCoords = worldToScreen(previousWorldCoords.x, previousWorldCoords.y);
                    const currentScreenCoords = worldToScreen(currentWorldCoords.x, currentWorldCoords.y);

                    ctx.strokeStyle = strokeStyle;
                    ctx.lineWidth = 3;
                    ctx.beginPath();
                    ctx.moveTo(previousScreenCoords.x, previousScreenCoords.y);
                    ctx.lineTo(currentScreenCoords.x, currentScreenCoords.y);
                    ctx.stroke();

                    // draw arrow on the destination node
                    drawArrow(previousScreenCoords, currentScreenCoords, ctx, '#2196F3');
                } else {
                    console.warn(`Warning: Could not find coordinates for route segment: ${previousNodeId} -> ${currentNodeId}. Previous Coords: ${previousWorldCoords ? 'Found' : 'Undefined'}, Current Coords: ${currentWorldCoords ? 'Found' : 'Undefined'}`);
                }
            }
        }
    }

    // fit the screem with all provided nodes
    function autoFitView(nodes, warehouseCoords) {
        if (nodes.length === 0 && !warehouseCoords) {
            scale = 1;
            offsetX = canvas.width / 2;
            offsetY = canvas.height / 2;
            return;
        }

        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;

        nodes.forEach(node => {
            minX = Math.min(minX, node.coords.x);
            minY = Math.min(minY, node.coords.y);
            maxX = Math.max(maxX, node.coords.x);
            maxY = Math.max(maxY, node.coords.y);
        });

        if (warehouseCoords) {
            minX = Math.min(minX, warehouseCoords.x);
            minY = Math.min(minY, warehouseCoords.y);
            maxX = Math.max(maxX, warehouseCoords.x);
            maxY = Math.max(maxY, warehouseCoords.y);
        }

        if (minX === Infinity) {
            scale = 1;
            offsetX = canvas.width / 2;
            offsetY = canvas.height / 2;
            return;
        }

        const padding = 50;
        const desiredWidth = (maxX - minX);
        const desiredHeight = (maxY - minY);

        const actualWidth = Math.max(desiredWidth, 100);
        const actualHeight = Math.max(desiredHeight, 100);

        const scaleX = (canvas.width - padding * 2) / actualWidth;
        const scaleY = (canvas.height - padding * 2) / actualHeight;

        scale = Math.min(scaleX, scaleY);
        scale = Math.max(0.1, Math.min(scale, 5));

        const centerXWorld = minX + desiredWidth / 2;
        const centerYWorld = minY + desiredHeight / 2;

        const canvasCenterX = canvas.width / 2;
        const canvasCenterY = canvas.height / 2;

        offsetX = canvasCenterX - (centerXWorld * scale);
        offsetY = canvasCenterY - (centerYWorld * scale);
    }

    function setScale(newScale) {
        scale = newScale;
    }

    function getScale() {
        return scale;
    }

    function setOffset(dx, dy) {
        offsetX += dx;
        offsetY += dy;
    }

    function getOffset() {
        return { x: offsetX, y: offsetY };
    }

    return {
        init,
        drawMap,
        drawRoute,
        autoFitView,
        worldToScreen, // return for drag and move
        setScale,
        getScale,
        setOffset,
        getOffset
    };
})();