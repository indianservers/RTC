# SYNTHETIC RTC laboratory report

All information is generated DEMO data, never official APSRTC information.

- cities: 60
- stations: 120
- routes: 600
- trips: 2400
- scenarios: 540
- questions: 540

Artifact validation: PASS
Gold scenario pass rate: 540/540 (100.0%); 0.004392 seconds.

## intent

- amenities: 50
- arrival: 10
- cheapest: 10
- departure: 20
- fare: 120
- gps: 20
- journey: 150
- platform: 30
- seats: 40
- selection: 40
- status: 50

## category

- A: 30
- B: 50
- C: 110
- D: 130
- E: 40
- F: 40
- G: 30
- H: 30
- I: 40
- J: 40

## bus_category

- Amaravathi AC: 54
- Express: 108
- Garuda: 54
- Indra AC: 54
- Pallevelugu: 108
- Super Luxury: 54
- Ultra Deluxe: 108

## date_time_case

- calendar: 30
- daytime: 500
- overnight: 10

## error_unknown_case

- AMBIGUOUS_SELECTION: 20
- FARE_EXPIRED: 20
- FARE_UNKNOWN: 10
- GPS_STALE: 10
- GPS_UNKNOWN: 10
- PLATFORM_UNKNOWN: 10
- SEATS_STALE: 10
- SEATS_UNKNOWN: 10
- SERVICE_UNKNOWN: 10

## Missing coverage and limits

- Production integration and real classifier evaluation have not been run.
- Bus-category labels measure fixture distribution, not category-specific production policy.
- Synthetic coverage does not validate official tariffs, schedules or concessions.
