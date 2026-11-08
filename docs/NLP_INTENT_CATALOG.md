# English RTC intent catalog — Phase 2A

Runtime source of truth: existing nlp_intents and nlp_utterances tables. Versioned JSON-compatible YAML manifests are explicit setup inputs, never runtime replacements for DB edits. Exactly 60 canonical enquiry intents are registered. Legacy rows retain their identifiers and examples, linking to canonical rows by a self foreign key. Dialogue acts are excluded from enquiry lists.

Capability audit: 0 IMPLEMENTED, 41 PARTIAL, 19 UNSUPPORTED. PARTIAL means an existing handler performs some relevant database logic but does not fully satisfy the new intent contract. No new operational capability is implied by registration.

The 300 English examples are agent-authored synthetic taxonomy examples pending human review. They are not the independent Phase 2D evaluation set, and have no train/test split. No model was trained in Phase 2A.

## NEXT_BUS — TIMINGS
Find the earliest eligible departures after the passenger's requested threshold, including later operating dates.

Capability: PARTIAL. Backend code: NEXT_BUS.
Required slots: destination.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: NEXT_BUS:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}]

- When is the next bus to Tirupati?
- Any Nellore departure coming up?
- Which Vijayawada service leaves next?
- I need the soonest bus for Guntur.
- What can I board now for Vizag?

## FIRST_BUS — TIMINGS
Find the earliest departure within one explicitly selected operating day, independent of the current time.

Capability: PARTIAL. Backend code: FIRST_BUS.
Required slots: destination.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: FIRST_BUS:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}]

- What's the first bus tomorrow to Nellore?
- When do Tirupati departures start in the morning?
- Tell me the earliest Guntur service on Monday.
- Which bus starts the day for Hyderabad?
- What is the opening departure to Kavali?

## LAST_BUS — TIMINGS
Find the final eligible departure inside the chosen calendar or operator-defined operating-day bounds.

Capability: PARTIAL. Backend code: LAST_BUS.
Required slots: destination.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: LAST_BUS:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}]

- What time is the last bus to Vizag?
- Can I still catch tonight's final Nellore service?
- When do Guntur buses stop running today?
- Which Tirupati departure closes the schedule?
- I need the final Hyderabad bus for this operating day.

## BUSES_BETWEEN — TIMINGS
List scheduled services permitting boarding at the origin and later alighting at the destination.

Capability: PARTIAL. Backend code: BUSES_BETWEEN.
Required slots: destination.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: BUSES_BETWEEN:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}]

- Show buses from Guntur to Vijayawada.
- List departures between Nellore and Tirupati.
- What services connect Ongole with Kavali?
- Give me today's Hyderabad route options from here.
- Which buses travel from Kurnool to Kadapa?

## DEPARTURES_AFTER — TIMINGS
Find eligible departures following an explicitly supplied lower time bound.

Capability: PARTIAL. Backend code: DEPARTURES_AFTER.
Required slots: destination, departure_after.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: DEPARTURES_AFTER:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}, {"missing_slot": "departure_after", "prompt": "What departure time should I use?"}]

- Any buses to Hyderabad after 9 PM?
- Show Nellore departures later than seven tonight.
- I cannot leave before noon; what goes to Guntur?
- Find Tirupati buses departing after breakfast at eight.
- List services leaving Vijayawada past 18:30.

## DEPARTURES_BEFORE — TIMINGS
Find eligible departures preceding an explicitly supplied upper time bound.

Capability: PARTIAL. Backend code: DEPARTURES_BEFORE.
Required slots: destination, departure_before.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: DEPARTURES_BEFORE:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}, {"missing_slot": "departure_before", "prompt": "What departure time should I use?"}]

- Is there a bus before 6 AM?
- Which Nellore services leave earlier than noon?
- I must depart by five; what can I board?
- Show Guntur departures before 20:00.
- Any Hyderabad bus that starts before sunrise at six?

## BUS_AT_TIME — TIMINGS
Find departures within a documented tolerance window around a specified clock time.

Capability: UNSUPPORTED. Backend code: none.
Required slots: destination, target_time.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: BUS_AT_TIME:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}, {"missing_slot": "target_time", "prompt": "What departure time should I use?"}]

- Is there a Tirupati bus around 7 PM?
- What goes to Nellore near half past eight?
- Does a Guntur service depart at noon?
- Find a Hyderabad departure close to 21:00.
- Is anything scheduled for Kavali at six sharp?

## ARRIVAL_TIME — TIMINGS
Retrieve the scheduled arrival time for the selected service and stop, labelling any operational override separately.

Capability: PARTIAL. Backend code: ARRIVAL_TIME.
Required slots: destination.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: ARRIVAL_TIME:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}]

- When will this bus reach Ongole?
- What is the scheduled arrival at Nellore?
- Tell me when service 3521 reaches Guntur.
- At what time should this route finish in Vizag?
- When does the overnight Hyderabad service reach its terminal?

