# Entity schema

32 entity types. Unknown values remain absent rather than zero or false. Negative preferences use NE or NOT_IN constraints, not positive keyword matches. Canonical place/category values must refer to DB masters. Date/time interpretation uses the station timezone.

## ORIGIN_CITY
Value type: string. Nullable: True. Operators: EQ, NE, IN, NOT_IN.
never infer unknown data.

## DESTINATION_CITY
Value type: string. Nullable: True. Operators: EQ, NE, IN, NOT_IN.
never infer unknown data.

## ORIGIN_STATION
Value type: string. Nullable: True. Operators: EQ, NE, IN, NOT_IN.
never infer unknown data.

## DESTINATION_STATION
Value type: string. Nullable: True. Operators: EQ, NE, IN, NOT_IN.
never infer unknown data.

## VIA_STATION
Value type: string. Nullable: True. Operators: EQ, NE, IN, NOT_IN.
never infer unknown data.

## TRANSFER_STATION
Value type: string. Nullable: True. Operators: EQ, NE, IN, NOT_IN.
never infer unknown data.

## BOARDING_STATION
Value type: string. Nullable: True. Operators: EQ, NE, IN, NOT_IN.
never infer unknown data.

## ALIGHTING_STATION
Value type: string. Nullable: True. Operators: EQ, NE, IN, NOT_IN.
never infer unknown data.

## BUS_CATEGORY
Value type: string. Nullable: True. Operators: EQ, NE, IN, NOT_IN.
never infer unknown data.

## VEHICLE_TYPE
Value type: string. Nullable: True. Operators: EQ, NE, IN, NOT_IN.
never infer unknown data.

## AC_PREFERENCE
Value type: boolean. Nullable: True. Operators: EQ, NE.
never infer unknown data.

## SLEEPER_PREFERENCE
Value type: boolean. Nullable: True. Operators: EQ, NE.
never infer unknown data.

## AMENITY
Value type: string. Nullable: True. Operators: EQ, NE, IN, NOT_IN.
never infer unknown data.

## ACCESSIBILITY_REQUIREMENT
Value type: string. Nullable: True. Operators: EQ, NE, IN, NOT_IN.
never infer unknown data.

## OPERATOR
Value type: string. Nullable: True. Operators: EQ, NE, IN, NOT_IN.
never infer unknown data.

## SERVICE_NUMBER
Value type: string. Nullable: True. Operators: EQ, NE, IN, NOT_IN.
never infer unknown data.

## ROUTE_NUMBER
Value type: string. Nullable: True. Operators: EQ, NE, IN, NOT_IN.
never infer unknown data.

## VEHICLE_NUMBER
Value type: string. Nullable: True. Operators: EQ, NE, IN, NOT_IN.
never infer unknown data.

## PLATFORM
Value type: string. Nullable: True. Operators: EQ, NE, IN, NOT_IN.
never infer unknown data.

## TRAVEL_DATE
Value type: date. Nullable: True. Operators: EQ, NE, LT, LTE, GT, GTE.
never infer unknown data.

## DATE_RANGE
Value type: structured_range. Nullable: True. Operators: BETWEEN, NOT_BETWEEN.
timezone required when date/time is evaluated.

## TIME
Value type: string. Nullable: True. Operators: EQ, NE, IN, NOT_IN.
timezone required when date/time is evaluated.

## TIME_RANGE
Value type: structured_range. Nullable: True. Operators: BETWEEN, NOT_BETWEEN.
timezone required when date/time is evaluated.

## TIME_PERIOD
Value type: string. Nullable: True. Operators: EQ, NE, IN, NOT_IN.
never infer unknown data.

## TIME_RELATION
Value type: string. Nullable: True. Operators: EQ, NE, IN, NOT_IN.
never infer unknown data.

## PASSENGER_COUNT
Value type: integer. Nullable: True. Operators: EQ, NE, LT, LTE, GT, GTE.
positive integer.

## SEAT_COUNT
Value type: integer. Nullable: True. Operators: EQ, NE, LT, LTE, GT, GTE.
positive integer.

## FARE_AMOUNT
Value type: decimal. Nullable: True. Operators: EQ, NE, LT, LTE, GT, GTE.
never infer unknown data.

## FARE_LIMIT
Value type: decimal. Nullable: True. Operators: EQ, NE, LT, LTE, GT, GTE.
never infer unknown data.

## CURRENCY
Value type: string. Nullable: True. Operators: EQ, NE, IN, NOT_IN.
never infer unknown data.

## CONCESSION_TYPE
Value type: string. Nullable: True. Operators: EQ, NE, IN, NOT_IN.
never infer unknown data.

## RESERVATION_REFERENCE
Value type: string. Nullable: True. Operators: EQ, NE, IN, NOT_IN.
never infer unknown data.

## Slot binding and authorization

ORIGIN_STATION/DESTINATION_STATION map to origin/destination; VIA_STATION to via; TRAVEL_DATE to travel_date; TIME_RELATION plus TIME to departure_after/departure_before/target_time; BUS_CATEGORY to category; AC_PREFERENCE/SLEEPER_PREFERENCE to ac/sleeper. Reservation authorization is a server-side precondition, never a passenger-supplied entity.

Alternative slot sets are OR groups, with all fields in any selected group required. Common kiosk defaults and validated conversation context can fill slots. Clarifications in the intent registry apply only to unresolved inputs; no prompt asks a passenger to assert authorization.

Entity metadata describes the intended contract. It does not mean the existing extractor recognizes every entity or operator; extraction improvements remain separate work.