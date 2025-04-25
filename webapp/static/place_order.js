// document.addEventListener("keydown", function (event) {
    function checkGamepad() {
        setInterval(() => {
            let gamepads = navigator.getGamepads();
            if (!gamepads) return;
            
            for (let gamepad of gamepads) {
            if (!gamepad) continue;
    
                if (gamepad.buttons[0].pressed) { // Detect "Z" keypress
                    place_orders("A");
                }
    
                if (gamepad.buttons[1].pressed) { // Detect "B" keypress
                    place_orders("B");
                }
    
                if (gamepad.buttons[4].pressed) { // Detect "Z" keypress
                    place_orders("Y");
                }
    
                if (gamepad.buttons[3].pressed) { // Detect "B" keypress
                    place_orders("X");
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
        
        console.log(`${shortcut} button pressed!`);
        console.log(order_details);
    
        // Send AJAX request using jQuery
        $.ajax({
            url: "/place_orders",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({ order_details: order_details }),
            success: function (response) {
                showToast(`Order Summary: ${response.message}`)
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
                let selectValue_hedge = row.cells[4].querySelector("select")?.value || null;
                let sizeValue = row.cells[6].querySelector("input").value;
                let sizeMinValue = row.cells[7].querySelector("input").value;
                let priceValue = row.cells[8].querySelector("input").value;
                let hedge = selectValue_hedge === shortcut ? true  : false;
                
                if (selectValue === shortcut || selectValue_hedge == shortcut) {
                    console.log(`shortcut: ${shortcut}, size: ${sizeValue}, sizeMin: ${sizeMinValue}, price: ${priceValue}, hedge: ${hedge}, rowId: ${rowId}`)
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
        // Speak the message
        const message = new SpeechSynthesisUtterance(`${shortcut} button pressed`);
        window.speechSynthesis.speak(message);
    }
    
    
    window.addEventListener("gamepadconnected", (event) => {
        console.log("Gamepad connected:", event.gamepad);
        checkGamepad();
      });
    