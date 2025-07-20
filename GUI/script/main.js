// js/main.js

import { mapRenderer } from './mapRenderer.js';
import { dataManager } from './dataManager.js';
import { uiHandlers } from './uiHandlers.js';

document.addEventListener('DOMContentLoaded', async () => {
    // init the Material Components
    mdc.autoInit();

    // DOM elements
    const mapCanvas = document.getElementById('mapCanvas');
    const nodeList = document.getElementById('nodeList');
    const warehouseLocationInput = document.getElementById('warehouseLocation');
    const submitButton = document.querySelector('.submit-button');
    const showAuctionResultBtn = document.getElementById('runAuctionBtn');
    const zoomInBtn = document.getElementById('zoomInBtn');
    const zoomOutBtn = document.getElementById('zoomOutBtn');
    const resetViewBtn = document.getElementById('resetViewBtn');

    mapRenderer.init(mapCanvas);

    uiHandlers.initUI(
        mapCanvas,
        nodeList,
        warehouseLocationInput,
        submitButton,
        showAuctionResultBtn,
        zoomInBtn,
        zoomOutBtn,
        resetViewBtn
    );

    await dataManager.readNodesFromCSVFile();

    uiHandlers.renderNodeList();

    mapRenderer.autoFitView(dataManager.getAvailableNodes(), dataManager.getWarehouseLocation());
    uiHandlers.drawMapEssentials();

    

});