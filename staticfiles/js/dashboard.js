/* CinePrime 3D Motion & Cinema Popups Engine */
document.addEventListener('DOMContentLoaded', () => {
  init3DTiltEffect();
  initModalTriggers();
  initEscKeyHandler();
  initSearchAutocomplete();
  initHorizontalScrollControls();
  initQuickBookingDynamicHandlers();
});

/* 1. 3D MOVIE CARD TILT ENGINE */
function init3DTiltEffect() {
  const cards = document.querySelectorAll('.movie-card-3d');
  
  cards.forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const cardWidth = rect.width;
      const cardHeight = rect.height;
      
      const centerX = rect.left + cardWidth / 2;
      const centerY = rect.top + cardHeight / 2;
      
      const mouseX = e.clientX - centerX;
      const mouseY = e.clientY - centerY;
      
      // Max tilt: 6 degrees
      const rotateX = ((-mouseY / (cardHeight / 2)) * 6).toFixed(2);
      const rotateY = ((mouseX / (cardWidth / 2)) * 6).toFixed(2);
      
      card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateZ(10px) scale3d(1.02, 1.02, 1.02)`;
    });
    
    card.addEventListener('mouseleave', () => {
      card.style.transform = `perspective(1000px) rotateX(0deg) rotateY(0deg) translateZ(0px) scale3d(1, 1, 1)`;
    });
  });
}

/* 2. MOVIE DETAILS MODAL ENGINE */
function initModalTriggers() {
  document.addEventListener('click', (e) => {
    const trigger = e.target.closest('[data-open-modal="details"]');
    if (trigger) {
      e.preventDefault();
      e.stopPropagation();
      const dataset = trigger.dataset;

      // If movie ID provided, fetch full details via API for accuracy
      if (dataset.id) {
        fetch(`/api/detail/${dataset.id}/`)
          .then(res => res.json())
          .then(data => openMovieDetailsModal(data))
          .catch(() => openMovieDetailsModal(dataset));
      } else {
        openMovieDetailsModal(dataset);
      }
    }

    const trailerTrigger = e.target.closest('[data-open-modal="trailer"]');
    if (trailerTrigger) {
      e.preventDefault();
      e.stopPropagation();
      const title = trailerTrigger.dataset.title;
      const trailerUrl = trailerTrigger.dataset.trailer;
      openTrailerModal(title, trailerUrl);
    }
  });
}

function openMovieDetailsModal(data) {
  const modalEl = document.getElementById('movieDetailsModal');
  if (!modalEl) return;

  document.getElementById('modalMovieTitle').textContent = data.title || 'Movie Details';
  document.getElementById('modalMovieRating').textContent = (data.average_rating || data.rating || '8.6') + '/10';
  document.getElementById('modalMovieYear').textContent = data.release_year || data.year || '2024';
  document.getElementById('modalMovieDuration').textContent = (data.duration_minutes || data.duration || '120') + 'm';
  document.getElementById('modalMovieAge').textContent = data.age_certification || data.age || 'U/A';
  document.getElementById('modalMovieLang').textContent = data.language || data.lang || 'English';
  document.getElementById('modalMovieDirector').textContent = data.director || 'N/A';
  document.getElementById('modalMovieDescription').textContent = data.description || 'No description available.';
  
  const backdropEl = document.getElementById('modalMovieBackdrop');
  if (backdropEl) {
    const bgUrl = data.backdrop_url || data.backdrop || data.poster_url || data.poster || '/media/movies/posters/cineprime_default_fallback.png';
    backdropEl.style.backgroundImage = `url('${bgUrl}')`;
  }
  
  const posterEl = document.getElementById('modalMoviePoster');
  if (posterEl) {
    posterEl.src = data.poster_url || data.poster || '/media/movies/posters/cineprime_default_fallback.png';
  }

  // Genre pills
  const genreContainer = document.getElementById('modalMovieGenres');
  if (genreContainer) {
    genreContainer.innerHTML = '';
    const genres = Array.isArray(data.genres) ? data.genres : (data.genres || '').split(',');
    genres.forEach(g => {
      const genreName = typeof g === 'string' ? g.trim() : g;
      if (genreName) {
        const badge = document.createElement('span');
        badge.className = 'badge bg-dark border border-secondary text-light me-1';
        badge.textContent = genreName;
        genreContainer.appendChild(badge);
      }
    });
  }

  // CTA Links
  const bookBtn = document.getElementById('modalBookBtn');
  if (bookBtn) {
    bookBtn.href = data.id ? `/bookings/movie/${data.id}/` : (data.bookUrl || '#');
  }

  const trailerBtn = document.getElementById('modalTrailerBtn');
  if (trailerBtn) {
    trailerBtn.setAttribute('data-title', data.title);
    trailerBtn.setAttribute('data-trailer', data.trailer_url || data.trailer || '');
  }

  const bsModal = new bootstrap.Modal(modalEl);
  bsModal.show();
}

/* 3. TRAILER VIDEO MODAL ENGINE */
function openTrailerModal(title, trailerUrl) {
  const modalEl = document.getElementById('trailerVideoModal');
  if (!modalEl) return;

  const titleEl = document.getElementById('trailerModalTitle');
  if (titleEl) titleEl.textContent = `${title} — Official Trailer`;

  const container = document.getElementById('trailerVideoContainer');
  if (container) {
    let videoId = extractYouTubeId(trailerUrl);
    if (videoId) {
      container.innerHTML = `
        <div class="ratio ratio-16x9">
          <iframe src="https://www.youtube.com/embed/${videoId}?autoplay=1" title="${title}" allowfullscreen allow="autoplay"></iframe>
        </div>
      `;
    } else {
      container.innerHTML = `
        <div class="p-5 text-center text-muted">
          <i class="fa-solid fa-film fs-1 mb-3 text-warning"></i>
          <h6>Trailer Currently Unavailable</h6>
          <p class="small">The official video trailer link for this movie will be added shortly.</p>
        </div>
      `;
    }
  }

  const bsModal = new bootstrap.Modal(modalEl);
  bsModal.show();

  modalEl.addEventListener('hidden.bs.modal', () => {
    if (container) container.innerHTML = '';
  }, { once: true });
}

function extractYouTubeId(url) {
  if (!url) return null;
  const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
  const match = url.match(regExp);
  return (match && match[2].length === 11) ? match[2] : null;
}

/* 4. LIVE SEARCH AUTOCOMPLETE ENGINE */
function initSearchAutocomplete() {
  const searchInput = document.querySelector('.nav-search-box');
  if (!searchInput) return;

  const container = searchInput.parentElement;
  let dropdown = document.createElement('div');
  dropdown.className = 'search-suggestions-dropdown d-none';
  container.appendChild(dropdown);

  let debounceTimer;

  searchInput.addEventListener('input', (e) => {
    clearTimeout(debounceTimer);
    const query = e.target.value.trim();

    if (query.length < 2) {
      dropdown.classList.add('d-none');
      dropdown.innerHTML = '';
      return;
    }

    debounceTimer = setTimeout(() => {
      fetch(`/api/search_suggestions/?q=${encodeURIComponent(query)}`)
        .then(res => res.json())
        .then(data => {
          if (!data.results || data.results.length === 0) {
            dropdown.innerHTML = `<div class="p-3 text-center text-muted small"><i class="fa-solid fa-film me-2 text-warning"></i>No matching movies found</div>`;
          } else {
            dropdown.innerHTML = data.results.map(item => `
              <a href="${item.detail_url}" class="search-suggestion-item">
                <img src="${item.poster_url}" class="search-suggestion-thumb" alt="${item.title}" onerror="this.onerror=null;this.src='/media/movies/posters/cineprime_default_fallback.png';">
                <div>
                  <div class="fw-bold small text-white">${item.title}</div>
                  <div class="text-secondary opacity-75" style="font-size: 0.75rem;">★ ${item.average_rating} • ${item.release_year} • ${item.language}</div>
                </div>
              </a>
            `).join('');
          }
          dropdown.classList.remove('d-none');
        })
        .catch(() => {
          dropdown.classList.add('d-none');
        });
    }, 200);
  });

  document.addEventListener('click', (e) => {
    if (!container.contains(e.target)) {
      dropdown.classList.add('d-none');
    }
  });
}

/* 5. HORIZONTAL CAROUSEL SCROLL CONTROLS */
function initHorizontalScrollControls() {
  document.querySelectorAll('.horizontal-scroll-container').forEach(wrapper => {
    const row = wrapper.querySelector('.horizontal-scroll-row');
    const leftBtn = wrapper.querySelector('.scroll-left-btn');
    const rightBtn = wrapper.querySelector('.scroll-right-btn');

    if (row && leftBtn && rightBtn) {
      leftBtn.addEventListener('click', () => {
        row.scrollBy({ left: -400, behavior: 'smooth' });
      });

      rightBtn.addEventListener('click', () => {
        row.scrollBy({ left: 400, behavior: 'smooth' });
      });
    }
  });
}

/* 6. DYNAMIC QUICK BOOKING HANDLERS */
function initQuickBookingDynamicHandlers() {
  const movieSelect = document.getElementById('quickMovieSelect');
  const theaterSelect = document.getElementById('quickTheaterSelect');
  const dateSelect = document.getElementById('quickDateSelect');
  const showSelect = document.getElementById('quickShowSelect');

  if (!movieSelect) return;

  movieSelect.addEventListener('change', () => {
    const movieId = movieSelect.value;
    if (!movieId) return;

    fetch(`/bookings/api/theaters/?movie_id=${movieId}`)
      .then(res => res.json())
      .then(data => {
        if (theaterSelect) {
          theaterSelect.innerHTML = '<option value="">Select Theater</option>' + 
            data.theaters.map(t => `<option value="${t.id}">${t.name} (${t.city})</option>`).join('');
          theaterSelect.disabled = false;
        }
      });
  });

  if (theaterSelect) {
    theaterSelect.addEventListener('change', () => {
      const movieId = movieSelect.value;
      const theaterId = theaterSelect.value;
      if (!movieId || !theaterId) return;

      fetch(`/bookings/api/dates/?movie_id=${movieId}&theater_id=${theaterId}`)
        .then(res => res.json())
        .then(data => {
          if (dateSelect) {
            dateSelect.innerHTML = '<option value="">Select Date</option>' +
              data.dates.map(d => `<option value="${d.date_str}">${d.formatted_date}</option>`).join('');
            dateSelect.disabled = false;
          }
        });
    });
  }

  if (dateSelect) {
    dateSelect.addEventListener('change', () => {
      const movieId = movieSelect.value;
      const theaterId = theaterSelect.value;
      const dateStr = dateSelect.value;
      if (!movieId || !theaterId || !dateStr) return;

      fetch(`/bookings/api/shows/?movie_id=${movieId}&theater_id=${theaterId}&date=${dateStr}`)
        .then(res => res.json())
        .then(data => {
          if (showSelect) {
            showSelect.innerHTML = '<option value="">Select Showtime</option>' +
              data.shows.map(s => `<option value="${s.id}">${s.time_str} — ${s.screen} (₹${s.price})</option>`).join('');
            showSelect.disabled = false;
          }
        });
    });
  }
}

/* 7. KEYBOARD ACCESSIBILITY */
function initEscKeyHandler() {
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const openModals = document.querySelectorAll('.modal.show');
      openModals.forEach(m => {
        const bsModal = bootstrap.Modal.getInstance(m);
        if (bsModal) bsModal.hide();
      });
    }
  });
}

