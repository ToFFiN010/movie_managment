document.addEventListener('DOMContentLoaded', function () {
  const seatButtons = document.querySelectorAll('.seat-btn.AVAILABLE');
  const selectedSeatsInput = document.getElementById('selected_seats_input');
  const selectedSeatsList = document.getElementById('selected_seats_display');
  const subtotalDisplay = document.getElementById('subtotal_display');
  const convenienceDisplay = document.getElementById('convenience_display');
  const totalDisplay = document.getElementById('total_display');
  const submitBtn = document.getElementById('proceed_checkout_btn');

  let selectedSeats = new Map(); // seatId -> { label, price }

  const convenienceFeePerTicket = parseFloat(document.getElementById('convenience_fee_val')?.value || '2.50');

  seatButtons.forEach(btn => {
    btn.addEventListener('click', function () {
      const seatId = this.dataset.id;
      const seatLabel = this.dataset.label;
      const seatPrice = parseFloat(this.dataset.price);

      if (selectedSeats.has(seatId)) {
        selectedSeats.delete(seatId);
        this.classList.remove('SELECTED');
      } else {
        selectedSeats.set(seatId, { label: seatLabel, price: seatPrice });
        this.classList.add('SELECTED');
      }

      updateSummary();
    });
  });

  function updateSummary() {
    const seatIds = Array.from(selectedSeats.keys());
    if (selectedSeatsInput) {
      selectedSeatsInput.value = seatIds.join(',');
    }

    if (selectedSeats.size === 0) {
      if (selectedSeatsList) selectedSeatsList.textContent = 'None';
      if (subtotalDisplay) subtotalDisplay.textContent = '$0.00';
      if (convenienceDisplay) convenienceDisplay.textContent = '$0.00';
      if (totalDisplay) totalDisplay.textContent = '$0.00';
      if (submitBtn) submitBtn.disabled = true;
      return;
    }

    let subtotal = 0;
    let labels = [];

    selectedSeats.forEach((val) => {
      subtotal += val.price;
      labels.push(val.label);
    });

    const totalFee = convenienceFeePerTicket * selectedSeats.size;
    const grandTotal = subtotal + totalFee;

    if (selectedSeatsList) selectedSeatsList.textContent = labels.join(', ');
    if (subtotalDisplay) subtotalDisplay.textContent = '$' + subtotal.toFixed(2);
    if (convenienceDisplay) convenienceDisplay.textContent = '$' + totalFee.toFixed(2);
    if (totalDisplay) totalDisplay.textContent = '$' + grandTotal.toFixed(2);
    if (submitBtn) submitBtn.disabled = false;
  }
});
