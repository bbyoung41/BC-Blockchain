// Auto-refresh data every 10 seconds
function startAutoRefresh() {
    setInterval(refreshData, 10000);
}

// Refresh all dashboard data
async function refreshData() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        // Update dashboard
        document.getElementById('balance').textContent = data.balance;
        document.getElementById('blockHeight').textContent = data.block_height;
        document.getElementById('peerCount').textContent = data.peer_count;
        document.getElementById('pendingTx').textContent = data.pending_transactions;

        // Update send page balance if exists
        const availableBalance = document.getElementById('availableBalance');
        if (availableBalance) {
            availableBalance.textContent = data.balance;
        }
    } catch (error) {
        console.error('Error refreshing data:', error);
    }
}

// Refresh peer list
async function refreshPeers() {
    try {
        const response = await fetch('/api/peers');
        const peers = await response.json();

        const peerList = document.getElementById('peerList');
        peerList.innerHTML = peers.map(peer =>
            `<div class="info-item">
                <span>${peer.host}:${peer.port}</span>
                <span>${peer.status}</span>
            </div>`
        ).join('');
    } catch (error) {
        console.error('Error refreshing peers:', error);
    }
}

// Start auto-refresh when page loads
document.addEventListener('DOMContentLoaded', function() {
    refreshData();
    startAutoRefresh();

    // If on network page, load peers
    if (document.getElementById('peerList')) {
        refreshPeers();
    }
});

// Send transaction form handling
async function handleSendForm(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    const resultDiv = document.getElementById('transactionResult');
    const sendButton = document.getElementById('sendButton');

    // Show loading state
    sendButton.disabled = true;
    sendButton.textContent = 'Sending...';
    resultDiv.style.display = 'none';

    try {
        const response = await fetch('/send', {
            method: 'POST',
            body: formData
        });

        const result = await response.text();

        if (response.ok) {
            // Success
            resultDiv.className = 'result-message success';
            resultDiv.innerHTML = `
                <h3>Transaction Sent!</h3>
                <p>${result}</p>
                <p>Transaction is being validated by the network...</p>
            `;

            // Clear form
            form.reset();
            updateTotalAmount();

            // Refresh data
            refreshData();
            updateRecentSent();

        } else {
            // Error
            throw new Error(result);
        }

    } catch (error) {
        resultDiv.className = 'result-message error';
        resultDiv.innerHTML = `
            <h3>Transaction Failed</h3>
            <p>${error.message}</p>
        `;
    } finally {
        // Reset button
        sendButton.disabled = false;
        sendButton.textContent = 'Send Transaction';
        resultDiv.style.display = 'block';

        // Scroll to result
        resultDiv.scrollIntoView({ behavior: 'smooth' });
    }
}

// Validate amount against balance
function validateAmount(input) {
    const amount = parseFloat(input.value) || 0;
    const balance = parseFloat(document.getElementById('currentBalance').textContent) || 0;
    const fee = 0.001; // Fixed transaction fee
    const total = amount + fee;

    const totalElement = document.getElementById('totalAmount');
    totalElement.textContent = total.toFixed(3);

    // Visual feedback
    if (amount > balance - fee) {
        input.style.borderColor = '#dc3545';
        document.getElementById('sendButton').disabled = true;
    } else {
        input.style.borderColor = '#28a745';
        document.getElementById('sendButton').disabled = false;
    }

    updateTotalAmount();
}

// Update total amount display
function updateTotalAmount() {
    const amount = parseFloat(document.getElementById('amount').value) || 0;
    const fee = 0.001;
    const total = amount + fee;
    document.getElementById('totalAmount').textContent = total.toFixed(3);
}

// Load recent sent transactions
async function updateRecentSent() {
    try {
        const response = await fetch('/api/recent-sent');
        const transactions = await response.json();

        const container = document.getElementById('recentSent');

        if (transactions.length === 0) {
            container.innerHTML = '<div class="no-transactions">No recent outgoing transactions</div>';
            return;
        }

        container.innerHTML = transactions.map(tx => `
            <div class="transaction-card pending">
                <div class="tx-header">
                    <span class="tx-type">Outgoing</span>
                    <span class="tx-status">${tx.status}</span>
                </div>
                <div class="tx-details">
                    <div class="tx-amount">-${tx.amount}</div>
                    <div class="tx-address">To: ${tx.recipient.slice(0, 8)}...${tx.recipient.slice(-8)}</div>
                </div>
                <div class="tx-time">${new Date(tx.timestamp * 1000).toLocaleString()}</div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading recent transactions:', error);
    }
}

// Update send page balance
async function updateSendPageBalance() {
    try {
        const response = await fetch('/api/balance');
        const data = await response.json();

        const balanceElement = document.getElementById('currentBalance');
        if (balanceElement) {
            balanceElement.textContent = data.balance;
        }
    } catch (error) {
        console.error('Error updating balance:', error);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const amountInput = document.getElementById('amount');
    const sendButton = document.getElementById('sendButton');

    if (amountInput && sendButton) {
        // Get balance from HTML data attribute or hidden input
        const balance = parseFloat(document.getElementById('currentBalance').textContent);

        amountInput.addEventListener('input', function() {
            const amount = parseFloat(this.value) || 0;

            if (amount > balance) {
                // Show error
                this.style.borderColor = '#dc3545';
                sendButton.disabled = true;
                sendButton.style.opacity = '0.5';

                // Show error message
                showError(`Insufficient funds! Available: ${balance}`);
            } else {
                // Clear error
                this.style.borderColor = '#28a745';
                sendButton.disabled = false;
                sendButton.style.opacity = '1';
                clearError();
            }
        });
    }
});

function showError(message) {
    // Remove any existing error
    clearError();

    // Create error element
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.innerHTML = `<span style="color: #dc3545;">${message}</span>`;

    // Insert after amount input
    const amountInput = document.getElementById('amount');
    amountInput.parentNode.appendChild(errorDiv);
}

function clearError() {
    const existingError = document.querySelector('.error-message');
    if (existingError) {
        existingError.remove();
    }
}

// Blockchain visualization code
