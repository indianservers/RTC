# Intent ambiguity rules

These are semantic distinctions, not empirical model confusion scores.

## NEXT_BUS / FIRST_BUS
NEXT_BUS: Next available after a threshold.
FIRST_BUS: Earliest departure in the requested operating day.
Do not substitute one interpretation for the other without the missing qualifier or a clarification.

## LAST_BUS / DEPARTURES_BEFORE
LAST_BUS: Final departure within operating-day bounds.
DEPARTURES_BEFORE: Any departure earlier than a time cutoff.
Do not substitute one interpretation for the other without the missing qualifier or a clarification.

## ARRIVAL_TIME / ESTIMATED_ARRIVAL
ARRIVAL_TIME: Published or explicitly labelled arrival time.
ESTIMATED_ARRIVAL: Fresh verified operational ETA; scheduled time is insufficient.
Do not substitute one interpretation for the other without the missing qualifier or a clarification.

## BUS_AT_TIME / DEPARTURES_AFTER
BUS_AT_TIME: Departure within an explicit proximity window.
DEPARTURES_AFTER: All departures strictly following a lower bound.
Do not substitute one interpretation for the other without the missing qualifier or a clarification.

## BUS_VIA_LOCATION / INTERMEDIATE_STOP
BUS_VIA_LOCATION: Path travels through the location.
INTERMEDIATE_STOP: Scheduled halt/boarding permissions must be established.
Do not substitute one interpretation for the other without the missing qualifier or a clarification.

## DIRECT_BUS / DESTINATION_REACHABILITY
DIRECT_BUS: Single service with no transfer.
DESTINATION_REACHABILITY: Any feasible path, potentially connecting.
Do not substitute one interpretation for the other without the missing qualifier or a clarification.

## GET_FARE / FARE_COMPARISON
GET_FARE: Applicable fare for a valid travel segment.
FARE_COMPARISON: Compare fares on the same segment/date.
Do not substitute one interpretation for the other without the missing qualifier or a clarification.

## CHEAPEST_BUS / CONCESSION_ENQUIRY
CHEAPEST_BUS: Rank known applicable fares.
CONCESSION_ENQUIRY: Explain eligibility rules without assuming eligibility.
Do not substitute one interpretation for the other without the missing qualifier or a clarification.

## BUS_DELAY / LIVE_BUS_STATUS
BUS_DELAY: Verified delay duration or reason.
LIVE_BUS_STATUS: Current verified operational state/location.
Do not substitute one interpretation for the other without the missing qualifier or a clarification.

## BUS_PLATFORM / PLATFORM_CHANGE
BUS_PLATFORM: Current valid bay assignment.
PLATFORM_CHANGE: Compare assignment history to confirm a reassignment.
Do not substitute one interpretation for the other without the missing qualifier or a clarification.

## BOOKING_STATUS / SEAT_AVAILABILITY
BOOKING_STATUS: Authorized existing booking record.
SEAT_AVAILABILITY: Segment-specific fresh remaining inventory.
Do not substitute one interpretation for the other without the missing qualifier or a clarification.

## Multi-intent composition

[
  {
    "intents": [
      "NEXT_BUS",
      "GET_FARE"
    ],
    "shared_slots": [
      "origin",
      "destination",
      "travel_date"
    ],
    "dependencies": {
      "GET_FARE": [
        "NEXT_BUS"
      ]
    },
    "reuse": [
      "service_id",
      "trip_id",
      "segment"
    ]
  },
  {
    "intents": [
      "BUS_DELAY",
      "BUS_PLATFORM"
    ],
    "shared_slots": [
      "trip_id",
      "station"
    ],
    "dependencies": {}
  },
  {
    "intents": [
      "CHEAPEST_BUS"
    ],
    "constraints": {
      "ac": true,
      "sleeper": true
    },
    "shared_slots": [
      "travel_date"
    ]
  },
  {
    "intents": [
      "FASTEST_BUS",
      "INTERMEDIATE_STOP"
    ],
    "dependencies": {
      "INTERMEDIATE_STOP": [
        "FASTEST_BUS"
      ]
    },
    "shared_slots": [
      "destination",
      "via"
    ]
  }
]

Dependency plans describe shared entities and result reuse; full execution-plan optimization is not implemented in Phase 2A.