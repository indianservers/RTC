# RTC OFFLINE AI — PHASE 4B
## Premium Interactive Passenger Experience, Smart UI and Full Backend Integration

You are a principal UI/UX designer, senior React engineer, conversational interface specialist and full-stack software architect.

Continue development in the EXISTING RTC Offline AI repository.

Phase 4A introduced the passenger chat interface, search, journey planning, journey details and administrative pages.

Your objective is to make every major screen polished, informative, interactive and correctly connected to the real RTC backend.

IMPORTANT:
- English text only.
- No voice, microphone, ASR or TTS development.
- No GPT or cloud services.
- Entire application must function offline.
- Use the existing React + TypeScript + FastAPI architecture.
- Preserve existing database schema and business logic.
- Do not create duplicate APIs or frontend components.
- Do not overwrite working interfaces unnecessarily.
- Do not fabricate timetable, fare or availability information.
- Keep DEMO information visibly labelled.
- No ticket payments or unsupported booking features.

## 1. AUDIT THE EXISTING UI

Inspect every implemented Phase 4A screen.

Identify:
- Broken interactions
- Placeholder content
- Duplicate components
- Inconsistent typography
- Poor spacing
- Excessive scrolling
- Crowded result cards
- Unnecessary navigation
- Missing loading/error states
- Nonfunctional buttons
- Incorrect API mappings
- Missing accessibility labels
- Mobile responsiveness issues

Create a concise gap report.

Fix actual problems rather than rebuilding the entire frontend without reason.

## 2. BUILD A UNIFIED DESIGN SYSTEM

Use:
- Snow-white or near-white backgrounds
- Deep navy navigation
- Restrained teal and blue highlights
- Premium typography
- Rounded cards
- Consistent shadows and borders
- Lucide icons
- Compact but readable data presentation
- Excellent contrast
- Accessible keyboard navigation

Create shared components:
- PageHeader
- SearchField
- StationSelector
- ServiceCard
- FareBadge
- StatusIndicator
- RouteTimeline
- JourneyCard
- FilterBar
- EmptyState
- ErrorState
- LoadingSkeleton
- ConfirmDialog
- DataTable
- ContextualActions

Centralize design tokens.

Avoid decorative gradients, excessive whitespace and oversized headings.

## 3. PASSENGER CHAT — MAJOR ENHANCEMENT

Make the chat experience the center of the application.

Features:
- Chat bubbles with timestamps
- Session-aware conversation
- Interactive query suggestions
- Auto-scroll and scroll-to-latest
- Retry failed requests
- New conversation
- Clear context
- Selected service tracking
- Context-aware next-question suggestions
- Rich service results embedded inside conversation
- Compact journey comparisons
- Clarification choices
- Visible demo and source status

Add contextual suggestion chips such as:
- What is the fare?
- Show AC buses
- Show cheaper options
- View intermediate stops
- What about tomorrow?
- Show connecting buses
- Which platform?

These chips must send actual follow-up enquiries to the conversation backend.

Do not implement frontend-only fake replies.

## 4. SMART RESULT CARDS

Redesign service results with:

- Service number
- RTC operator
- Bus category
- AC / non-AC
- Sleeper / seater
- Departure time
- Arrival time
- Duration
- Origin and destination
- Fare
- Platform status
- Seat availability
- Operational status
- Source freshness

Use responsive layouts.

Desktop:
Show multiple services with clear comparisons.

Mobile:
Compact vertical cards.

Actions:
- Select service
- View details
- View stops
- Compare
- Ask about service

Every action must work through existing backend context or enquiry APIs.

Do not make buttons that only change appearance.

## 5. INTERACTIVE JOURNEY PLANNER

Create or improve:

- Source and destination autocomplete
- Swap origin/destination
- Travel date picker
- Departure time window
- Arrival deadline
- Bus category selection
- AC/non-AC
- Sleeper/seater
- Fare ceiling
- Direct-only filter
- Maximum transfers

Show direct and connecting journeys.

Present:
- Route timeline
- Transfer location
- Transfer waiting duration
- Total duration
- Total known fare
- Departure/arrival
- Service categories
- Warnings

Offer sorting by:
- Earliest arrival
- Cheapest known fare
- Fewest changes
- Shortest duration

Unknown values must not distort ranking.

## 6. JOURNEY COMPARISON

Allow selecting two or three valid journeys.

Compare:
- Fare
- Duration
- Departure
- Arrival
- Transfers
- Bus types
- Amenities
- Seat availability
- Platform status

Highlight differences clearly.

Only label a journey "cheapest" or "fastest" when the relevant data is known and comparable.

Do not claim a winner when data is incomplete.

## 7. JOURNEY DETAILS

Create a detailed service view with tabs:

Overview
Route & Stops
Fares
Amenities
Operational Status

Overview:
Service, category, departure, arrival, source and destination.

Route & Stops:
Ordered timeline with scheduled times, boarding and alighting permissions.

Fares:
Segment fare, known concession information and source.

Amenities:
Only verified properties.