## JOURNEY_DURATION — TIMINGS
Calculate travel duration between the passenger's valid boarding and alighting stops.

Capability: PARTIAL. Backend code: JOURNEY_DURATION.
Required slots: destination.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: JOURNEY_DURATION:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}]

- How long does it take to reach Kurnool?
- What is the travel time from Guntur to Nellore?
- How many hours is this Tirupati journey?
- Does the Hyderabad ride take the whole night?
- Tell me the scheduled duration to Kavali.

## BUSES_OPERATING_TODAY — TIMINGS
Check which services operate on the station-local current date using calendars and exceptions.

Capability: PARTIAL. Backend code: BUSES_OPERATING_TODAY.
Required slots: destination.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: BUSES_OPERATING_TODAY:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}]

- Are Nellore buses running today?
- Which Guntur services operate this date?
- Is the Tirupati timetable active today?
- Does this weekday-only bus run on Sunday?
- Show today's operating Hyderabad services.

## SERVICE_FREQUENCY — TIMINGS
Describe scheduled departure counts or intervals on a segment within a specified period, without assuming regular headways.

Capability: UNSUPPORTED. Backend code: none.
Required slots: destination.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: SERVICE_FREQUENCY:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}]

- How often do buses run to Guntur?
- What is the gap between Nellore departures?
- Are Hyderabad buses hourly?
- How many Tirupati services run in a day?
- Tell me the service interval on the Kavali route.

## SPECIAL_DAY_SCHEDULE — TIMINGS
Retrieve date-specific extra or changed schedules for a specified holiday, festival or special operating date.

Capability: UNSUPPORTED. Backend code: none.
Required slots: destination.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: SPECIAL_DAY_SCHEDULE:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}]

- Are there additional buses for the festival?
- Any Sankranti specials to Nellore?
- Does Tirupati have a holiday timetable?
- Show extra Hyderabad services this weekend.
- What changes in the Guntur schedule on the festival date?

## AVAILABLE_BUS_TYPES — BUS_TYPES
List the service classifications represented by eligible departures on the requested segment.

Capability: PARTIAL. Backend code: AVAILABLE_BUS_TYPES.
Required slots: destination.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: AVAILABLE_BUS_TYPES:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}]

- What types of buses go to Vizag?
- Which classes are offered for Nellore?
- Do you have multiple categories on the Tirupati route?
- List the bus types serving Hyderabad.
- What service choices are there between Guntur and Ongole?

## AC_BUS_AVAILABILITY — BUS_TYPES
Find services whose assigned vehicle or configuration explicitly supports air conditioning.

Capability: PARTIAL. Backend code: AC_BUS_AVAILABILITY.
Required slots: destination.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: AC_BUS_AVAILABILITY:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}]

- Is there an AC bus to Hyderabad?
- Show air-conditioned departures for Nellore.
- Can I travel to Tirupati with AC tonight?
- Any cooled bus leaving Guntur tomorrow?
- Find an air-conditioned service for Vizag.

## NON_AC_BUS_AVAILABILITY — BUS_TYPES
Find services explicitly known to be non-air-conditioned, excluding unknown configurations.

Capability: PARTIAL. Backend code: NON_AC_AVAILABILITY.
Required slots: destination.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: NON_AC_BUS_AVAILABILITY:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}]

- Show non-AC buses to Nellore.
- I want a Hyderabad bus without air conditioning.
- Are ordinary non-air-conditioned services running to Guntur?
- Only non AC options for Tirupati please.
- Which Vizag buses have no AC?

## SLEEPER_AVAILABILITY — BUS_TYPES
Find services with verified sleeping berths, independently of branded category and seat inventory.

Capability: PARTIAL. Backend code: SLEEPER_BUS_AVAILABILITY.
Required slots: destination.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: SLEEPER_AVAILABILITY:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}]

- Is an AC sleeper available tonight?
- Any sleeping berths on the Hyderabad route?
- Find a sleeper bus for Nellore tomorrow.
- Can I lie down on a Tirupati service?
- Which Vizag departures have sleeper accommodation?

## SEATER_AVAILABILITY — BUS_TYPES
Find services with verified seater accommodation rather than inferring layout from category branding.

Capability: PARTIAL. Backend code: SEATER_BUS_AVAILABILITY.
Required slots: destination.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: SEATER_AVAILABILITY:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}]

- Any seater buses to Tirupati?
- I need a seated bus instead of a sleeper.
- Show Hyderabad services with seats rather than berths.
- Does Nellore have a seater departure tonight?
- Find a Guntur bus where I can travel sitting.

## ELECTRIC_BUS_AVAILABILITY — BUS_TYPES
Find services with an explicitly assigned electric vehicle or configuration.

Capability: PARTIAL. Backend code: ELECTRIC_BUS_AVAILABILITY.
Required slots: destination.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: ELECTRIC_BUS_AVAILABILITY:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}]

