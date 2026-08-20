# CinePrime Button Audit

## Original Controls

| Control | Location | Action | Status |
|---|---|---|---|
| Brand Logo | Top Navbar | Navigate to `movies:listing` (Home) | FUNCTIONAL |
| Mobile Navbar Toggler | Top Navbar | Collapse/Expand Navbar | FUNCTIONAL |
| Home | Top Navbar | Navigate to `movies:listing` | FUNCTIONAL |
| Movies | Top Navbar | Navigate to `movies:listing` | FUNCTIONAL |
| Now Showing | Top Navbar | Filter movies by `status=NOW_SHOWING` | FUNCTIONAL |
| Upcoming | Top Navbar | Filter movies by `status=UPCOMING` | FUNCTIONAL |
| Theaters | Top Navbar | Navigate to `theaters:list` | FUNCTIONAL |
| Search Input & Submit | Top Navbar | Search movies, cast, directors | FUNCTIONAL |
| Notifications Bell Icon | Top Navbar | Navigate to `notifications:list` | FUNCTIONAL |
| User Profile Dropdown | Top Navbar | Toggle User Menu | FUNCTIONAL |
| Profile | Profile Dropdown | Navigate to `accounts:profile` | FUNCTIONAL |
| My Bookings | Profile Dropdown | Navigate to `bookings:my_bookings` | FUNCTIONAL |
| Watchlist | Profile Dropdown | Navigate to `movies:watchlist` | FUNCTIONAL |
| Admin Dashboard | Profile Dropdown | Navigate to `custom_admin_dashboard` | FUNCTIONAL |
| Logout | Profile Dropdown | Logout user (`accounts:logout`) | FUNCTIONAL |
| Login Button | Top Navbar (Guest) | Navigate to `accounts:login` | FUNCTIONAL |
| Sign Up Button | Top Navbar (Guest) | Navigate to `accounts:register` | FUNCTIONAL |
| Alert Close Button | Global Messages | Dismiss alert | FUNCTIONAL |
| Home | Sidebar | Navigate to `movies:listing` | DUPLICATE |
| Browse Movies | Sidebar | Navigate to `movies:listing` | FUNCTIONAL |
| Now Showing | Sidebar | Filter movies by `status=NOW_SHOWING` | DUPLICATE |
| Upcoming | Sidebar | Filter movies by `status=UPCOMING` | DUPLICATE |
| Top Rated | Sidebar | Filter movies by `sort=rating` | FUNCTIONAL |
| Trending | Sidebar | Filter movies by `sort=popular` | FUNCTIONAL |
| Theaters | Sidebar | Navigate to `theaters:list` | DUPLICATE |
| Watchlist | Sidebar | Navigate to `movies:watchlist` | FUNCTIONAL |
| My Bookings | Sidebar | Navigate to `bookings:my_bookings` | FUNCTIONAL |
| Profile | Sidebar | Navigate to `accounts:profile` | FUNCTIONAL |
| Claim Promo | Sidebar Promo Card | Navigate to `movies:listing` | FUNCTIONAL |
| Search Box & Submit | Discovery Bar | Submit search query | FUNCTIONAL |
| Clear Search X | Discovery Bar | Clear search filter | FUNCTIONAL |
| Sort Dropdown | Discovery Bar | Change sorting mode | FUNCTIONAL |
| Mobile Filters Drawer | Discovery Bar | Toggle filter drawer | FUNCTIONAL |
| Clear All Filters | Filter Sidebar | Reset all discovery filters | FUNCTIONAL |
| Genre Filter | Filter Sidebar | Filter by Genre | FUNCTIONAL |
| Language Filter | Filter Sidebar | Filter by Language | FUNCTIONAL |
| City Filter | Filter Sidebar | Filter by City | FUNCTIONAL |
| Theater Filter | Filter Sidebar | Filter by Theater | FUNCTIONAL |
| Release Date Filter | Filter Sidebar | Filter by Release Date | FUNCTIONAL |
| Minimum Rating Filter | Filter Sidebar | Filter by Minimum Rating | FUNCTIONAL |
| Show Timing Filter | Filter Sidebar | Filter by Showtime Range | FUNCTIONAL |
| Price Range Filter | Filter Sidebar | Filter by Ticket Price | FUNCTIONAL |
| Apply Filters Button | Filter Sidebar | Submit filter form | FUNCTIONAL |
| Reset Button | Filter Sidebar | Reset filter form | FUNCTIONAL |
| Watch Trailer | Movie Card | Open Trailer Video Modal | FUNCTIONAL |
| View Details | Movie Card | Navigate to `movies:detail` | FUNCTIONAL |
| Book Now | Movie Card | Navigate to `bookings:booking_movie` | FUNCTIONAL |
| Pagination Prev/Next | Movie Grid | Navigate movie pages | FUNCTIONAL |
| Watch Trailer | Movie Details | Open Trailer Video Modal | FUNCTIONAL |
| Book Tickets | Movie Details | Navigate to `bookings:booking_movie` | FUNCTIONAL |
| Add to Watchlist | Movie Details | Toggle Watchlist item | FUNCTIONAL |
| Select Seats | Movie Details | Navigate to `bookings:seat_selection` | FUNCTIONAL |
| Write Review | Movie Details | Navigate to `reviews:write_review` | FUNCTIONAL |
| Report Review | Movie Details | Navigate to `reviews:report_review` | FUNCTIONAL |
| Similar Movie Details | Movie Details | Navigate to `movies:detail` | FUNCTIONAL |
| Select Theater / Date / Show | Quick Booking | Dynamic AJAX selects | FUNCTIONAL |
| View Shows | Theater List | Navigate to `theaters:detail` | FUNCTIONAL |
| Book Tickets | Theater Detail | Navigate to `bookings:seat_selection` | FUNCTIONAL |
| Select Seat Button | Seat Selection | Toggle seat selection | FUNCTIONAL |
| Proceed to Checkout | Seat Selection | Submit booking form | FUNCTIONAL |
| Pay with Razorpay | Checkout Page | Initiate Razorpay SDK / popup | FUNCTIONAL |
| Simulate Test Payment | Checkout Page | Execute test payment verification | FUNCTIONAL |
| Download PDF Ticket | Booking Confirmation | Download ticket PDF | FUNCTIONAL |
| Cancel Booking | Booking Confirmation | Navigate to cancellation form | FUNCTIONAL |