Operational Status:
Scheduled, delayed, cancelled or unknown information with freshness timestamp.

Do not invent stop arrival times.

## 8. ADMIN INTERFACE

Improve the admin pages using a consistent application shell.

Pages:
- Dashboard
- Operators
- Stations
- Bus Categories
- Routes
- Services
- Timetables
- Fare Rules
- Platform Assignments
- Operational Events
- Data Imports
- NLP Diagnostics
- Model Status
- Data Quality

Support:
- Search
- Filters
- Sorting
- Pagination
- Detail drawers
- Validated forms
- Confirmation dialogs
- Role-aware permissions

Only enable mutations for operations supported and authorized by the backend.

Do not create fake CRUD functionality.

## 9. DATA QUALITY SCREEN

Create a dedicated Data Quality page.

Display:
- Stations missing aliases
- Routes missing stops
- Services missing valid calendars
- Trips missing scheduled stop times
- Services without fare data
- Expired fare rules
- Duplicate service codes
- Unassigned platforms
- Stale operational updates
- Invalid data import rows

Use actual database validation results.

Provide:
- Issue severity
- Affected record
- Suggested correction
- Filter by issue
- Link to record where possible

Do not invent quality metrics.

## 10. NLP DIAGNOSTICS

Make NLP diagnostics useful for developers.

Display:
- Input text
- Normalized text
- Detected intent
- Secondary intents
- Model name/version
- Confidence
- Extracted entities
- Context changes
- Selected station/service
- Enquiry function
- Result count
- Processing latency
- Response template

Add a test input box for developers.

Use actual inference output.

Do not create mock confidence scores.

## 11. SYSTEM STATUS

Display:
- Backend connection
- Database status
- Active NLP model
- Fallback classifier status
- Loaded operators
- Stations
- Services
- Dataset/model version
- Data source status
- Last import
- Offline operation indicator

Distinguish:
- Local backend connected
- Backend unavailable
- Operational data stale
- Demo-only data

Do not treat browser offline status alone as proof that the application is fully offline.

## 12. PERFORMANCE IMPROVEMENTS

Use:
- Query caching where suitable
- Debounced station autocomplete
- Paginated result lists
- Lazy loading for admin routes
- Memoized expensive rendering
- Efficient tables
- Cancellation of obsolete requests
- Stable keys for result cards

Avoid unnecessary backend requests.

Do not cache live operational information beyond its configured freshness period.

## 13. ERROR AND EMPTY STATES

Implement helpful responses for:
- No bus found
- No direct route
- Unknown fare
- Unknown seat inventory
- Unconfirmed platform
- Backend disconnected
- Ambiguous destination
- Expired session
- Invalid filter combination
- No permission to edit
- Import failure

Offer relevant recovery actions.

Do not silently reset passenger filters.

## 14. MOBILE AND KIOSK READINESS

Desktop:
- Efficient navigation
- Wide chat and journey results
- Minimal scrolling

Tablet:
- Touch-friendly inputs
- Collapsible navigation
- Readable service cards

Mobile:
- Compact header
- Sticky chat composer
- Full-width cards
- No horizontal overflow

Kiosk:
- Large touch targets
- Clear restart action
- Automatic session expiration
- No display of previous passenger data after reset

Do not implement microphone controls yet.

## 15. ACCESSIBILITY

Provide:
- Semantic HTML
- Accessible labels
- Keyboard navigation
- Focus management
- Screen-reader-friendly status messages
- High contrast
- Proper error association
- Consistent loading announcements

Avoid color-only communication.

## 16. TESTING

Add Playwright tests for:

1. Chat sends a real enquiry.
2. Service results render.
3. Contextual follow-ups work.
4. Selected service persists.
5. Changing destination invalidates selection.
6. Journey planner filters correctly.
7. Fare comparison handles missing values.
8. Route timeline follows stop sequence.
9. No-results page works.
10. Offline frontend assets load.
11. Admin authorization is enforced.
12. Data quality issues display.
13. NLP diagnostics use real values.
14. Mobile layout has no overflow.
15. Kiosk reset clears prior session.
16. Error recovery works.
17. Unknown fields are not fabricated.
18. Demo data remains labelled.
19. All visible action buttons work.
20. Existing backend APIs remain compatible.

Run the full frontend and backend regression suite.

## 17. DELIVERABLES

Deliver:
1. Polished passenger chat.
2. Smart service result cards.
3. Interactive journey planner.
4. Journey comparison.
5. Detailed service tabs.
6. Consistent admin interface.
7. Data Quality page.
8. NLP Diagnostics page.
9. System Status page.
10. Responsive mobile/kiosk layouts.
11. Automated E2E tests.
12. UI/UX improvement report.

Run the actual application and verify major workflows.

Do not stop after creating static screenshots.

At completion report:
- Screens improved
- Components added/reused
- APIs integrated
- Tests executed
- Broken functionality fixed
- Remaining limitations

Do not implement Phase 4C, Telugu or voice.

Start implementing Phase 4B immediately.