- Are electric buses operating on this route?
- Can I take a battery-powered bus to Guntur?
- Show electric services from this station.
- Is the Nellore departure an electric vehicle?
- Which scheduled buses use electric propulsion?

## BUS_AMENITIES — BUS_TYPES
Report verified amenities of the selected assigned vehicle, retaining unknown feature states.

Capability: PARTIAL. Backend code: BUS_AMENITIES.
Required slots: .
Required alternatives: [["trip_id"], ["service_id", "travel_date", "station"]].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: BUS_AMENITIES:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "alternative_slot_group", "prompt": "Please identify the trip/service or the required travel segment.", "alternatives": [["trip_id"], ["service_id", "travel_date", "station"]]}]

- Does this bus have charging ports?
- Is drinking water provided on the Hyderabad bus?
- Can I charge my phone during this journey?
- What facilities are fitted on this vehicle?
- Are reclining seats verified for this service?

## SERVICE_CATEGORY_COMPARISON — BUS_TYPES
Explain recorded differences between two or more service categories without guaranteeing vehicle amenities.

Capability: PARTIAL. Backend code: SERVICE_CATEGORY_COMPARISON.
Required slots: categories.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: SERVICE_CATEGORY_COMPARISON:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "categories", "prompt": "Please specify categories."}]

- What's the difference between Express and Super Luxury?
- Compare Ultra Deluxe with Express.
- How do Indra and Amaravathi categories differ?
- Which features distinguish Pallevelugu from Express?
- Explain the category differences without assuming the assigned vehicle.

## ACCESSIBLE_BUS_AVAILABILITY — BUS_TYPES
Find departures meeting explicitly recorded accessibility requirements.

Capability: UNSUPPORTED. Backend code: none.
Required slots: destination.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: ACCESSIBLE_BUS_AVAILABILITY:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}]

- Is there a wheelchair-accessible bus?
- Which Nellore departure supports wheelchair boarding?
- I need accessible seating for Hyderabad.
- Are mobility-friendly vehicles assigned today?
- Find a service with verified wheelchair support.

## BUS_CAPACITY — BUS_TYPES
Report physical seat and berth capacity of the assigned configuration, not vacant inventory.

Capability: UNSUPPORTED. Backend code: none.
Required slots: .
Required alternatives: [["trip_id"], ["service_id", "travel_date", "station"]].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: BUS_CAPACITY:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "alternative_slot_group", "prompt": "Please identify the trip/service or the required travel segment.", "alternatives": [["trip_id"], ["service_id", "travel_date", "station"]]}]

- How many seats does this bus have?
- What is the assigned vehicle's berth capacity?
- Tell me the total seating layout for this service.
- Is this a forty-seat bus or a larger one?
- How many passengers can the vehicle accommodate, apart from availability?

## DIRECT_BUS — ROUTES
Find a single service allowing the requested journey without a vehicle change.

Capability: PARTIAL. Backend code: DIRECT_BUS_AVAILABILITY.
Required slots: destination.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: DIRECT_BUS:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}]

- Is there a direct bus to Srisailam?
- Can I go to Tirumala without changing buses?
- Show nonstop-transfer options for Nellore.
- Do I need a change to reach Hyderabad?
- Which Vizag service takes me all the way on one bus?

## ROUTE_STOPS — ROUTES
Retrieve the ordered scheduled stopping pattern of the selected route variant or service.

Capability: PARTIAL. Backend code: ROUTE_STOPS.
Required slots: service_id.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: ROUTE_STOPS:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "service_id", "prompt": "Please specify service id."}]

- What are the stops on this route?
- List the stations in travel order for service 3521.
- Where does the Nellore bus call along the way?
- Show the complete stop list for this variant.
- Which intermediate stations are scheduled on this journey?

## BUS_VIA_LOCATION — ROUTES
Check or search for a route passing through a requested via point without asserting a passenger halt.

Capability: PARTIAL. Backend code: BUS_VIA_LOCATION.
Required slots: destination, via.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: BUS_VIA_LOCATION:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}, {"missing_slot": "via", "prompt": "Which location should the route pass through?"}]

- Does this bus go via Ongole?
- Find a Tirupati service travelling through Kavali.
- Which Nellore route passes Guntur?
- Can I choose a Hyderabad service routed via Kurnool?
- Show Vizag options using Rajahmundry as a via point.

## INTERMEDIATE_STOP — ROUTES
Confirm whether a selected service actually calls at a specific intermediate station and allows the relevant passenger action.

Capability: PARTIAL. Backend code: INTERMEDIATE_STOP.
Required slots: service_id, station.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: INTERMEDIATE_STOP:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "service_id", "prompt": "Please specify service id."}, {"missing_slot": "station", "prompt": "Which intermediate stop do you mean?"}]

- Will this bus stop at Kavali?
- Is Ongole a scheduled halt rather than just on the road?
- Does service 3521 actually call at Guntur?
- Will I be allowed to get down at Nellore on this service?
- Is this intermediate station served by the selected departure?

