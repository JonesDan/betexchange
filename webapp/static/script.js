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
        url: "/get_prices2",
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
                        <td class="fs-6">${market.b_l}</td>
                        <td id="size-${market.id}" class="fs-6"><input type="number" class="form-control form-control-sm  w-100" min="0"></td>
                        <td id="sizeMin-${market.id}" class="fs-6"><input type="number" class="form-control form-control-sm  w-100" min="0"></td>
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
                        <td id="min-price-${market.id}" class="min-price fs-6">
                            <input type="number" class="form-control form-control-sm  w-100" min="0" value="${market.priceList.at(0)}" oninput="syncSlider(this)"
                            >
                        <td>
                            <select>
                                <option value=""></option>
                                <option value="z">z</option>
                                <option value="x">x</option>
                            </select>
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

// Adjust widths when the page loads and when resized
window.onload = matchWidths;
window.onresize = matchWidths;


// document.addEventListener("DOMContentLoaded", function() {
//     // let selectedMarkets = new Set();
//     let selectedMarkets = {}

//     $(".market-btn").click(function() {
//         let market_id = $(this).data("market");
//         let market_name = $(this).data("market_name");

//         console.log(selectedMarkets)

//         // Toggle selection
//         if (market_id in selectedMarkets) {
//             // selectedMarkets.delete(market);
//             delete selectedMarkets[market_id];
//             $(this).removeClass("selected");
//             deleteRowsByName(market_name)
//         } else {
//             selectedMarkets[market_id] = market_name
//             // selectedMarkets.add(market);
//             $(this).addClass("selected");
//             addMarketToTable(market_id)
//         }

//         // Update the tab title with selected count
//         let count = Object.keys(selectedMarkets).length;
//         const market_counter = document.getElementById('selected_markets_tab');
//         market_counter.innerHTML = `Select Markets (${count})`;
//     });

//     $("#place_order_tab").click(function() {

//         const selectedMarkets = getElementIdsByClass("selected");

//         $.ajax({
//             url: "/get_prices",
//             type: "POST",
//             contentType: "application/json",
//             data: JSON.stringify({ selected_ids: selectedMarkets }),
//             success: function (data) {
//                 // Update table with selected markets
//                 const tableBody = $("#selected-markets");
//                 const el_updatetime = document.getElementById("update_time");
//                 const selected_markets = data.selected_markets
//                 el_updatetime.innerHTML = `Selected Markets <span class="small-text">updated_at: ${data.update_time}</span>`
//                 tableBody.empty();
//                 selected_markets.forEach(market => {
//                     tableBody.append(`
//                         <tr id=${market.id}>
//                             <td>${market.market_name}</td>
//                             <td>${market.selection_name}</td>
//                             <td>${market.b_l}</td>
//                             <td id="size-${market.id}" class="number-input-column"><input type="number"></td>
//                             <td id="max-price-${market.id}" class="max-price">${market.priceList.at(0)}</td>
//                             <td>
//                                 <canvas class="chart-container" id="chart-${market.id}" height="50"></canvas>
//                                 <span>
//                                         <input type="range" class="slider"
//                                         id="slider-${market.id}"
//                                         data-id="back"
//                                         min="0" 
//                                         max="9"
//                                         step="1"
//                                         value="0"
//                                         oninput="updatePrice(this)"
//                                         >
//                                 </span>
//                             </td>
//                             <td id="min-price-${market.id}" class="min-price">${market.priceList.at(0)}</td>
//                             <td>
//                                 <select>
//                                     <option value=""></option>
//                                     <option value="z">z</option>
//                                     <option value="x">x</option>
//                                 </select>
//                             </td>
//                         </tr>
//                     `);

//                     priceList[`slider-${market.id}`] = market.priceList;


//                     var ctx = document.getElementById(`chart-${market.id}`).getContext("2d");
//                     new Chart(ctx, {
//                         type: "bar",
//                         data: {
//                             labels: market.priceList,
//                             datasets: [{
//                                 label: "Size",
//                                 data: market.sizeList,
//                                 backgroundColor: "rgba(54, 162, 235, 0.6)"
//                             }]
//                         },
//                         options: {
//                             responsive: false,
//                             scales: { y: { display: false }, x: { display: true } },
//                             plugins: { legend: { display: false } },
//                             maintainAspectRatio: false,
//                         }
//                     })
//                     matchWidths()
//                 });
//             }
//         });
        
//     });
    
// });


