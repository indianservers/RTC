# RTC OFFLINE AI — PHASE 4A
## Build the Complete Working Passenger App and Admin Interface

You are a principal frontend engineer, UI/UX architect, full-stack developer and conversational application designer.

Continue working in the EXISTING RTC Offline AI repository.

The user wants to SEE AND USE THE APPLICATION NOW.

Do not provide another architecture-only response.

Build a working graphical application connected to the existing RTC backend.

## NON-NEGOTIABLE REQUIREMENTS

- English text only for this phase.
- No microphone or speech development.
- No GPT or cloud AI services.
- No external inference.
- No CDN dependencies or Google Fonts.
- All frontend assets must load locally.
- Use the existing backend and database.
- Do not duplicate APIs, tables or business logic.
- Preserve existing trained models and NLP components.
- Use actual enquiry API responses.
- Mark fictional timetable records as DEMO.
- Do not implement payment or real ticket booking.
- Prioritize an immediately runnable, usable app.

## 1. FRONTEND STACK

Use:
- React
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui or compatible locally installed components
- Lucide icons
- TanStack Query
- TanStack Table
- React Router
- Recharts for admin visualizations

Inspect package availability and reuse existing frontend libraries where possible.

Avoid unnecessary dependencies.

## 2. DESIGN DIRECTION

Build a premium transportation information system.

Visual characteristics:
- Snow-white background
- Deep navy navigation
- Restrained blue/teal accents
- Rounded modern cards
- Elegant, readable typography
- Clear hierarchy
- Excellent spacing
- Beautiful tab navigation
- Consistent iconography
- Desktop, tablet and mobile responsive
- Accessible contrast
- Fast interactions

The app should feel like an enterprise-grade product, not a college project.

Avoid excessive gradients, huge empty cards, decorative dashboards and cluttered navigation.

## 3. MAIN PASSENGER CHAT

Build the primary page as a professional chat experience.

Header:
- RTC Smart Enquiry branding
- Current bus stand
- Operator
- English language indicator
- Offline backend connection status
- Demo/live data indicator
- New conversation button

Conversation area:
- Passenger messages aligned right
- Assistant replies aligned left
- Message timestamps
- Typing/loading feedback
- Auto-scroll
- Retry failed enquiry
- Clear error feedback
- Contextual suggestion chips
- Rich bus result cards
- Journey comparison cards
- Service status and source information

Composer:
- Text input
- Enter to send
- Shift+Enter for newline
- Send button
- Disabled state while submitting
- Helpful placeholder
- Keyboard accessibility

Do not implement a microphone button in this phase.

## 4. CONNECT TO EXISTING NLP BACKEND

Use the existing conversation APIs.

Prefer:
POST /api/v1/conversation/message

Reuse the existing session ID.

Support:
- Conversation memory
- Contextual follow-ups
- Multi-intent questions
- Corrections
- Selected bus references
- Route planning
- Clarification replies
- Session reset

Do not replace the real NLP backend with frontend regex matching.

Do not fabricate successful API responses.

If a backend endpoint is missing, implement only the minimum compatible adapter and document it.

## 5. RICH BUS RESULT CARDS

Display actual backend fields:

- RTC operator
- Service number
- Bus category
- AC or non-AC
- Seater or sleeper
- Source station
- Destination
- Departure
- Arrival
- Journey duration
- Fare
- Platform
- Seat availability status
- Scheduled/live status
- Data freshness

Fields with unknown values must display "Not available" or "Not confirmed".

Never treat unknown fares as zero.

Allow:
- Select this bus
- View stops
- Compare
- Ask about this bus

Selecting a service must update conversation context through the backend rather than only changing frontend state.

## 6. JOURNEY PLANNER

Provide a separate route-planning page.

Include:
- Source
- Destination
- Travel date
- Earliest departure
- Arrival deadline
- Operator
- Bus type
- AC/sleeper filters
- Fare ceiling
- Direct buses only
- Maximum transfers

Display:
- Direct routes
- Connecting routes
- Transfer stations
- Waiting times
- Total duration
- Total known fare
- Cheapest option
- Fastest arrival
- Fewest transfers

Do not invent journeys.

Reuse Phase 3B APIs where available.

## 7. SEARCH AND FILTER PAGE

Create a fast bus search experience.

Allow filtering by:
- Destination
- Departure window
- Category
- AC/non-AC
- Sleeper/seater
- Fare
- Availability
- Operator

Include intelligent station autocomplete from existing station/alias APIs.

Handle ambiguous stations.

