// static/scanner.js

const scannedBarcodes = new Set();
const listElement = document.getElementById('scanned-list');
const submitButton = document.getElementById('submit-btn');

function onScanSuccess(decodedText, decodedResult) {
    if (!scannedBarcodes.has(decodedText)) {
        scannedBarcodes.add(decodedText);
        const newItem = document.createElement('li');
        newItem.innerText = decodedText;
        listElement.appendChild(newItem);
        if(submitButton.style.display === 'none') {
            submitButton.style.display = 'block';
            listElement.querySelector('li').remove();
        }
    }
}

function onScanFailure(error) {
    // This is normal, just means no code found in frame
}

// --- THIS IS THE NEW FIX ---
// We are enabling the experimental barcode detector.
let html5QrcodeScanner = new Html5QrcodeScanner(
    "reader",
    { 
        fps: 10, 
        qrbox: { width: 250, height: 250 },
        experimentalFeatures: {
            useBarCodeDetectorIfSupported: true
        }
    },
    false // verbose = false
);
// --- END OF FIX ---

html5QrcodeScanner.render(onScanSuccess, onScanFailure);

submitButton.addEventListener('click', () => {
    const barcodesArray = Array.from(scannedBarcodes);
    console.log("Submitting these barcodes:", barcodesArray);

    submitButton.innerText = "Submitting...";
    submitButton.disabled = true;

    fetch('/api/stock-in', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ barcodes: barcodesArray })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Server response:', data);
        alert(data.message);
        location.reload();
    })
    .catch(error => {
        console.error('Error submitting stock:', error);
        alert('Error submitting stock. Check console.');
        submitButton.innerText = "Submit Stock";
        submitButton.disabled = false;
    });
});