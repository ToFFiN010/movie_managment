document.addEventListener('DOMContentLoaded', function () {
  const showId = document.getElementById('show_id_val')?.value;
  const seatButtons = document.querySelectorAll('.seat-btn');
  const selectedSeatsInput = document.getElementById('selected_seats_input');
  const selectedSeatsList = document.getElementById('selected_seats_display');
  const subtotalDisplay = document.getElementById('subtotal_display');
  const convenienceDisplay = document.getElementById('convenience_display');
  const totalDisplay = document.getElementById('total_display');
  const submitBtn = document.getElementById('proceed_checkout_btn');
  const timerBadge = document.getElementById('timer_badge');
  const timerCountdown = document.getElementById('timer_countdown');

  let selectedSeats = new Map(); // seatId -> { label, price }
  let countdownInterval = null;
  let remainingSeconds = 120;

  const convenienceFeePerTicket = parseFloat(document.getElementById('convenience_fee_val')?.value || '2.50');

  // WebSockets Live Seat Updates Setup
  if (showId) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/shows/${showId}/seats/`;
    
    let socket = null;
    try {
      socket = new WebSocket(wsUrl);

      socket.onopen = function () {
        console.log('Real-time seat WS connected.');
      };

      socket.onmessage = function (e) {
        const data = JSON.parse(e.data);
        if (data.type === 'seat_update') {
          handleSeatUpdateBroadcast(data);
        }
      };

      socket.onclose = function () {
        console.log('Real-time seat WS disconnected.');
      };
    } catch (err) {
      console.warn('WebSocket connection error:', err);
    }
  }

  function handleSeatUpdateBroadcast(data) {
    const { seat_ids, status, user_id } = data;
    const currentUserId = document.getElementById('current_user_id')?.value;

    seat_ids.forEach(seatId => {
      const btn = document.querySelector(`.seat-btn[data-id="${seatId}"]`);
      if (btn) {
        // If user is currently holding this seat locally
        if (status === 'RESERVED' && user_id == currentUserId) {
          btn.className = 'seat-btn status-SELECTED_BY_ME selected';
        } else if (status === 'RESERVED') {
          btn.className = 'seat-btn status-RESERVED';
          btn.disabled = true;
          if (selectedSeats.has(String(seatId))) {
            selectedSeats.delete(String(seatId));
            updateSummary();
          }
        } else if (status === 'BOOKED') {
          btn.className = 'seat-btn status-BOOKED';
          btn.disabled = true;
          if (selectedSeats.has(String(seatId))) {
            selectedSeats.delete(String(seatId));
            updateSummary();
          }
        } else if (status === 'AVAILABLE') {
          btn.className = 'seat-btn status-AVAILABLE';
          btn.disabled = false;
        }
      }
    });
  }

  seatButtons.forEach(btn => {
    btn.addEventListener('click', function () {
      if (this.classList.contains('status-BOOKED') || this.classList.contains('status-RESERVED')) {
        return;
      }

      const seatId = this.dataset.id;
      const seatLabel = this.dataset.label;
      const seatPrice = parseFloat(this.dataset.price);

      if (selectedSeats.has(seatId)) {
        selectedSeats.delete(seatId);
        this.classList.remove('selected');
        this.classList.add('status-AVAILABLE');
      } else {
        selectedSeats.set(seatId, { label: seatLabel, price: seatPrice });
        this.classList.add('selected');
      }

      updateSummary();
    });
  });

  function startTimer(seconds) {
    clearInterval(countdownInterval);
    remainingSeconds = seconds;
    if (timerBadge) timerBadge.classList.remove('d-none');

    countdownInterval = setInterval(() => {
      remainingSeconds--;
      if (remainingSeconds <= 0) {
        clearInterval(countdownInterval);
        if (timerCountdown) timerCountdown.textContent = '00:00';
        alert('Your 2-minute seat reservation has expired. Please select seats again.');
        window.location.reload();
      } else {
        const mins = Math.floor(remainingSeconds / 60).toString().padStart(2, '0');
        const secs = (remainingSeconds % 60).toString().padStart(2, '0');
        if (timerCountdown) timerCountdown.textContent = `${mins}:${secs}`;
      }
    }, 1000);
  }

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
      if (timerBadge) timerBadge.classList.add('d-none');
      clearInterval(countdownInterval);
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

    // Start 2-minute countdown whenever seats are active
    if (remainingSeconds === 120 || !countdownInterval) {
      startTimer(120);
    }
  }
});
