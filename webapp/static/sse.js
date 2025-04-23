const eventSource = new EventSource('/stream?channel=prices');

// Listen for 'update' events
eventSource.addEventListener('update', function(event) {
    // Parse the incoming data
    const data = JSON.parse(event.data);
    chartId = `chart-${data.market_id}-${data.selection_id}-${data.b_l}`
    const chartInstance = Chart.getChart(chartId); // Get the chart instance by ID

    if (chartInstance) {
        console.log(`Update data for chart ${chartId}`);
        const el_updatetime = document.getElementById("update_time");

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

        el_updatetime.innerHTML = `Selected Markets <span class="small-text">updated_at: ${data.update_time}</span>`

      } else {
        console.log("Chart not found!");
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

// Function to update or insert a row in the table
function updateTable(data) {
    const table = document.getElementById("orders_table");
    let row = document.getElementById(`row-${data.bet_id}`);

    if (row) {
        // Update existing row
        console.log(`Update order ${data.bet_id}`);
        row.innerHTML = `
                    <td class="fs-6">${data.bet_id}</td>
                    <td class="fs-6">${data.market_name}</td>
                    <td class="fs-6">${data.selection_selection}</td>
                    <td class="fs-6">${data.placed_date}</td>
                    <td class="fs-6">${data.side}</td>
                    <td class="fs-6">${data.status}</td>
                    <td class="fs-6">${data.price}</td>
                    <td class="fs-6">${data.size}</td>
                    <td class="fs-6">${data.average_price_matched}</td>
                    <td class="fs-6">${data.size_matched}</td>
                    <td class="fs-6">${data.size_remaining}</td>
                    <td class="fs-6">${data.size_lapsed}</td>
                    <td class="fs-6">${data.size_cancelled}</td>
                    <td class="fs-6">${data.size_voided}</td>
                    `;
    } else {
        
        // Create new row if it doesn't exist
        // Create new row if it doesn't exist
        row = table.insertRow();
        row.id = `row-${data.order_id}`;
        let rowColor = data.b_l === "B" ? "table-info" : "table-warning";
        row.classList.add(`${rowColor}`);

        console.log(`Add new order ${data.order_id}`);

        row.innerHTML = `
                    <td class="fs-6">${data.bet_id}</td>
                    <td class="fs-6">${data.market_name}</td>
                    <td class="fs-6">${data.selection_name}</td>
                    <td class="fs-6">${data.placed_date}</td>
                    <td class="fs-6">${data.side}</td>
                    <td class="fs-6">${data.status}</td>
                    <td class="fs-6">${data.price}</td>
                    <td class="fs-6">${data.size}</td>
                    <td class="fs-6">${data.average_price_matched}</td>
                    <td class="fs-6">${data.size_matched}</td>
                    <td class="fs-6">${data.size_remaining}</td>
                    <td class="fs-6">${data.size_lapsed}</td>
                    <td class="fs-6">${data.size_cancelled}</td>
                    <td class="fs-6">${data.size_voided}</td>
                        `;
    }
    const rowCount = document.querySelectorAll('#orders_table tbody tr').length;
    const tab = document.getElementById('order_summary_tab');
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
    dataList.forEach(data => {
        const expW_cell = document.getElementById(`${data.market_id}_${data.selection_id}_expW`);

        if (expW_cell) {
            console.log(`Update exposure ${data.market_id}_${data.selection_id}_expW`);

            expW_cell.textContent = data.back_exposure;

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