## BOARDING_POINT — ROUTES
Identify locations at which passengers may board the selected service or destination-bound journey.

Capability: PARTIAL. Backend code: BOARDING_POINT.
Required slots: service_id.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: BOARDING_POINT:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "service_id", "prompt": "Please specify service id."}]

- Where can I board the Tirupati bus?
- Can I join this service at Guntur?
- Which stops permit pickup for Hyderabad?
- Where is the boarding location for the selected service?
- May I get on at Kavali instead of the starting terminal?

## ALIGHTING_POINT — ROUTES
Identify permitted drop-off locations or validate a requested alighting station on a selected service.

Capability: PARTIAL. Backend code: ALIGHTING_POINT.
Required slots: service_id.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: ALIGHTING_POINT:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "service_id", "prompt": "Please specify service id."}]

- Can I get down at Rajahmundry?
- Which stations allow drop-off on this bus?
- Is alighting permitted at Ongole?
- Where may I leave the selected service before its terminal?
- Does the Tirupati bus allow passengers off at Nellore?

## CONNECTING_BUSES — ROUTES
Find feasible time-ordered multi-leg journeys respecting transfer windows and stop permissions.

Capability: PARTIAL. Backend code: CONNECTING_BUSES.
Required slots: origin, destination.
Required alternatives: [["travel_date"], ["next_available_policy"]].
Optional slots: travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: CONNECTING_BUSES:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "origin", "prompt": "Please specify origin."}, {"missing_slot": "destination", "prompt": "Please specify destination."}, {"missing_slot": "alternative_slot_group", "prompt": "Please identify the trip/service or the required travel segment.", "alternatives": [["travel_date"], ["next_available_policy"]]}]

- Where should I change buses for Annavaram?
- Find a connection from Guntur to Srisailam.
- Can I transfer at Vijayawada for Nellore?
- Which onward bus can I catch after arriving at Kurnool?
- Plan a journey to Tirumala with at most two changes.

## ALTERNATIVE_ROUTES — ROUTES
Find different feasible paths or transfer patterns for the same journey, relative to an optional selected route.

Capability: PARTIAL. Backend code: ALTERNATIVE_ROUTES.
Required slots: destination.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: ALTERNATIVE_ROUTES:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}]

- Is there another way to reach Vizag?
- What route can I use if the direct Nellore bus is unavailable?
- Show a different path to Hyderabad.
- Are there alternative connections through another station?
- Can I reach Tirupati by a route other than the usual one?

## ROUTE_DISTANCE — ROUTES
Retrieve sourced cumulative or segment distance along the applicable route variant.

Capability: UNSUPPORTED. Backend code: none.
Required slots: destination.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: ROUTE_DISTANCE:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}]

- How many kilometres is it to Nellore?
- What distance does this route cover?
- Tell me the stop-to-stop distance from Guntur to Ongole.
- How far is Hyderabad along this bus variant?
- What is the cumulative route distance at Kavali?

## DESTINATION_REACHABILITY — ROUTES
Determine whether any feasible direct or connecting bus itinerary reaches the requested destination in the search period.

Capability: UNSUPPORTED. Backend code: none.
Required slots: destination.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: DESTINATION_REACHABILITY:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}]

- Can I reach Tirumala from here by bus?
- Is there any bus journey to Srisailam, including connections?
- Does the network serve Annavaram from this station?
- Can you find a way to get to Hyderabad at all?
- Is Nellore reachable today even if I must change?

## GET_FARE — FARES_AND_BOOKINGS
Retrieve an applicable date-effective fare for the actual boarding and alighting segment and selected service or category.

Capability: PARTIAL. Backend code: TICKET_FARE.
Required slots: origin.
Required alternatives: [["destination"], ["selected_service_id", "boarding_station", "alighting_station"]].
Optional slots: travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: GET_FARE:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "origin", "prompt": "Please specify origin."}, {"missing_slot": "alternative_slot_group", "prompt": "Please identify the trip/service or the required travel segment.", "alternatives": [["destination"], ["selected_service_id", "boarding_station", "alighting_station"]]}]

- How much is the ticket to Nellore?
- What will Guntur to Ongole cost on this service?
- Tell me the adult fare for the selected Tirupati bus.
- How much ticket to Hyderabad from here?
- What price applies when boarding at Kavali?

## CHEAPEST_BUS — FARES_AND_BOOKINGS
Rank eligible services by known applicable segment fare; missing prices are never zero.

Capability: PARTIAL. Backend code: CHEAPEST_BUS.
Required slots: destination.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: CHEAPEST_BUS:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}]

- What's the cheapest bus to Hyderabad?
- Find the lowest known fare to Nellore.
- Which Guntur departure costs the least?
- I want the minimum ticket price among available Tirupati services.
- Show the most economical bus for this same boarding segment.