window.addEventListener("gamepadconnected", (event) => {
    console.log("Gamepad connected:", event.gamepad);
    checkGamepad();
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
                place_orders("z");
            }
        }

        // if (event.key.toLowerCase() === "z") { // Detect "Z" keypress
        //     place_orders("z");
        // }

    }, 100); // Check every 100ms
};

// document.addEventListener("keydown", function (event) {
document.addEventListener("gamepadconnected", function (event) {
    setInterval(() => {
        let gamepads = navigator.getGamepads();
        if (!gamepads) return;
        
        for (let gamepad of gamepads) {
        if (!gamepad) continue;

            if (gamepad.buttons[0].pressed) { // Detect "Z" keypress
                console.log("A button pressed!");
                place_orders("z");
            }
        }

        // if (event.key.toLowerCase() === "z") { // Detect "Z" keypress
        //     place_orders("z");
        // }

    }, 100); // Check every 100ms
});

function place_orders(shortcut) {

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
            let selectValue = row.cells[7].querySelector("select").value;
            let sizeValue = row.cells[3].querySelector("input").value;
            let sizeMinValue = row.cells[4].querySelector("input").value;
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

const eventSource = new EventSource('/stream?channel=prices');

// Listen for 'update' events
eventSource.addEventListener('update', function(event) {
    // Parse the incoming data
    const data = JSON.parse(event.data);
    chartId = `chart-${data.market_id}-${data.selection_id}-${data.b_l}`
    const chartInstance = Chart.getChart(chartId); // Get the chart instance by ID

    if (chartInstance) {
        const el_updatetime = document.getElementById("update_time");
        // const min_price = document.getElementById(`min-price-${data.market_id}-${data.selection_id}-${data.b_l}`);

        const Labels = chartInstance.data.labels
        const Dataset = chartInstance.data.datasets[0].data;

        const level = data.level
        Labels[level] = data.price;
        Dataset[level] = data.size;

        chartInstance.destroy()
        var ctx = document.getElementById(chartId).getContext("2d");

        new Chart(ctx, {
            type: "bar",
            data: {
                labels: Labels,
                datasets: [{
                    label: "Size",
                    data: Dataset,
                    backgroundColor: "rgba(54, 162, 235, 0.6)"
                }]
            },
            options: {
                responsive: false,
                scales: { y: { display: false }, x: { display: true, ticks: {font: {size: 6}} } },
                plugins: { legend: { display: false } },
                maintainAspectRatio: false,
            }
        })

        let levelValue = document.getElementById(`slider-${data.market_id}-${data.selection_id}-${data.b_l}`).value

        const max = Labels[0]
        const min = Labels[levelValue]

        el_updatetime.innerHTML = `Selected Markets <span class="small-text">updated_at: ${data.update_time}</span>`
        // min_price.innerHTML = `${min}`

      } else {
        console.log("Chart not found!");
      }
});


const eventSource_orders = new EventSource('/stream?channel=orders');

// Listen for 'update' events
eventSource_orders.addEventListener('update', function(event) {
    const data = JSON.parse(event.data); // Parse incoming JSON data
    updateTable(data);
});

// Function to update or insert a row in the table
function updateTable(data) {
    const table = document.getElementById("orders_table");
    let row = document.getElementById(`row-${data.order_id}`);

    if (row) {
        // Update existing row
        row.innerHTML = `
        <td class="fs-6">${data.market_id}</td>
        <td class="fs-6">${data.selection_id}</td>
        <td class="fs-6">${data.b_l}</td>
        <td class="fs-6">${data.price}</td>
        <td class="fs-6">${data.size}</td>
        <td class="fs-6">${data.matched}</td>
        <td class="fs-6">${data.remaining}</td>
        <td class="fs-6">${data.lapsed}</td>
        <td class="fs-6">${data.cancelled}</td>
        <td class="fs-6">${data.voided}</td>
        <td class="fs-6">${data.update_time}</td>
    `;
    } else {
        // Create new row if it doesn't exist
        // Create new row if it doesn't exist
        row = table.insertRow();
        row.id = `row-${data.order_id}`;

        row.innerHTML = `
        <td class="fs-6">${data.market_id}</td>
        <td class="fs-6">${data.selection_id}</td>
        <td class="fs-6">${data.b_l}</td>
        <td class="fs-6">${data.price}</td>
        <td class="fs-6">${data.size}</td>
        <td class="fs-6">${data.matched}</td>
        <td class="fs-6">${data.remaining}</td>
        <td class="fs-6">${data.lapsed}</td>
        <td class="fs-6">${data.cancelled}</td>
        <td class="fs-6">${data.voided}</td>
        <td class="fs-6">${data.update_time}</td>
                    `;
    }
}