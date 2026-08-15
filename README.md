# CinePrime — Complete Django Movie Management & Booking System

CinePrime is a modern, production-ready Movie Management and Movie Booking web application built with **Django**, **Django REST Framework (DRF)**, **Bootstrap 5**, and custom **Glassmorphic Cinema Styling**.

---

## 🌟 Key Features

### 🎬 Movie Management & Discovery
- **Browsing & Filtering:** Filter movies by Genre, Language, Age Certification, Rating, and Showing Status (Now Showing, Upcoming).
- **Search System:** Real-time search across Movie Titles, Cast Members, and Directors.
- **Featured Sections:** Trending Now, Now Showing, Upcoming Movies, Recently Released, and Top Rated.
- **Secure YouTube Trailers:** Extracted video ID parser embedding safe iframe modals (no arbitrary HTML injection vulnerabilities).
- **Multiple Movie Images:** Hero backdrops, primary posters, and image galleries.
- **Cast & Crew:** Detailed cast roles (Actor, Actress, Director, Producer, Writer, Music Director, Cinematographer).

### 🎟️ Interactive Booking & Seat Selection
- **Theater & Screen Management:** Support for 2D, 3D, IMAX, and 4DX screens.
- **Auto-Generated Seat Matrix:** Seats automatically generated in grids (Regular, Premium, Recliner) upon Screen creation.
- **Show Schedules:** Overlap protection and screen validation.
- **Interactive Seat Map:** Live seat selection UI with dynamic subtotal and convenience fee recalculation.
- **Atomic Double-Booking Protection:** Concurrency locking using `db.transaction.atomic()` and `select_for_update()`.
- **Mock Payment Gateway:** Supports UPI, Credit/Debit Cards, Net Banking, and Wallets with transaction logging.
- **Digital Ticket (PDF & QR):** Downloadable PDF ticket generated via ReportLab featuring scannable QR codes.

### ⭐ Ratings, Reviews & Verified Viewers
- **Strict Eligibility:** Only users who booked and watched the movie can rate/review.
- **Verified Viewer Badge (`✓ VERIFIED VIEWER`):** Automatically awarded to verified ticket holders.
- **Review Moderation & Reporting:** Users can report inappropriate reviews; Admins can moderate/hide reported content.
- **Dynamic Average Rating & Distribution:** Real-time recalculation of 5-star to 1-star percentage bars.

### 🤖 Intelligent Recommendations
- **Similar Movies Engine:** Dynamic weighted similarity matching Genre (+3), Language (+2), Director (+2), and Rating (+1).
- **Trending Score Engine:** Calculated from booking volume, page views, rating, and review count.

### 📊 Custom Admin Dashboard & APIs
- **Custom Admin Analytics:** Charts and statistics for revenue, bookings, user signups, popular movies, and review reports.
- **REST APIs:** DRF endpoints for `/api/movies/`, `/api/shows/`, `/api/bookings/`, `/api/reviews/`, etc.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+
- pip

### 2. Installation & Setup

Clone or open the repository, then create a virtual environment and install dependencies:

```bash
# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

### 4. Database Setup & Migrations

```bash
# Run migrations
python manage.py makemigrations
python manage.py migrate
```

### 5. Seed Demo Data
Populate the database with sample movies, theaters, screens, seat layouts, show schedules, users, and reviews:

```bash
python manage.py seed_data
```

### 6. Demo User Credentials
- **Admin Panel & Custom Dashboard:**
  - Username: `admin`
  - Password: `admin123`
  - URL: `http://127.0.0.1:8000/admin/` or `http://127.0.0.1:8000/dashboard/admin/`
- **Registered User:**
  - Username: `johndoe`
  - Password: `user123`

### 7. Run Local Development Server

```bash
python manage.py runserver
```
Open `http://127.0.0.1:8000/` in your web browser.

---

## 🧪 Running Automated Tests

```bash
python manage.py test
```

---

## 🔌 REST API Endpoints

- `GET /api/movies/` — List all movies (supports filtering & search)
- `GET /api/movies/<id>/` — Retrieve movie details
- `GET /api/movies/trending/` — List trending movies
- `GET /api/movies/recent/` — List recently released movies
- `GET /api/movies/similar/<id>/` — Get similar movie recommendations
- `GET /api/genres/` — List genres
- `GET /api/languages/` — List languages
- `GET /api/theaters/` — List active theaters
- `GET /api/shows/` — List show schedules
- `POST /api/bookings/` — Create booking
- `POST /api/reviews/` — Submit review

---

## 🛡️ License & Credits
Built as a complete Django Movie Management & Booking System.
