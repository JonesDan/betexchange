let selectedMarkets = {}

$(".market-btn").click(function() {
    let market_id = $(this).data("market");
    let market_name = $(this).data("market_name");

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

    console.log(`Selected Markets ${selectedMarkets}`)

    // Update the tab title with selected count
    let count = Object.keys(selectedMarkets).length;
    const market_counter = document.getElementById('selected_markets_tab');
    market_counter.innerHTML = `Select Markets (${count})`;
});

function updateSelection(market_id, add_remove) {

    console.log(`Update selected_markets Shelve`)

    fetch('/update_selection', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ market_id: market_id, add_remove: add_remove })
    });

}

function deleteRowsByName(name) {

    console.log(`Remove ${market_id} from selected_markets`)

    updateSelection(market_id, 'remove')

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

    console.log(`Add ${market_id} to selected_markets`)

    updateSelection(market_id, 'add')

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
                
                console.log(`Pull Prices for ${market.market_name}_${market.selection_name}`)

                let rowColor = market.b_l === "BACK" ? "table-info" : "table-warning";
                let exp_id = market.b_l === "BACK" ? `${market.market_id}_${market.selection_id}_expW` : `${market.market_id}_${market.selection_id}_expL`;
                let exp_text_col = parseFloat(`${market.ex}`) >= 0 ? 'text-success' : 'text-danger';

                let hedge_input = market.b_l === "BACK" ? `<select>
                                                                <option value=""></option>
                                                                <option value="X">X</option>
                                                                <option value="Y">Y</option>
                                                            </select>` : '';

                tableBody.append(`
                    <tr id=${market.id} class="${rowColor}">
                        <td class="fs-6">${market.market_name}</td>
                        <td class="fs-6">${market.selection_name}</td>
                        <td class="text-center ${exp_text_col}" id="${exp_id}">
                            £${market.exposure}
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
                        <td id="sizeMin-${market.id}" class="fs-6"><input type="number" class="form-control form-control-sm  w-100" min="0" value="0"></td>
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

// Start process on page load
window.addEventListener('load', () => {
    console.log(`Start processes`)
    const currentUrl = window.location.href;

    fetch('/start_process', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ url: currentUrl })
    });
});

// Stop process on page unload
window.addEventListener('beforeunload', () => {
    console.log(`Stop processes`)
    navigator.sendBeacon('/stop_process');
});