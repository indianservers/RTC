# Phase 2B dataset quality report

PHASE 2B INCOMPLETE. No models trained.

Generated: 449. Schema-valid: 449. Unreviewed synthetic: 449. Human-reviewed: 0.

## Dataset categories

- SINGLE_INTENT: 300
- MULTI_INTENT: 16
- CONTEXTUAL: 12
- OUT_OF_SCOPE: 20
- AMBIGUOUS: 11
- NEGATION_CORRECTION: 13
- ASR_STYLE: 77

## Per-intent coverage

- ACCESSIBLE_BUS_AVAILABILITY: 5/200; 5 authored families.
- AC_BUS_AVAILABILITY: 5/200; 5 authored families.
- ALIGHTING_POINT: 5/200; 5 authored families.
- ALTERNATIVE_ROUTES: 5/200; 5 authored families.
- ARRIVAL_TIME: 5/200; 5 authored families.
- AVAILABLE_BUS_TYPES: 5/200; 5 authored families.
- BOARDING_POINT: 5/200; 5 authored families.
- BOOKING_OPTIONS: 5/200; 5 authored families.
- BOOKING_STATUS: 5/200; 5 authored families.
- BUSES_BETWEEN: 5/200; 5 authored families.
- BUSES_OPERATING_TODAY: 5/200; 5 authored families.
- BUS_AMENITIES: 5/200; 5 authored families.
- BUS_ARRIVED_STATUS: 5/200; 5 authored families.
- BUS_AT_TIME: 5/200; 5 authored families.
- BUS_CANCELLATION: 5/200; 5 authored families.
- BUS_CAPACITY: 5/200; 5 authored families.
- BUS_DELAY: 5/200; 5 authored families.
- BUS_DEPARTED_STATUS: 5/200; 5 authored families.
- BUS_PLATFORM: 5/200; 5 authored families.
- BUS_VIA_LOCATION: 5/200; 5 authored families.
- CANCELLATION_POLICY: 5/200; 5 authored families.
- CHEAPEST_BUS: 5/200; 5 authored families.
- COMPLAINT_GUIDANCE: 5/200; 5 authored families.
- CONCESSION_ENQUIRY: 5/200; 5 authored families.
- CONNECTING_BUSES: 5/200; 5 authored families.
- DEPARTURES_AFTER: 5/200; 5 authored families.
- DEPARTURES_BEFORE: 5/200; 5 authored families.
- DESTINATION_REACHABILITY: 5/200; 5 authored families.
- DIRECT_BUS: 5/200; 5 authored families.
- ELECTRIC_BUS_AVAILABILITY: 5/200; 5 authored families.
- ESTIMATED_ARRIVAL: 5/200; 5 authored families.
- FARE_COMPARISON: 5/200; 5 authored families.
- FASTEST_BUS: 5/200; 5 authored families.
- FIRST_BUS: 5/200; 5 authored families.
- GET_FARE: 5/200; 5 authored families.
- INTERMEDIATE_STOP: 5/200; 5 authored families.
- JOURNEY_DURATION: 5/200; 5 authored families.
- LAST_BUS: 5/200; 5 authored families.
- LIVE_BUS_STATUS: 5/200; 5 authored families.
- LOST_PROPERTY: 5/200; 5 authored families.
- LUGGAGE_RULES: 5/200; 5 authored families.
- NEXT_BUS: 5/200; 5 authored families.
- NON_AC_BUS_AVAILABILITY: 5/200; 5 authored families.
- OPERATOR_CONTACT: 5/200; 5 authored families.
- PLATFORM_CHANGE: 5/200; 5 authored families.
- REFUND_POLICY: 5/200; 5 authored families.
- RESERVATION_SUPPORTED: 5/200; 5 authored families.
- ROUTE_DISTANCE: 5/200; 5 authored families.
- ROUTE_STOPS: 5/200; 5 authored families.
- SEATER_AVAILABILITY: 5/200; 5 authored families.
- SEAT_AVAILABILITY: 5/200; 5 authored families.
- SERVICE_CATEGORY_COMPARISON: 5/200; 5 authored families.
- SERVICE_DISRUPTION: 5/200; 5 authored families.
- SERVICE_FREQUENCY: 5/200; 5 authored families.
- SERVICE_NUMBER_LOOKUP: 5/200; 5 authored families.
- SLEEPER_AVAILABILITY: 5/200; 5 authored families.
- SPECIAL_DAY_SCHEDULE: 5/200; 5 authored families.
- STATION_FACILITIES: 5/200; 5 authored families.
- STATION_HELPDESK: 5/200; 5 authored families.
- STATION_NAVIGATION: 5/200; 5 authored families.

## Quality findings

