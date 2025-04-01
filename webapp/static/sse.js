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

const eventSource_orders_agg = new EventSource('/stream?channel=orders_agg');

// Listen for 'update' events
eventSource_orders_agg.addEventListener('update', function(event) {
    const data = JSON.parse(event.data); // Parse incoming JSON data
    updateTable_agg(data);
});

// Function to update or insert a row in the table
function updateTable_agg(data) {
    let tableBody = document.getElementById("orders_table_agg");
    tableBody.innerHTML = "";  // Clear existing rows

    data.forEach(row => {
        let tr = document.createElement("tr");
        tr.innerHTML = `<td>${row.market_name}</td><td>${row.selection_name}</td><td class="table-info">${row.bk_price}</td><td class="table-info">${row.bk_stake}</td>><td class="table-info">${row.bk_profit}</td><td class="table-warning">${row.lay_stake}</td><td class="table-warning">${row.lay_liability}</td><td class="table-warning">${row.lay_payout}</td>`;
        tableBody.appendChild(tr);
    });
}