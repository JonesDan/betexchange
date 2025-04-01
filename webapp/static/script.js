// Function to highlight selected markets
// Function to update price when slider moves

let priceList = {};

function updatePrice(slider) {
    // if (priceList.length === 0) return;  // Ensure prices are loaded
    let row = slider.closest("tr");
    let priceCell = row.querySelector(`.min-price`);
    priceCell.textContent = priceList[slider.id].at(slider.value);  // Update price
    price = priceList[slider.id].at(slider.value);
    if (price === "Custom") {
        price = 0;
    }
    priceCell.innerHTML = `<input type="number" class="form-control form-control-sm" min="0" value="${price}" oninput="syncSlider(this)">`;
}

function syncSlider(input) {
    let slider = input.closest('td').previousElementSibling.querySelector('input[type="range"]');
    slider.value = 10;
}

function matchWidths() {
    const rows = document.querySelectorAll("td");

    rows.forEach(row => {
        let chartContainer = row.querySelector(".chart-container");
        let slider = row.querySelector(".slider");

        if (chartContainer && slider) {
            width = chartContainer.clientWidth * 0.95
            slider.style.width = `${width}px`;
        }
    });
}

function getElementIdsByClass(className) {
    return Array.from(document.querySelectorAll(`.${className}`))
                .map(element => element.getAttribute('data-market'))
}

function deleteRowsByName(name) {
    let table = document.getElementById("market_prices_table");
    if (!table) {
        console.error("Table not found!");
        return;
    }

    let rows = table.getElementsByTagName("tr");

    // Loop through rows in reverse order to avoid skipping elements
    for (let i = rows.length - 1; i > 0; i--) {
        let cells = rows[i].getElementsByTagName("td");
        if (cells.length > 1 && cells[0].textContent.trim() === name) {
            table.deleteRow(i);
        }
    }
}

function addMarketToTable(market_id) {

    $.ajax({
        url: "/get_prices",
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify({ marketid: market_id }),
        success: function (data) {
            // Update table with selected markets
            const tableBody = $("#selected-markets");
            const el_updatetime = document.getElementById("update_time");
            const selected_markets = data.selected_markets
            el_updatetime.innerHTML = `Selected Markets <span class="small-text">updated_at: ${data.update_time}</span>`
            selected_markets.forEach(market => {
                let rowColor = market.b_l === "BACK" ? "table-info" : "table-warning";
                tableBody.append(`
                    <tr id=${market.id} class="${rowColor}">
                        <td class="fs-6">${market.market_name}</td>
                        <td class="fs-6">${market.selection_name}</td>
                        <td>
                            <select>
                                <option value=""></option>
                                <option value="A">A</option>
                                <option value="B">B</option>
                            </select>
                        </td>
                        <td class="fs-6">${market.b_l}</td>
                        <td id="size-${market.id}" class="fs-6"><input type="number" class="form-control form-control-sm  w-100" min="0"></td>
                        <td id="sizeMin-${market.id}" class="fs-6"><input type="number" class="form-control form-control-sm  w-100" min="0"></td>
                        <td id="min-price-${market.id}" class="min-price fs-6">
                            <input type="number" class="form-control form-control-sm  w-100" min="0" value="${market.priceList.at(0)}" oninput="syncSlider(this)"
                            >
                        <td>
                            <canvas class="chart-container" id="chart-${market.id}" height="50"></canvas>
                            <span>
                                    <input type="range" class="slider"
                                    id="slider-${market.id}"
                                    data-id="back"
                                    min="0" 
                                    max="10"
                                    step="1"
                                    value="0"
                                    oninput="updatePrice(this)"
                                    >
                            </span>
                        </td>
                    </tr>
                `);

                priceList[`slider-${market.id}`] = market.priceList;

                var ctx = document.getElementById(`chart-${market.id}`).getContext("2d");
                new Chart(ctx, {
                    type: "bar",
                    data: {
                        labels: market.priceList,
                        datasets: [{
                            label: "Size",
                            data: market.sizeList,
                            backgroundColor: "rgba(54, 162, 235, 0.6)"
                        }]
                    },
                    options: {
                        responsive: false,
                        scales: { y: { display: false }, x: { display: true, ticks: {font: {size: 6}} } },
                        plugins: {
                            legend: {
                                display: false
                            } 
                        },
                        maintainAspectRatio: false,
                    }
                })
                matchWidths()
            });
            tableBody.append(`
                <tr>
                    <td colspan="8" style="height: 20px;"></td> <!-- Break Row -->
                </tr>
            `);
        }
    });
}