## FASTEST_BUS — FARES_AND_BOOKINGS
Rank eligible services by elapsed journey duration for the same requested segment.

Capability: PARTIAL. Backend code: FASTEST_BUS.
Required slots: destination.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: FASTEST_BUS:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}]

- Which bus reaches Vizag fastest?
- Find the shortest scheduled journey to Nellore.
- What service gets me to Hyderabad in the least time?
- Which Tirupati departure has the quickest ride?
- Compare travel durations and show the fastest Guntur option.

## FARE_COMPARISON — FARES_AND_BOOKINGS
Compare applicable prices for multiple services or categories on the same boarding segment and travel date.

Capability: PARTIAL. Backend code: FARE_COMPARISON.
Required slots: origin.
Required alternatives: [["destination"], ["selected_service_id", "boarding_station", "alighting_station"]].
Optional slots: travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: FARE_COMPARISON:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "origin", "prompt": "Please specify origin."}, {"missing_slot": "alternative_slot_group", "prompt": "Please identify the trip/service or the required travel segment.", "alternatives": [["destination"], ["selected_service_id", "boarding_station", "alighting_station"]]}]

- Compare Express and Super Luxury fares.
- How much extra does the AC service cost for the same segment?
- Show ticket prices side by side for these buses.
- Is the sleeper more expensive than the seater to Hyderabad?
- Compare Nellore fares for tomorrow's matching departures.

## SEAT_AVAILABILITY — FARES_AND_BOOKINGS
Report fresh segment-specific inventory for a dated trip and requested seat count, distinguishing unknown and stale states.

Capability: PARTIAL. Backend code: SEAT_AVAILABILITY.
Required slots: .
Required alternatives: [["trip_id"], ["service_id", "travel_date", "station"]].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: SEAT_AVAILABILITY:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "alternative_slot_group", "prompt": "Please identify the trip/service or the required travel segment.", "alternatives": [["trip_id"], ["service_id", "travel_date", "station"]]}]

- Are two seats available tonight?
- How many vacant seats are currently known on this trip?
- Is there one sleeper berth free from Guntur to Nellore?
- Can three people travel on the selected bus?
- Is the latest local inventory fresh enough to confirm vacancies?

## RESERVATION_SUPPORTED — FARES_AND_BOOKINGS
Report whether reservations are supported for the selected service, separately from current seat availability.

Capability: PARTIAL. Backend code: RESERVATION_SUPPORTED.
Required slots: service_id.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: RESERVATION_SUPPORTED:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "service_id", "prompt": "Please specify service id."}]

- Can I reserve a seat on this bus?
- Is this service reservation-enabled?
- Does the Nellore route accept advance reservations?
- Can seats be reserved on Pallevelugu here?
- Is booking supported for the selected trip category?

## BOOKING_OPTIONS — FARES_AND_BOOKINGS
Describe locally recorded approved ticket booking channels and instructions without executing a purchase.

Capability: UNSUPPORTED. Backend code: none.
Required slots: operator.
Required alternatives: [].
Optional slots: origin, travel_date, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: BOOKING_OPTIONS:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "operator", "prompt": "Please specify operator."}]

- Where can I book a ticket?
- Which local booking counter handles Hyderabad services?
- What reservation channels does this operator provide?
- How do I buy a ticket for the selected bus?
- Is there an approved booking contact for this service?

## BOOKING_STATUS — FARES_AND_BOOKINGS
Read status of an existing booking only when an authorized local record is available; otherwise report unsupported or unavailable.

Capability: UNSUPPORTED. Backend code: none.
Required slots: reservation_reference.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: BOOKING_STATUS:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "reservation_reference", "prompt": "Which booking reference do you mean? Local status lookup is unavailable unless an authorized record exists."}]

- Can you check whether my booking is confirmed?
- Is reservation reference ABC123 available locally?
- Does the authorized local record show my ticket as confirmed?
- Can this kiosk look up my existing booking reference?
- Is my reservation status known without contacting an external system?

## CANCELLATION_POLICY — FARES_AND_BOOKINGS
Explain locally stored passenger ticket cancellation terms, independently of operational trip cancellation.

Capability: UNSUPPORTED. Backend code: none.
Required slots: operator.
Required alternatives: [].
Optional slots: origin, travel_date, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: CANCELLATION_POLICY:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "operator", "prompt": "Please specify operator."}]

- What are the cancellation charges?
- How late can I cancel this ticket under operator rules?
- Which policy applies if a passenger cancels a booking?
- Is there a penalty for cancelling a reserved seat?
- Where can I read this service's ticket cancellation terms?

## REFUND_POLICY — FARES_AND_BOOKINGS
Explain applicable recorded refund rules or a supported calculation; never infer a refund without required policy data.

Capability: UNSUPPORTED. Backend code: none.
Required slots: operator.
Required alternatives: [].
Optional slots: origin, travel_date, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: REFUND_POLICY:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "operator", "prompt": "Please specify operator."}]

