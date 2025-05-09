let selectedMarkets = {}

function insertHorizontalSubTableRow(market_id, selection_id, dataList) {
    const mainTable = document.getElementById('selected-markets');

    // Create new row for the subtable
    const newRow = document.createElement('tr');
    newRow.id = `${market_id}-${selection_id}-overs_exposure`
    const newCell = document.createElement('td');
    newCell.colSpan = 11;

    // Create the subtable
    const subTable = document.createElement('table');
    subTable.className = 'table table-bordered table-sm text-center';

    if (dataList.length > 0) {
        // Get all keys from the first dict
        // const keys = Object.keys(dataList[0]);
        const keys = ['runs', 'profit'];

        // Create a row for each key (runs, profit, etc.)
        keys.forEach(key => {
            const row = document.createElement('tr');

            // Header cell for the row label (e.g., "runs")
            const th = document.createElement('th');
            th.textContent = key;
            row.appendChild(th);

            // Data cells
            dataList.forEach(item => {
                const td = document.createElement('td');
                td.textContent = item[key];
                td.classList.add('fs-6');

                // Color-code profit cells
                if (key.toLowerCase() === 'profit') {
                    td.classList.add('text-white');
                    if (item[key] > 0) td.classList.add('bg-success');
                    else if (item[key] < 0) td.classList.add('bg-danger');
                    else td.classList.add('bg-secondary');
                }

                row.appendChild(td);
            });

            subTable.appendChild(row);
        });
    }

    newCell.appendChild(subTable);
    newRow.appendChild(newCell);
    mainTable.appendChild(newRow);
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
            el_updatetime.innerHTML = `Selected Markets <span class="small-text">updated_at: ${data.publish_time}</span>`
            tableBody.append(`
                <tr id="${selected_markets[0].market_id}-break">
                    <td colspan="10" style="height: 20px;">${selected_markets[0].market_name}</td> <!-- Break Row -->
                </tr>
            `);
            selected_markets.forEach(market => {
                
                const side2 = market.market_name.toUpperCase().includes("OVERS LINE")
                                ? (market.side === "LAY" ? "OVER" : market.side === "BACK" ? "UNDER" : market.side)
                                : market.side;

                console.log(`Pull Prices for ${market.market_name}_${market.selection_name}, ${side2}`)


                if (side2 === 'LAY') {
                    rowColor = 'table-warning';
                  } else if (side2 === 'UNDER') {
                    rowColor = 'table-light';
                  } else if (side2 === 'BACK') {
                    rowColor = 'table-info';
                  } else {
                    rowColor = 'table-secondary';
                  }
                
                let exp_id = market.side === "BACK" ? `${market.market_id}_${market.selection_id}_expW` : `${market.market_id}_${market.selection_id}_expL`;
                let exp_text_col = parseFloat(`${market.exposure}`) >= 0 ? 'text-success' : 'text-danger';

                // let exp  = market.side === "BACK"  ? `£${market.exposure}` : ``;
                let exp = side2 === "BACK"
                                            ? (market.exposure < 0
                                                ? `-£${Math.abs(market.exposure).toFixed(2)}`
                                                : `£${market.exposure}`
                                            )
                                            : '';


                let id = `${market.market_id}-${market.selection_id}-${market.side}`
                let hedge_input = side2 === "BACK"
                                    ? `<select>
                                        <option value=""></option>
                                        <option value="X">X</option>
                                        <option value="Y">Y</option>
                                    </select>`
                                    : '';

                const price1 = market.priceList?.[0] || "";
                const price2 = market.priceList?.[1] || "";
                const price3 = market.priceList?.[2] || "";

                const size1 = market.sizeList?.[0] || "0";
                const size2 = market.sizeList?.[1] || "0";
                const size3 = market.sizeList?.[2] || "0";

                tableBody.append(`
                    <tr id=${id} class="${rowColor}">
                        <td class="fs-6"><small>${market.selection_name}</small></td>
                        <td class="text-center ${exp_text_col}" id="${exp_id}">
                            ${exp}
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
                        <td class="fs-6">${side2}</td>
                        <td id="size-${id}" class="number-input-column"><input type="number" min="0 value="0"/></td>
                        <td id="price-${id}" class="number-input-column"><input type="number" min="0" value="${price1}"/></td>
                        <td id="level1-${id}">
                             <button class="btn btn-primary">${price1}<br>
                             <small class="small-text">(£${size1})</small></button>
                        </td>
                        <td id="level2-${id}">
                            <button class="btn btn-secondary">${price2}<br>
                            <small class="small-text">(£${size2})</small></button>
                        </td>
                        <td id="level3-${id}">
                            <button class="btn btn-secondary">${price3}<br>
                            <small class="small-text">(£${size3})</small></button>
                        </td>
                    </tr>
                `);
            });
            if (data.exposure_overs && data.exposure_overs.length > 0) insertHorizontalSubTableRow(data.selected_markets[0].market_id, data.selected_markets[0].selection_id, data.exposure_overs);
        }
    });
}

