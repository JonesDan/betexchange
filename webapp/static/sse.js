const eventSource = new EventSource('/stream?channel=prices');

// Listen for 'update' events
eventSource.addEventListener('update', function(event) {
    // Parse the incoming data
    const data = JSON.parse(event.data);

    const cellId = `level${data.level}-${data.market_id}-${data.selection_id}-${data.side}`
    const cell = document.getElementById(cellId);
    if (cell) {
        console.log(`Update data for cell ${cellId}`);
        const el_updatetime = document.getElementById("update_time");

        const button = cell.querySelector("button");
        const text = button.childNodes[0].nodeValue.trim(); // This grabs only the first text node
        const currentValue = parseFloat(text);

        const newValue = parseFloat(data.price)
        
        if (newValue < currentValue) {
            cell.classList.add('bg-success', 'text-white');
            cell.classList.remove('bg-danger');
        } else if (newValue > currentValue) {
            cell.classList.add('bg-danger', 'text-white');
            cell.classList.remove('bg-success');
        } else {
            // no change, clear any color classes
            cell.classList.remove('bg-success', 'bg-danger', 'text-white');
        }

        button_colour = "btn-primary"
        let button_colour = data.level === 0 ? "btn-primary" : "btn-secondary";
        cell.innerHTML = `<button class="btn ${button_colour}">${newValue}<br>
                            <small>(£${data.size})</small></button>`;

        setTimeout(() => {
            cell.classList.remove('bg-success', 'bg-danger', 'text-white');
        }, 3000);

        el_updatetime.innerHTML = `Selected Markets <span class="small-text">updated_at: ${data.publish_time}</span>`

      } else {
        console.log("Cell not found!");
      }
});

eventSource.onerror = function() {
    console.error("SSE prices connection lost. Reconnecting...");
    setTimeout(() => {
        eventSource = new EventSource('/stream?channel=prices');
    }, 3000);
};


const eventSource_orders = new EventSource('/stream?channel=orders');

// Listen for 'update' events
eventSource_orders.addEventListener('update', function(event) {
    const data = JSON.parse(event.data); // Parse incoming JSON data
    updateTable(data);
});

async function fetchAndUpdateOrders() {
    try {
        const response = await fetch('/get_orders');
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const orders = await response.json();

        orders.forEach(order => {
            updateTable(order);
        });

    } catch (error) {
        console.error('Error fetching orders:', error);
    }
}