- How much refund will I receive?
- What refund rules apply to this fare class?
- Is the refundable amount known for a cancelled ticket?
- Does the operator provide a refund policy locally?
- What deductions apply before returning the ticket amount?

## CONCESSION_ENQUIRY — FARES_AND_BOOKINGS
Explain date-effective concession schemes and explicit eligibility requirements without assuming passenger qualification.

Capability: PARTIAL. Backend code: CONCESSION_ELIGIBILITY.
Required slots: operator.
Required alternatives: [].
Optional slots: origin, travel_date, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: CONCESSION_ENQUIRY:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "operator", "prompt": "Please specify operator."}]

- Is there a senior citizen concession?
- What eligibility is required for a child fare?
- Are any operator travel schemes applicable on this route?
- Where can I check pass-holder discount conditions?
- Does this concession require proof rather than being automatically granted?

## LUGGAGE_RULES — FARES_AND_BOOKINGS
Describe recorded baggage allowances, restrictions and applicable published luggage charges.

Capability: UNSUPPORTED. Backend code: none.
Required slots: operator.
Required alternatives: [].
Optional slots: origin, travel_date, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: LUGGAGE_RULES:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "operator", "prompt": "Please specify operator."}]

- Is there an extra luggage charge?
- How much baggage is allowed on this service?
- What are the operator's luggage limits?
- Can I carry a large suitcase on the Nellore bus?
- Are additional parcels charged under a published local rule?

## LIVE_BUS_STATUS — OPERATIONS
Report the freshest authoritative operational state or location, distinguishing scheduled-only, stale and unknown data.

Capability: PARTIAL. Backend code: BUS_LIVE_STATUS.
Required slots: .
Required alternatives: [["trip_id"], ["service_id", "travel_date", "station"]].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: True. Template key: LIVE_BUS_STATUS:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "alternative_slot_group", "prompt": "Please identify the trip/service or the required travel segment.", "alternatives": [["trip_id"], ["service_id", "travel_date", "station"]]}]

- Where is the Hyderabad bus right now?
- Do you have a verified current location for this trip?
- Show the freshest operational status of service 3521.
- Is this bus actually running or only scheduled?
- What live information is available for the selected vehicle?

## BUS_DELAY — OPERATIONS
Report a verified delay duration or recorded reason for the selected dated trip and affected stop.

Capability: PARTIAL. Backend code: BUS_DELAY.
Required slots: .
Required alternatives: [["trip_id"], ["service_id", "travel_date", "station"]].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: True. Template key: BUS_DELAY:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "alternative_slot_group", "prompt": "Please identify the trip/service or the required travel segment.", "alternatives": [["trip_id"], ["service_id", "travel_date", "station"]]}]

- Why is the Tirupati bus late?
- How many minutes is this departure delayed?
- Has a verified delay been recorded at Ongole?
- Is there a reported reason for the late Nellore service?
- What is the latest confirmed delay update?

## BUS_CANCELLATION — OPERATIONS
Confirm operational cancellation of a specific service occurrence, not a passenger's ticket cancellation request.

Capability: PARTIAL. Backend code: BUS_CANCELLATION.
Required slots: .
Required alternatives: [["trip_id"], ["service_id", "travel_date", "station"]].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: True. Template key: BUS_CANCELLATION:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "alternative_slot_group", "prompt": "Please identify the trip/service or the required travel segment.", "alternatives": [["trip_id"], ["service_id", "travel_date", "station"]]}]

- Has the 8 PM bus been cancelled?
- Is today's selected Tirupati trip removed from operation?
- Did the operator cancel the Hyderabad departure on this date?
- Does a local record confirm this service is cancelled?
- Which scheduled Nellore trip is not running because of cancellation?

## BUS_PLATFORM — OPERATIONS
Report the currently valid confirmed station bay assignment for a specific dated trip.

Capability: PARTIAL. Backend code: BUS_PLATFORM.
Required slots: .
Required alternatives: [["trip_id"], ["service_id", "travel_date", "station"]].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: True. Template key: BUS_PLATFORM:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "alternative_slot_group", "prompt": "Please identify the trip/service or the required travel segment.", "alternatives": [["trip_id"], ["service_id", "travel_date", "station"]]}]

- Which platform is the Nellore bus on?
- Where is the assigned bay for this trip?
- Tell me the confirmed boarding platform at Vijayawada.
- What platform should I stand at for service 3521?
- Is the bay assignment known for this service and date?

## ESTIMATED_ARRIVAL — OPERATIONS
Report a fresh verified operational arrival estimate; a scheduled arrival alone does not satisfy this intent.

Capability: UNSUPPORTED. Backend code: none.
Required slots: .
Required alternatives: [["trip_id"], ["service_id", "travel_date", "station"]].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: True. Template key: ESTIMATED_ARRIVAL:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "alternative_slot_group", "prompt": "Please identify the trip/service or the required travel segment.", "alternatives": [["trip_id"], ["service_id", "travel_date", "station"]]}]