function deleteRowsByName(market_id, market_name) {

    console.log(`Remove ${market_name} ${market_id} from selection list`)

    updateSelection(market_id, 'remove')
    
    let table = document.getElementById("market_prices_table");
    if (!table) {
        console.error("Table not found!");
        return;
    }

    const rows = document.querySelectorAll(`tr[id*="${market_id}"]`);
    rows.forEach(row => row.remove());
}

function handleMarketButtonClick(event) {

    const button = $(event.currentTarget);
    const market_id = button.data("market");
    const market_name = button.data("market_name");

    if (market_id in selectedMarkets) {
        delete selectedMarkets[market_id];
        button.removeClass("selected");
        deleteRowsByName(market_id, market_name);
    } else {
        selectedMarkets[market_id] = market_name;
        button.addClass("selected");
        addMarketToTable(market_id);
    }

    console.log(`Selected Markets`, selectedMarkets);

    const count = Object.keys(selectedMarkets).length;
    document.getElementById('selected_markets_tab').innerHTML = `Select Markets (${count})`;

};


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


// document.getElementById('refreshBtn').addEventListener('click', function () {
function refreshMarkets() {
    const currentUrl = window.location.href;

    fetch('/get_markets', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ url: currentUrl })
    })
        .then(response => response.json())
        .then(data => {
            const listGroup = document.getElementById('market-list');
            listGroup.innerHTML = ''; // Clear old markets
            const market_updatetime = document.getElementById("update_time_markets");
            market_updatetime.innerHTML = `Market Name / Total Matched <span class="small-text">updated_at: ${data.update_time}</span>`

            data.markets.forEach(market => {
                const button = document.createElement('button');
                // button.type = 'button';
                let cl = market.market_id in selectedMarkets ? 'list-group-item list-group-item-action market-btn selected' : 'list-group-item list-group-item-action market-btn';
                button.className = cl;
                button.setAttribute('data-market', market.market_id);
                button.setAttribute('data-market_name', market.market_name);
                button.textContent = `${market.market_name} / (£${market.total_matched})`;
                listGroup.appendChild(button);
            });
        })
        .catch(error => console.error('Error fetching markets:', error));
};

// Use event delegation on a static parent (e.g., #market-list)
$(document).on('click', '.market-btn', handleMarketButtonClick);

document.addEventListener('DOMContentLoaded', function () {
    // Execute on page load
    refreshMarkets();

    // Execute on button click
    document.getElementById('refreshBtn').addEventListener('click', function () {
        refreshMarkets();
    });
});

function cancelOrder(betId) {
    const button = event.target;
    button.disabled = true;
    button.textContent = 'CANCELING...';

    fetch('/cancel_orders', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ bet_id: betId })
    })
    .then(response => {
        if (response.ok) {
            button.textContent = 'CANCELLED';  // Optionally update or hide
            button.classList.remove('btn-danger');
            button.classList.add('btn-secondary');
        } else {
            button.textContent = 'FAILED';
            button.disabled = false;
        }
    })
    .catch(error => {
        console.error('Error:', error);
        button.textContent = 'ERROR';
        button.disabled = false;
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

    refreshMarkets();
});

// Stop process on page unload
window.addEventListener('beforeunload', () => {
    console.log(`Stop processes`)
    navigator.sendBeacon('/stop_process');
});
