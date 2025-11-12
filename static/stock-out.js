// static/stock-out.js

document.addEventListener('DOMContentLoaded', () => {
    const resultMessage = document.getElementById('result-message');
    const scanAgainBtn = document.getElementById('scan-again-btn');
    const readerContainer = document.getElementById('reader-container');

    function onScanSuccess(decodedText, decodedResult) {
        html5QrcodeScanner.clear().catch(error => {
            console.error("Failed to clear scanner:", error);
        });
        readerContainer.style.display = 'none';
        showMessage('Processing... Please wait.', 'loading');

        fetch('/api/stock-out', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ barcode: decodedText })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showMessage(data.message, 'success');
            } else {
                showMessage(data.message, 'error');
            }
            scanAgainBtn.style.display = 'block';
        })
        .catch(error => {
            console.error('Error:', error);
            showMessage('A critical error occurred.', 'error');
            scanAgainBtn.style.display = 'block';
        });
    }

    function onScanFailure(error) {
        // This is normal
    }

    function showMessage(message, type) {
        resultMessage.innerText = message;
        resultMessage.className = 'status-' + type;
        resultMessage.style.display = 'block';
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
        false // verbose
    );
    // --- END OF FIX ---
    
    html5QrcodeScanner.render(onScanSuccess, onScanFailure);

    scanAgainBtn.addEventListener('click', () => {
        location.reload();
    });
});