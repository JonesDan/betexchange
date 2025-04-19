const eventSource = new EventSource('/stream?channel=prices');

// Listen for 'update' events
eventSource.addEventListener('update', function(event) {
    // Parse the incoming data
    const data = JSON.parse(event.data);
    chartId = `chart-${data.market_id}-${data.selection_id}-${data.b_l}`
    const chartInstance = Chart.getChart(chartId); // Get the chart instance by ID

    if (chartInstance) {
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

        let levelValue = document.getElementById(`slider-${data.market_id}-${data.selection_id}-${data.b_l}`).value

        const max = Labels[0]
        const min = Labels[levelValue]

        el_updatetime.innerHTML = `Selected Markets <span class="small-text">updated_at: ${data.update_time}</span>`
        // min_price.innerHTML = `${min}`

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
    let row = document.getElementById(`row-${data.order_id}`);

    if (row) {
        // Update existing row
        row.innerHTML = `
        <td class="fs-6">${data.market_name}</td>
        <td class="fs-6">${data.selection_name}</td>
        <td class="fs-6">${data.b_l}</td>
        <td class="fs-6">${data.price}</td>
        <td class="fs-6">${data.avp}</td>
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
        let rowColor = data.b_l === "B" ? "table-info" : "table-warning";
        row.classList.add(`${rowColor}`);

        row.innerHTML = `
        <td class="fs-6">${data.market_name}</td>
        <td class="fs-6">${data.selection_name}</td>
        <td class="fs-6">${data.b_l}</td>
        <td class="fs-6">${data.price}</td>
        <td class="fs-6">${data.avp}</td>
        <td class="fs-6">${data.size}</td>
        <td class="fs-6">${data.matched}</td>
        <td class="fs-6">${data.remaining}</td>
        <td class="fs-6">${data.lapsed}</td>
        <td class="fs-6">${data.cancelled}</td>
        <td class="fs-6">${data.voided}</td>
        <td class="fs-6">${data.update_time}</td>
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

const eventSource_orders_agg = new EventSource('/stream?channel=orders_agg');

// Listen for 'update' events
eventSource_orders_agg.addEventListener('update', function(event) {
    const data = JSON.parse(event.data); // Parse incoming JSON data
    updateTable_agg(data);
});

// Function to update or insert a row in the table
function updateTable_agg(data) {
    const expW_cell = document.getElementById(`${data.market_id}_${data.selection_id}_expW`);
    const expL_cell = document.getElementById(`${data.market_id}_${data.selection_id}_expL`);
    
    if (expW_cell) {
        expW_cell.textContent = data.exp_wins;
        expL_cell.textContent = data.exp_lose;

        // Add color logic
        if (parseFloat(data.exp_wins) >= 0) {
            expW_cell.classList.remove('text-danger');
            expW_cell.classList.add('text-success');
        } else {
            expW_cell.classList.remove('text-success');
            expW_cell.classList.add('text-danger');
        }

        if (parseFloat(data.exp_lose) >= 0) {
            expL_cell.classList.remove('text-danger');
            expL_cell.classList.add('text-success');
            } else {
            expL_cell.classList.remove('text-success');
            expL_cell.classList.add('text-danger');
            }
        }
}

eventSource_orders_agg.onerror = function() {
    console.error("SSE orders_agg connection lost. Reconnecting...");
    setTimeout(() => {
        eventSource_orders_agg= new EventSource('/stream?channel=orders_agg');
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


    if (eventSource_orders_agg) {
        eventSource_orders_agg.close();
        eventSource_orders_agg= null; // Clear reference
    }
}

// Example: Stop SSE when switching pages
window.addEventListener("beforeunload", stopSSE);