Near-duplicate pairs: 82 (normalized character similarity >=0.90; a heuristic, not semantic proof). Normalized duplicate text pairs: 0. Exact duplicate IDs: 0. Repeated annotated sentence shapes: 8.
Only five authored seed structures per intent exist. Station substitutions and ASR normalization are not counted toward the 200 single-intent target. Style-specific distribution targets remain incomplete; mean pairwise trigram overlap is recorded in the JSON report. The ASR set contains controlled synthetic phonetic variants, not measured Vosk errors. Most examples lack comprehensive entity labels; exact unambiguous DB spans are annotated, unclear roles are left absent. Unconfigured categories in older question seeds remain hypothetical mentions and have no fabricated IDs. Demo vocabulary is not official operator-service evidence.
No held-out splits were constructed; family and parent IDs are retained for Phase 2C. The supplied 300 Phase 2A examples are preserved separately. Current duplicate/diversity findings block training readiness. No 12000 or 16000 record claim is made.

## Schema failures

{
  "candidate_errors": [],
  "intentionally_invalid_fixture": [
    {
      "mutation": "Empty passenger text",
      "result": "REJECTED",
      "error": "1 validation error for Example"
    }
  ]
}

## Heuristic near-duplicate examples

[
  {
    "left": 1,
    "right": 373,
    "same_family": true,
    "label_conflict": false
  },
  {
    "left": 2,
    "right": 374,
    "same_family": true,
    "label_conflict": false
  },
  {
    "left": 6,
    "right": 375,
    "same_family": true,
    "label_conflict": false
  },
  {
    "left": 7,
    "right": 376,
    "same_family": true,
    "label_conflict": false
  },
  {
    "left": 12,
    "right": 377,
    "same_family": true,
    "label_conflict": false
  },
  {
    "left": 14,
    "right": 378,
    "same_family": true,
    "label_conflict": false
  },
  {
    "left": 17,
    "right": 379,
    "same_family": true,
    "label_conflict": false
  },
  {
    "left": 17,
    "right": 380,
    "same_family": true,
    "label_conflict": false
  },
  {
    "left": 22,
    "right": 381,
    "same_family": true,
    "label_conflict": false
  },
  {
    "left": 24,
    "right": 382,
    "same_family": true,
    "label_conflict": false
  },
  {
    "left": 27,
    "right": 383,
    "same_family": true,
    "label_conflict": false
  },
  {
    "left": 31,
    "right": 384,
    "same_family": true,
    "label_conflict": false
  },
  {
    "left": 32,
    "right": 385,
    "same_family": true,
    "label_conflict": false
  },
  {
    "left": 37,
    "right": 386,
    "same_family": true,
    "label_conflict": false
  },
  {
    "left": 42,
    "right": 387,
    "same_family": true,
    "label_conflict": false
  },
  {
    "left": 43,
    "right": 388,
    "same_family": true,
    "label_conflict": false
  },
  {
    "left": 46,
    "right": 389,
    "same_family": true,
    "label_conflict": false
  },
  {
    "left": 48,
    "right": 390,
    "same_family": true,
    "label_conflict": false
  },
  {
    "left": 52,
    "right": 391,
    "same_family": true,
    "label_conflict": false
  },
  {
    "left": 54,
    "right": 392,
    "same_family": true,
    "label_conflict": false
  }
]

## Remaining styles and entity coverage

{
  "styles": {
    "natural": 336,
    "contextual": 12,
    "clarification": 11,
    "negation": 13,
    "asr_like": 77
  },
  "entity_types": {
    "DESTINATION_STATION": 69,
    "ORIGIN_STATION": 9,
    "TIME": 7,
    "AC_PREFERENCE": 12,
    "VIA_STATION": 2,
    "SEAT_COUNT": 2,
    "BUS_CATEGORY": 4
  }
}

## Phase 2C readiness and reproduction

NOT READY for model training or Phase 2C acceptance. The combined candidate collection has 449 records: 300 reused Phase 2A seed questions plus 149 additional challenge/context records. Counts do not sum physical copies across category files, all.jsonl and export files. All records are SYNTHETIC and PENDING_HUMAN_REVIEW. Each of 60 intents still has only five single-intent examples. No semantic uniqueness claim is made. The 82 near-duplicate pairs include controlled parent/ASR variants; none of these is counted toward the 200-per-intent target.

Reproduce locally with python training/generation/generate.py and python training/validation/validate_phase2b.py. The vocabulary snapshot and fixed seed/version preserve provenance; database changes intentionally alter generated vocabulary/context and therefore snapshot checksums. Unchanged snapshot inputs reproduce identical records in tests. Existing Phase 2A files remain untouched. Family and parent linkage is retained, but no train/validation/test partitions are constructed. The validator rejects supplied cross-split family collisions without performing Phase 2C splitting.

Exports executed: CSV and local Hugging Face JSON-loader-compatible directory under training/datasets/generated/2b-v1/exports. Optional native Hugging Face Arrow save_to_disk requires datasets and is implemented behind --huggingface, but was not executed here. No upload or runtime network call is used. Existing application and models were not modified for data generation. No model training, UI or speech work occurred.
