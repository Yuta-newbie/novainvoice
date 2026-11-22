/**
 * NovaInvoice Main Client Scripts
 * Handles dynamic invoice calculation, UI events, and clock updates.
 * Strictly zero emojis.
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Digital Clock in Header
    const clockEl = document.getElementById('digital-clock');
    if (clockEl) {
        function updateClock() {
            const now = new Date();
            const timeStr = now.toLocaleTimeString('en-IN', { hour12: true, hour: '2-digit', minute: '2-digit', second: '2-digit' });
            const dateStr = now.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
            clockEl.textContent = `${dateStr} | ${timeStr}`;
        }
        updateClock();
        setInterval(updateClock, 1000);
    }

    // 2. Invoice Creation Page Dynamic Logic
    const invoiceTable = document.getElementById('invoice-items-table');
    if (invoiceTable) {
        initInvoiceCalculator();
    }
});

function initInvoiceCalculator() {
    const customerSelect = document.getElementById('customer_select');
    const customerStateBadge = document.getElementById('customer_state_badge');
    const taxTypeBadge = document.getElementById('tax_type_badge');
    const companyState = document.getElementById('company_state_val')?.value || 'Uttar Pradesh';

    const tbody = document.getElementById('invoice-items-body');
    const addBtn = document.getElementById('add-item-btn');

    const subtotalEl = document.getElementById('calc-subtotal');
    const cgstRow = document.getElementById('calc-cgst-row');
    const sgstRow = document.getElementById('calc-sgst-row');
    const igstRow = document.getElementById('calc-igst-row');
    const cgstEl = document.getElementById('calc-cgst');
    const sgstEl = document.getElementById('calc-sgst');
    const igstEl = document.getElementById('calc-igst');
    const totalTaxEl = document.getElementById('calc-tax');
    const grandTotalEl = document.getElementById('calc-grand-total');

    let isInterState = false;

    // Detect tax type when customer changes
    function updateTaxJurisdiction() {
        if (!customerSelect) return;
        const selectedOpt = customerSelect.options[customerSelect.selectedIndex];
        const custState = selectedOpt.getAttribute('data-state') || '';
        const custGstin = selectedOpt.getAttribute('data-gstin') || '';

        if (customerStateBadge) {
            customerStateBadge.textContent = custState || 'Not selected';
        }

        if (custState && custState.toLowerCase() !== companyState.toLowerCase()) {
            isInterState = true;
            if (taxTypeBadge) taxTypeBadge.textContent = 'Inter-State (IGST Applicable)';
            if (cgstRow) cgstRow.style.display = 'none';
            if (sgstRow) sgstRow.style.display = 'none';
            if (igstRow) igstRow.style.display = 'flex';
        } else {
            isInterState = false;
            if (taxTypeBadge) taxTypeBadge.textContent = 'Intra-State (CGST + SGST Applicable)';
            if (cgstRow) cgstRow.style.display = 'flex';
            if (sgstRow) sgstRow.style.display = 'flex';
            if (igstRow) igstRow.style.display = 'none';
        }
        recalculateTotals();
    }

    if (customerSelect) {
        customerSelect.addEventListener('change', updateTaxJurisdiction);
        updateTaxJurisdiction();
    }

    // Recalculate financial amounts across all items
    function recalculateTotals() {
        let subtotal = 0.0;
        let totalCgst = 0.0;
        let totalSgst = 0.0;
        let totalIgst = 0.0;

        const rows = tbody.querySelectorAll('.item-row');
        rows.forEach(row => {
            const prodSelect = row.querySelector('.product-select');
            const qtyInput = row.querySelector('.item-qty');
            const opt = prodSelect.options[prodSelect.selectedIndex];

            const price = parseFloat(opt.getAttribute('data-price') || 0);
            const gstRate = parseFloat(opt.getAttribute('data-gst') || 0);
            const stock = parseInt(opt.getAttribute('data-stock') || 0);
            let qty = parseInt(qtyInput.value || 0);

            // Restrict quantity to available stock
            if (qty > stock) {
                qty = stock;
                qtyInput.value = stock;
            }
            if (qty < 1 && stock > 0) {
                qty = 1;
                qtyInput.value = 1;
            }

            const lineTaxable = price * qty;
            let lineCgst = 0.0;
            let lineSgst = 0.0;
            let lineIgst = 0.0;

            if (isInterState) {
                lineIgst = lineTaxable * (gstRate / 100.0);
            } else {
                lineCgst = lineTaxable * (gstRate / 200.0);
                lineSgst = lineTaxable * (gstRate / 200.0);
            }

            const lineTax = lineCgst + lineSgst + lineIgst;
            const lineTotal = lineTaxable + lineTax;

            // Update row displays
            const priceDisplay = row.querySelector('.price-display');
            const taxableDisplay = row.querySelector('.taxable-display');
            const gstDisplay = row.querySelector('.gst-display');
            const totalDisplay = row.querySelector('.total-display');
            const stockBadge = row.querySelector('.stock-badge');

            if (priceDisplay) priceDisplay.textContent = `₹${price.toFixed(2)}`;
            if (taxableDisplay) taxableDisplay.textContent = `₹${lineTaxable.toFixed(2)}`;
            if (gstDisplay) gstDisplay.textContent = `${gstRate}%`;
            if (totalDisplay) totalDisplay.textContent = `₹${lineTotal.toFixed(2)}`;
            if (stockBadge) {
                stockBadge.textContent = `Stock: ${stock}`;
                stockBadge.className = stock <= 5 ? 'badge-custom badge-danger stock-badge' : 'badge-custom badge-bronze stock-badge';
            }

            subtotal += lineTaxable;
            totalCgst += lineCgst;
            totalSgst += lineSgst;
            totalIgst += lineIgst;
        });

        const totalTax = totalCgst + totalSgst + totalIgst;
        const grandTotal = subtotal + totalTax;

        if (subtotalEl) subtotalEl.textContent = `₹${subtotal.toFixed(2)}`;
        if (cgstEl) cgstEl.textContent = `₹${totalCgst.toFixed(2)}`;
        if (sgstEl) sgstEl.textContent = `₹${totalSgst.toFixed(2)}`;
        if (igstEl) igstEl.textContent = `₹${totalIgst.toFixed(2)}`;
        if (totalTaxEl) totalTaxEl.textContent = `₹${totalTax.toFixed(2)}`;
        if (grandTotalEl) grandTotalEl.textContent = `₹${grandTotal.toFixed(2)}`;
    }

    // Attach listeners to row
    function attachRowEvents(row) {
        const prodSelect = row.querySelector('.product-select');
        const qtyInput = row.querySelector('.item-qty');
        const removeBtn = row.querySelector('.remove-row-btn');

        prodSelect.addEventListener('change', recalculateTotals);
        qtyInput.addEventListener('input', recalculateTotals);
        if (removeBtn) {
            removeBtn.addEventListener('click', function () {
                const totalRows = tbody.querySelectorAll('.item-row').length;
                if (totalRows > 1) {
                    row.remove();
                    recalculateTotals();
                } else {
                    alert('An invoice must contain at least one product item.');
                }
            });
        }
    }

    // Initialize existing rows
    tbody.querySelectorAll('.item-row').forEach(attachRowEvents);

    // Add new row button
    if (addBtn) {
        addBtn.addEventListener('click', function () {
            const firstRow = tbody.querySelector('.item-row');
            if (!firstRow) return;
            const newRow = firstRow.cloneNode(true);
            newRow.querySelector('.item-qty').value = 1;
            tbody.appendChild(newRow);
            attachRowEvents(newRow);
            recalculateTotals();
        });
    }

    // Initial calculation
    recalculateTotals();
}

// Confirmation helper
function confirmAction(message) {
    return confirm(message || 'Are you sure you want to proceed with this operation?');
}