let selectedMarkets = {}

$(".market-btn").click(function() {
    let market_id = $(this).data("market");
    let market_name = $(this).data("market_name");

    console.log(selectedMarkets)

    // Toggle selection
    if (market_id in selectedMarkets) {
        // selectedMarkets.delete(market);
        delete selectedMarkets[market_id];
        $(this).removeClass("selected");
        deleteRowsByName(market_name)
    } else {
        selectedMarkets[market_id] = market_name
        // selectedMarkets.add(market);
        $(this).addClass("selected");
        addMarketToTable(market_id)
    }

    // Update the tab title with selected count
    let count = Object.keys(selectedMarkets).length;
    const market_counter = document.getElementById('selected_markets_tab');
    market_counter.innerHTML = `Select Markets (${count})`;
});

$("#place_order_tab").click(function() {
    matchWidths()
});

// document.addEventListener("keydown", function (event) {
function checkGamepad() {
    setInterval(() => {
        let gamepads = navigator.getGamepads();
        if (!gamepads) return;
        
        for (let gamepad of gamepads) {
        if (!gamepad) continue;

            if (gamepad.buttons[0].pressed) { // Detect "Z" keypress
                console.log("A button pressed!");
                place_orders("A");
            }

            if (gamepad.buttons[1].pressed) { // Detect "B" keypress
                console.log("B button pressed!");
                place_orders("B");
            }
        }

    }, 100); // Check every 100ms
};

function triggerVibration() {
    if ("vibrate" in navigator) {  // Check if vibration is supported
        navigator.vibrate(200);  // Vibrate for 200ms
    } else {
        console.log("Vibration API not supported");
    }
}

function place_orders(shortcut) {

    triggerVibration();
    order_details = getSelectedRows(shortcut)

    console.log(order_details);

    // Send AJAX request using jQuery
    $.ajax({
        url: "/place_orders",
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify({ order_details: order_details }),
        success: function (response) {
            $("#message-text").text(response.message);
            $("#temp-message").fadeIn();

            // Auto-hide the message after 3 seconds
            setTimeout(function() {
                $("#temp-message").fadeOut();
            }, 3000);
        },
        error: function (xhr, status, error) {
            console.error("Error:", error);
        }
    });
}

function getSelectedRows(shortcut) {
    let selectedRows = {};
    document.querySelectorAll("tbody tr").forEach(row => {
        let rowId = row.id;
        if (rowId) {
            let selectValue = row.cells[2].querySelector("select").value;
            let sizeValue = row.cells[4].querySelector("input").value;
            let sizeMinValue = row.cells[5].querySelector("input").value;
            let priceValue = row.cells[6].querySelector("input").value;
    
            console.log(selectValue, sizeValue, sizeMinValue, priceValue)
            
            if (selectValue === shortcut) {
                selectedRows[rowId] = {size: sizeValue, sizeMin: sizeMinValue, price: priceValue};
            }
        }
    });
    console.log(selectedRows);
    return selectedRows;
}

function stopSSE() {
    if (eventSource) {
        eventSource.close();
        eventSource = null; // Clear reference
    }

    if (eventSource_orders) {
        eventSource_orders.close();
        eventSource_orders= null; // Clear reference
    }
}

// Example: Stop SSE when switching pages
window.addEventListener("beforeunload", stopSSE);
// Adjust widths when the page loads and when resized
window.onload = matchWidths;
window.onresize = matchWidths;

window.addEventListener("gamepadconnected", (event) => {
    console.log("Gamepad connected:", event.gamepad);
    checkGamepad();
  });