## 8. JOURNEY DETAILS

Create a detailed service view.

Include:
- Route timeline
- Ordered intermediate stops
- Boarding/alighting permissions
- Scheduled stop times
- Available fare details
- Service category and amenities
- Platform details
- Current operational status
- Source and freshness indicators

Use actual route-stop and trip data.

## 9. ADMIN DASHBOARD

Build a protected admin area.

Sections:
- Overview
- RTC Operators
- Stations
- Depots
- Bus Categories
- Routes
- Services
- Timetables
- Fare Rules
- Platform Assignments
- Service Exceptions
- Data Imports
- NLP Diagnostics
- System Status

Use existing backend admin APIs.

Do not expose admin mutations without authentication and authorization.

If a required admin API is absent, display a truthful read-only page rather than fabricating editable functionality.

## 10. DATA MANAGEMENT SCREENS

Implement searchable lists with:
- Sorting
- Filtering
- Pagination
- Column visibility
- Inline status badges
- Detail views
- Add/edit forms where supported
- Validation messages
- Confirmation for destructive operations

Provide CSV import interface only where a backend import API actually exists.

## 11. NLP DIAGNOSTICS

Create a developer-only diagnostics screen.

Display:
- Original passenger message
- Normalized text
- Intent predictions
- Classifier name/version
- Entities
- Confidence/calibrated score
- Conversation context
- Applied filters
- Invoked enquiry function
- Result counts
- Processing latency
- Errors

Do not expose diagnostics to ordinary passengers.

## 12. MODEL AND SYSTEM STATUS

Show genuine backend state:

- Active NLP model
- Model readiness
- Deterministic fallback availability
- Database connectivity
- Loaded RTC operators
- Available stations
- Number of services
- Data import recency
- Demo/verified data source

Never label the system as AI-trained when only deterministic NLP is active.

## 13. OFFLINE REQUIREMENTS

The browser must be able to communicate with the local FastAPI backend without internet.

Ensure:
- No CDN
- No remote fonts
- No external analytics
- No internet image requests
- No externally hosted scripts
- No cloud authentication

Test after building production frontend assets.

Use local assets and APIs only.

## 14. RESPONSIVE DESIGN

Desktop:
- Efficient sidebar
- Wide conversation area
- Optional journey-results side panel

Tablet:
- Collapsible navigation
- Comfortable touch targets
- Responsive result cards

Mobile:
- Full-width chat
- Compact header
- Sticky composer
- Single-column cards
- Easy navigation

No horizontal overflow.

## 15. SECURITY

Implement:
- Safe text rendering
- No arbitrary HTML injection
- Protected admin routes
- Proper session handling
- Request validation
- Rate limiting where required
- Safe error messages
- No secrets in frontend bundles

Do not confuse hidden navigation with authorization.

Admin API access must be enforced by the backend.

## 16. TESTING

Add Playwright tests for:

1. App loads offline
2. Chat sends a message
3. Conversation response displays
4. Follow-up retains context
5. Destination correction works
6. New conversation clears context
7. Bus selection updates backend context
8. Unknown fare renders correctly
9. Demo data is labelled
10. Journey details display
11. Route planning handles no results
12. Station search works
13. Admin routes require authentication
14. Mobile layout works
15. Keyboard navigation works

Use realistic local fixture data for tests.

Do not fake successful production behaviour.

## 17. RUN THE APPLICATION

Provide a one-command Windows development startup.

For example:
start-rtc.ps1

It should:
- Validate local environment
- Start FastAPI backend
- Start Vite frontend
- Print local URLs
- Report missing dependencies
- Avoid downloading packages at runtime

Document production build and offline installation steps.

Use the actual project paths and commands.

## 18. FINAL DELIVERABLES

Deliver:
1. Working passenger chat interface
2. Live connection to RTC conversation backend
3. Bus result cards
4. Search/filter page
5. Journey planning page
6. Journey details
7. Admin dashboard
8. Data management screens
9. NLP diagnostics
10. System status page
11. Responsive layouts
12. Automated frontend tests
13. Local startup script
14. Updated README

Run backend and frontend tests.

Fix integration issues.

Report:
- Files created or modified
- Pages implemented
- APIs connected
- Tests passed/failed
- Known limitations
- Exact local startup command

Do not claim the application works without actually running it.

Do not stop after generating static mockups.

The main success criterion is that a passenger can open the application, type "Next bus to Nellore?", receive a real database-grounded answer and continue asking contextual questions.

Begin implementation immediately.