// Function to update or insert a row in the table
function updateTable(data) {
    const table = document.getElementById("order_summary");
    let row = document.getElementById(`row-${data.bet_id}`);

    console.log(`Order data: ${data.market_name}`);

    const side2 = data.market_name.toUpperCase().includes("OVERS LINE")
    ? (data.side === "LAY" ? "OVER" : data.side === "BACK" ? "UNDER" : data.side)
    : data.side;

    let innerHTML_txt = `
                    <td class="fs-6"><small class="small-text">${data.bet_id}</small></td>
                    <td class="fs-6"><small class="small-text">${data.placed_date}</small></td>
                    <td class="fs-6"><small class="small-text">${data.matched_date}</small></td>
                    <td class="fs-6">
                        <small class="small-text">
                            ${
                                data.status === 'EXECUTABLE'
                                ? `<button class="btn btn-sm btn-danger" onclick="cancelOrder('${data.bet_id}')">Cancel</button>`
                                : data.cancelled_date || ''
                            }
                        </small>
                    </td>
                    <td class="fs-6"><small class="small-text">${data.market_name}</small></td>
                    <td class="fs-6"><small class="small-text">${data.selection_name}</small></td>
                    <td class="fs-6"><small class="small-text">${side2}</small></td>
                    <td class="fs-6"><small class="small-text">${data.status}</small></td>
                    <td class="fs-6"><small class="small-text">${data.price}</small></td>
                    <td class="fs-6"><small class="small-text">${data.size}</small></td>
                    <td class="fs-6"><small class="small-text">${data.average_price_matched}</small></td>
                    <td class="fs-6"><small class="small-text">${data.size_matched}</small></td>
                    <td class="fs-6"><small class="small-text">${data.size_remaining}</small></td>
                    <td class="fs-6"><small class="small-text">${data.size_lapsed}</small></td>
                    <td class="fs-6"><small class="small-text">${data.size_cancelled}</small></td>
                    <td class="fs-6"><small class="small-text">${data.size_voided}</small></td>
                        `;

    if (row) {
        // Update existing row
        console.log(`Update order ${data.bet_id}`);

        row.innerHTML = innerHTML_txt;
    } else {
        
        // Create new row if it doesn't exist
        // Create new row if it doesn't exist
        row = table.insertRow();
        row.id = `row-${data.bet_id}`;

        if (side2 === 'LAY') {
        rowColor = 'table-warning';
        } else if (side2 === 'UNDER') {
        rowColor = 'table-light';
        } else if (side2 === 'BACK') {
        rowColor = 'table-info';
        } else {
        rowColor = 'table-secondary';
        }

        row.classList.add(`${rowColor}`);

        console.log(`Add new order ${data.bet_id}`);

        row.innerHTML = innerHTML_txt;
    }
    const rowCount = document.querySelectorAll('#orders_table tbody tr').length;
    const tab = document.getElementById('order_summary_tab');
    console.log(`Update Order Logs counter ${rowCount}`)
    tab.textContent = `Order Logs (${rowCount})`;
}

eventSource_orders.onerror = function() {
    console.error("SSE orders connection lost. Reconnecting...");
    setTimeout(() => {
        eventSource_orders = new EventSource('/stream?channel=orders');
    }, 3000);
};

const eventSource_selection_exposure = new EventSource('/stream?channel=selection_exposure');

// Listen for 'update' events
eventSource_selection_exposure.addEventListener('update', function(event) {
    const data = JSON.parse(event.data); // Parse incoming JSON data
    updateSelection_exp(data);
});


function updateSelection_exp(dataList) {
    if (dataList.length > 0 && dataList[0].market_name.includes('OVERS LINE')) {
        console.log(`Update overs exposure${dataList[0].market_id}_${dataList[0].selection_id}_expW`);
        insertHorizontalSubTableRow(dataList[0].market_id, dataList[0].selection_id, dataList);
    } else {

        dataList.forEach(data => {
            const expW_cell = document.getElementById(`${data.market_id}_${data.selection_id}_expW`);

            if (expW_cell) {
                console.log(`Update backs exposure ${data.market_id}_${data.selection_id}_expW`);
                expW_cell.textContent = data.exposure;

                // Add color logic
                if (parseFloat(data.back_exposure) >= 0) {
                    expW_cell.classList.remove('text-danger');
                    expW_cell.classList.add('text-success');
                } else {
                    expW_cell.classList.remove('text-success');
                    expW_cell.classList.add('text-danger');
                }
            }
        });
    }
}


eventSource_selection_exposure.onerror = function() {
    console.error("SSE selection_exposure connection lost. Reconnecting...");
    setTimeout(() => {
        eventSource_selection_exposure= new EventSource('/stream?channel=selection_exposure');
    }, 3000);
};

function stopSSE() {
    if (eventSource) {
        eventSource.close();
        eventSource = null; // Clear reference
    }

    if (eventSource_orders) {
        eventSource_orders.close();
        eventSource_orders= null; // Clear reference
    }


    if (eventSource_selection_exposure) {
        eventSource_selection_exposure.close();
        eventSource_selection_exposure= null; // Clear reference
    }
}

// Example: Stop SSE when switching pages
window.addEventListener("beforeunload", stopSSE);

window.addEventListener('load', () => {
    console.log(`Fetching orders`)
    fetchAndUpdateOrders()
});
