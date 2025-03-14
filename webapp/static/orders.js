let activeMode = ""; // Tracks the active mode: "blue", "green", or ""

function toggleMode(mode) {
    let blueButton = document.getElementById('blueButton');
    let greenButton = document.getElementById('greenButton');

    if (activeMode === mode) {
        // If clicking the active button, turn off mode
        activeMode = "";
        blueButton.classList.remove('border', 'border-danger', 'border-3');
        greenButton.classList.remove('border', 'border-danger', 'border-3');
    } else {
        // Activate selected mode and deactivate the other
        activeMode = mode;
        
        if (mode === "blue") {
            blueButton.classList.add('border', 'border-danger', 'border-3');
            greenButton.classList.remove('border', 'border-danger', 'border-3');
        } else if (mode === "green") {
            greenButton.classList.add('border', 'border-danger', 'border-3');
            blueButton.classList.remove('border', 'border-danger', 'border-3');
        }
    }
}

function markCell(event) {
    if (activeMode === "blue") {
        toggleCellColor(event.target, 'blue', 'white'); // Blue background, white text
    } else if (activeMode === "green") {
        toggleCellColor(event.target, 'green', 'white'); // Green background, white text
    }
}

function toggleCellColor(cell, color, textColor) {
    if (cell.style.backgroundColor === color) {
        // Reset to default if already active
        cell.style.backgroundColor = '';
        cell.style.color = '';
    } else {
        // Set the new color
        cell.style.backgroundColor = color;
        cell.style.color = textColor;
    }
}