- When is the bus expected to arrive here?
- Is there a verified revised arrival estimate at Ongole?
- What is the latest predicted arrival rather than the timetable time?
- Has the arrival estimate for Nellore changed?
- Can you show the fresh operational ETA for this trip?

## BUS_DEPARTED_STATUS — OPERATIONS
Confirm departure only from an authoritative actual-departure event at the specified stop.

Capability: UNSUPPORTED. Backend code: none.
Required slots: .
Required alternatives: [["trip_id"], ["service_id", "travel_date", "station"]].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: True. Template key: BUS_DEPARTED_STATUS:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "alternative_slot_group", "prompt": "Please identify the trip/service or the required travel segment.", "alternatives": [["trip_id"], ["service_id", "travel_date", "station"]]}]

- Has the Vizag bus already left?
- Is there an actual departure event from this station?
- Did service 3521 leave Ongole yet?
- Can you confirm the bus departed rather than assume from its schedule?
- Is the selected trip still waiting or recorded as departed?

## BUS_ARRIVED_STATUS — OPERATIONS
Confirm arrival only from an authoritative actual-arrival event at the specified stop.

Capability: UNSUPPORTED. Backend code: none.
Required slots: .
Required alternatives: [["trip_id"], ["service_id", "travel_date", "station"]].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: True. Template key: BUS_ARRIVED_STATUS:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "alternative_slot_group", "prompt": "Please identify the trip/service or the required travel segment.", "alternatives": [["trip_id"], ["service_id", "travel_date", "station"]]}]

- Has the Guntur bus arrived?
- Is there an actual arrival event at this station?
- Did the selected bus reach Nellore already?
- Can you confirm arrival using a local operational record?
- Does the latest verified event say the bus has arrived?

## SERVICE_DISRUPTION — OPERATIONS
Report verified diversions, suspensions or other incidents effective for the requested service or period.

Capability: PARTIAL. Backend code: SERVICE_DISRUPTION.
Required slots: destination.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: True. Template key: SERVICE_DISRUPTION:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "destination", "prompt": "Please specify destination."}]

- Are services affected by road closures?
- Has a diversion been announced for this route?
- What operational alert affects today's Hyderabad journey?
- Is the Nellore service disrupted by a local incident?
- Are there verified temporary restrictions on this departure?

## PLATFORM_CHANGE — OPERATIONS
Confirm a platform reassignment by examining assignment history for the same trip and station.

Capability: UNSUPPORTED. Backend code: none.
Required slots: .
Required alternatives: [["trip_id"], ["service_id", "travel_date", "station"]].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: True. Template key: PLATFORM_CHANGE:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "alternative_slot_group", "prompt": "Please identify the trip/service or the required travel segment.", "alternatives": [["trip_id"], ["service_id", "travel_date", "station"]]}]

- Has the bus moved to another platform?
- Was a new bay assigned after the earlier announcement?
- Which platform replaced the original Nellore assignment?
- Is there a confirmed platform reassignment for this trip?
- Has service 3521 changed its boarding bay today?

## SERVICE_NUMBER_LOOKUP — OPERATIONS
Resolve a service identifier within operator and validity scope, requesting clarification if multiple records match.

Capability: PARTIAL. Backend code: SERVICE_NUMBER_LOOKUP.
Required slots: service_number.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: SERVICE_NUMBER_LOOKUP:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "service_number", "prompt": "Please specify service number."}]

- Where is service number 3521 going?
- Which operator runs service 8120?
- Show the route for this service identifier.
- Can you identify the bus using its service number?
- Are there multiple local matches for service 1234?

## STATION_FACILITIES — STATION_ASSISTANCE
Report locally recorded passenger facilities and their verification or availability state at a station.

Capability: PARTIAL. Backend code: STATION_FACILITIES.
Required slots: station.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: STATION_FACILITIES:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "station", "prompt": "Please specify station."}]

- Where is the waiting hall?
- Does this bus stand have drinking water?
- Are toilets available at the station?
- What passenger facilities are recorded here?
- Is an accessible waiting area listed at this terminal?

## STATION_HELPDESK — STATION_ASSISTANCE
Provide a recorded station enquiry/helpdesk contact, location or opening information.

Capability: PARTIAL. Backend code: STATION_HELPDESK.
Required slots: station.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: STATION_HELPDESK:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "station", "prompt": "Please specify station."}]

- Where is the enquiry counter?
- How do I contact the station helpdesk?
- Is the information desk open at this bus stand?
- Which counter can help with a bus enquiry?
- Give me the recorded station assistance contact.

## LOST_PROPERTY — STATION_ASSISTANCE
Provide the locally recorded lost-property reporting contact or procedure without claiming an item was found.