## Duplicate Controls

| Control A | Control B | Same Function? | Decision |
|---|---|---|---|
| Top Nav "Home" | Sidebar "Home" | YES (`movies:listing`) | Remove Sidebar "Home" |
| Top Nav "Now Showing" | Sidebar "Now Showing" | YES (`movies:listing?status=NOW_SHOWING`) | Remove Sidebar "Now Showing" |
| Top Nav "Upcoming" | Sidebar "Upcoming" | YES (`movies:listing?status=UPCOMING`) | Remove Sidebar "Upcoming" |
| Top Nav "Theaters" | Sidebar "Theaters" | YES (`theaters:list`) | Remove Sidebar "Theaters" |

## Removed Controls

| Removed | Reason | Replacement |
|---|---|---|
| Sidebar "Home" | Redundant duplicate of Top Nav "Home" | Top Nav "Home" |
| Sidebar "Now Showing" | Redundant duplicate of Top Nav "Now Showing" | Top Nav "Now Showing" |
| Sidebar "Upcoming" | Redundant duplicate of Top Nav "Upcoming" | Top Nav "Upcoming" |
| Sidebar "Theaters" | Redundant duplicate of Top Nav "Theaters" | Top Nav "Theaters" |

## Consolidated Controls

| Original Controls | Final Control | Reason |
|---|---|---|
| Movie Card View Details Button (modal trigger) | Direct `<a>` Link to `movies:detail` | Direct navigation allows full movie detail inspection while modal trailer handles quick preview. |
| Sidebar Top Rated Link (`min_rating=4.0`) | Sidebar Top Rated Link (`sort=rating`) | Uses standard discovery service sorting. |
| Sidebar Trending Link (`movies:listing`) | Sidebar Trending Link (`sort=popular`) | Uses standard discovery service popularity sorting. |

## Broken Controls

| Control | Problem | Fix |
|---|---|---|
| Top Nav Search Button | Missing `aria-label` | Added `aria-label="Search movies"` |
| Notifications Bell Icon | Missing `aria-label` | Added `aria-label="Notifications"` |
| User Profile Toggle | Missing `aria-label` | Added `aria-label="Open profile menu"` |
| Mobile Navbar Toggler | Missing `aria-label` | Added `aria-label="Toggle navigation menu"` |
| Carousel Scroll Buttons | Missing `aria-label` | Added `aria-label="Scroll left"` & `aria-label="Scroll right"` |

## Final Navigation

### TOP NAVIGATION
- Home
- Movies
- Now Showing
- Upcoming
- Theaters
- Search
- Notifications
- Profile

### SIDEBAR
- Browse Movies
- Top Rated
- Trending
----------------
- Watchlist
- My Bookings
- Profile
