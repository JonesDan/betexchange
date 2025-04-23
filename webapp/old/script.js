// Function to highlight selected markets
// Function to update price when slider moves

let priceList = {};


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
                let exp_id = market.b_l === "BACK" ? `${market.market_id}_${market.selection_id}_expW` : `${market.market_id}_${market.selection_id}_expL`;
                let exp_text_col = parseFloat(`${market.ex}`) >= 0 ? 'text-success' : 'text-danger';

                let hedge_input = market.b_l === "BACK" ? `<select>
                                                                <option value=""></option>
                                                                <option value="X">X</option>
                                                                <option value="Y">Y</option>
                                                            </select>` : '';
                
                console.log(exp_text_col)

                tableBody.append(`
                    <tr id=${market.id} class="${rowColor}">
                        <td class="fs-6">${market.market_name}</td>
                        <td class="fs-6">${market.selection_name}</td>
                        <td class="text-center ${exp_text_col}" id="${exp_id}">
                            £${market.ex}
                        </td>
                        <td>
                            <select>
                                <option value=""></option>
                                <option value="A">A</option>
                                <option value="B">B</option>
                            </select>
                        </td>
                        <td>
                            ${hedge_input}
                        </td>
                        <td class="fs-6">${market.b_l}</td>
                        <td id="size-${market.id}" class="fs-6"><input type="number" class="form-control form-control-sm  w-100" min="0"></td>
                        <td id="sizeMin-${market.id}" class="fs-6"><input type="number" class="form-control form-control-sm  w-100" min="0"></td>
                        <td id="min-price-${market.id}" class="min-price fs-6">
                        <td>
                            <canvas class="chart-container" id="chart-${market.id}" height="50"></canvas>
                        </td>
                    </tr>
                `);


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

            if (gamepad.buttons[2].pressed) { // Detect "Z" keypress
                console.log("X button pressed!");
                place_orders("X");
            }

            if (gamepad.buttons[3].pressed) { // Detect "B" keypress
                console.log("Y button pressed!");
                place_orders("Y");
            }
        }

    }, 100); // Check every 100ms
};

function triggerVibration() {
    if ("vibrate" in navigator) {  // Check if vibration is supported
        navigator.vibrate(1000);  // Vibrate for 200ms
    } else {
        console.log("Vibration API not supported");
    }
}

function place_orders(shortcut) {

    triggerVibration();
    order_details = getSelectedRows(shortcut)
    showToast(`${shortcut} Button Pressed`);
    handleButtonClick(shortcut)

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
            let selectValue = row.cells[3].querySelector("select").value;
            let selectValue_hedge = row.cells[4].querySelector("select").value;
            let sizeValue = row.cells[6].querySelector("input").value;
            let sizeMinValue = row.cells[7].querySelector("input").value;
            let priceValue = row.cells[8].querySelector("input").value;
            let hedge = selectValue_hedge === shortcut ? true  : false;
            
            if (selectValue === shortcut || selectValue_hedge == shortcut) {
                console.log({size: sizeValue, sizeMin: sizeMinValue, price: priceValue, hedge: hedge})
                selectedRows[rowId] = {size: sizeValue, sizeMin: sizeMinValue, price: priceValue, hedge: hedge};
            }
        }
    });
    return selectedRows;
}


// Function to create and show a toast
function showToast(message) {
    const toastContainer = document.getElementById("toast-container");

    const toastId = "toast-" + Date.now();
    const toastHTML = `
    <div id="${toastId}" class="toast align-items-center text-bg-primary border-0 mb-2" role="alert" aria-live="assertive" aria-atomic="true">
        <div class="d-flex">
        <div class="toast-body">${message}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    </div>
    `;
    
    toastContainer.insertAdjacentHTML("beforeend", toastHTML);
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { delay: 3000 });  // 3 seconds
    toast.show();

    // Optional: remove toast from DOM after hidden
    toastElement.addEventListener('hidden.bs.toast', () => toastElement.remove());
}

function handleButtonClick(shortcut) {
    // Your existing JS logic here
    console.log(`${shortcut} button pressed`); // or any other action

    // Speak the message
    const message = new SpeechSynthesisUtterance(`${shortcut} button pressed`);
    window.speechSynthesis.speak(message);
}


window.addEventListener("gamepadconnected", (event) => {
    console.log("Gamepad connected:", event.gamepad);
    checkGamepad();
  });