Capability: PARTIAL. Backend code: LOST_PROPERTY_CONTACT.
Required slots: station.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: LOST_PROPERTY:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "station", "prompt": "Please specify station."}]

- I forgot my bag on the bus.
- Where should I report a lost suitcase?
- Is there a lost-property contact at this station?
- Who handles items left on an RTC vehicle?
- How can I ask about belongings found on the Nellore bus?

## OPERATOR_CONTACT — STATION_ASSISTANCE
Provide published local operator or depot contact information relevant to the passenger's service.

Capability: UNSUPPORTED. Backend code: none.
Required slots: operator.
Required alternatives: [].
Optional slots: origin, travel_date, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: OPERATOR_CONTACT:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "operator", "prompt": "Please specify operator."}]

- What's the depot contact number?
- How do I reach this transport operator?
- Is a local operator enquiry contact recorded?
- Give me the depot office contact for this service.
- Where can I find the corporation's published telephone details?

## STATION_NAVIGATION — STATION_ASSISTANCE
Provide recorded within-station directions or zone information without inventing an indoor route.

Capability: UNSUPPORTED. Backend code: none.
Required slots: station.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: STATION_NAVIGATION:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "station", "prompt": "Please specify station."}]

- How do I get to platform 6?
- Where is bay ten inside this station?
- Which zone contains the boarding platform?
- Is there a recorded accessible path to the waiting area?
- How can I find the local bus bay from the enquiry counter?

## COMPLAINT_GUIDANCE — STATION_ASSISTANCE
Explain the locally recorded complaint or grievance channel and reporting instructions.

Capability: UNSUPPORTED. Backend code: none.
Required slots: station.
Required alternatives: [].
Optional slots: origin, travel_date, operator, category, ac, sleeper, after, before, via, maximum_transfers, minimum_transfer, fare_limit, passenger_count, concession_scheme, selected_service_id, selected_trip_id.
Live data required: False. Template key: COMPLAINT_GUIDANCE:{status}:{language} (intent-specific template is not yet installed).
Clarifications: [{"missing_slot": "station", "prompt": "Please specify station."}]

- Where can I report a conductor complaint?
- What is the operator's complaint process?
- Is there a recorded grievance contact?
- How do I submit feedback about this bus service?
- Which station counter handles passenger complaints?

## Compatibility aliases

- BUS_LIVE_STATUS → LIVE_BUS_STATUS
- CONCESSION_ELIGIBILITY → CONCESSION_ENQUIRY
- DIRECT_BUS_AVAILABILITY → DIRECT_BUS
- GET_ARRIVAL → ARRIVAL_TIME
- GET_BOOKING_OPTIONS → BOOKING_OPTIONS
- GET_BUS_TYPES → AVAILABLE_BUS_TYPES
- GET_CANCELLATION → BUS_CANCELLATION
- GET_CHEAPEST_SERVICE → CHEAPEST_BUS
- GET_CONCESSIONS → CONCESSION_ENQUIRY
- GET_CONNECTING_BUSES → CONNECTING_BUSES
- GET_DELAY → BUS_DELAY
- GET_DURATION → JOURNEY_DURATION
- GET_FACILITIES → STATION_FACILITIES
- GET_FASTEST_SERVICE → FASTEST_BUS
- GET_LUGGAGE_RULES → LUGGAGE_RULES
- GET_PLATFORM → BUS_PLATFORM
- GET_ROUTE → ROUTE_STOPS
- GET_SEAT_AVAILABILITY → SEAT_AVAILABILITY
- GET_STATION_FACILITIES → STATION_FACILITIES
- GET_STOPS → ROUTE_STOPS
- LOST_PROPERTY_CONTACT → LOST_PROPERTY
- NON_AC_AVAILABILITY → NON_AC_BUS_AVAILABILITY
- SEATER_BUS_AVAILABILITY → SEATER_AVAILABILITY
- SLEEPER_BUS_AVAILABILITY → SLEEPER_AVAILABILITY
- TICKET_FARE → GET_FARE

Unmapped legacy/internal records are preserved outside the canonical taxonomy. Their removal or forced consolidation would risk merging distinct meanings. Existing specialized HTTP routes retain their behavior. Unified engine requests resolve supported canonical codes to existing backend codes and return canonical intent names. Unsupported registered intents are stopped before execution.

## Operations

`python -m alembic upgrade head` then `python -m app.taxonomy_seed` with PYTHONPATH=backend registers defaults idempotently. Normal reseeding preserves existing metadata edits. `--refresh` explicitly replaces canonical metadata from the approved manifest and should only be used for an intentional bulk taxonomy update. The development DB was explicitly refreshed once after finalizing definitions.

GET /api/v1/nlp/intents supports limit/offset; GET /api/v1/nlp/intents/{code} accepts canonical or mapped legacy codes; GET /api/v1/nlp/entities lists the 32 structured entity specifications. The seed uses existing NLP models plus additive migration 0010; no duplicate service or taxonomy tables were created.
