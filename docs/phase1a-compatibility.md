# Phase 1A compatibility register

PHASE 1A INCOMPLETE. Existing column names remain canonical for API compatibility. Newly added fields are nullable until validated backfills can be completed.

## A1: states
Present columns: name_native, country_code, timezone, code, name, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## A2: districts
Present columns: code, name_native, state_id, name, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## A3: cities
Present columns: state_id, name_native, district_id, name, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## A4: transport_operators
Present columns: short_name, headquarters_city_id, website, default_timezone, code, name, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## A5: operator_service_areas
Present columns: operator_id, state_id, service_area_type, effective_from, effective_to, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## A6: operator_divisions
Present columns: operator_id, code, name, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## A7: depots
Present columns: operator_id, name, address, division_id, city_id, code, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## A8: bus_stations
Present columns: city_id, name_native, station_type, address, code, name, timezone, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## A9: station_bays
Present columns: bay_name, floor_or_zone, accessible, station_id, code, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## A10: place_aliases
Status: missing exact table; existing related tables may cover part of the concept. No duplicate replacement created.

## B1: bus_service_categories
Present columns: code, name_native, description, service_tier, fare_class_code, operator_id, name, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## B2: bus_type_aliases
Present columns: category_id, name, language, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## B3: vehicle_types
Present columns: name, ac, sleeper, fuel, configuration, wheelchair, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## B4: vehicles
Present columns: operator_id, type_id, layout_id, registration, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## B5: amenities
Present columns: code, name_en, name_native, description, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## B6: vehicle_amenities
Present columns: vehicle_id, name, available, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## B7: vehicle_seats
Present columns: layout_id, label, accessible, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## C1: routes
Present columns: operator_id, origin_station_id, destination_station_id, route_name, code, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## C2: route_variants
Present columns: route_id, name, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## C3: route_stops
Present columns: route_id, station_id, sequence, offset_minutes, distance_km, boarding, alighting, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## C4: route_aliases
Present columns: route_id, name, language, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## C5: route_distance_sources
Status: missing exact table; existing related tables may cover part of the concept. No duplicate replacement created.

## D1: services
Present columns: route_variant_id, reservation_supported, operator_id, category_id, route_id, number, departure_minutes, weekdays, valid_from, valid_to, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## D2: service_calendars
Present columns: service_id, valid_from, valid_to, weekdays, departure_minutes, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## D3: service_calendar_exceptions
Present columns: service_id, service_date, operates, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## D4: service_stop_times
Present columns: service_id, stop_id, arrival_offset, departure_offset, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## D5: trips
Present columns: vehicle_id, planned_departure_at, source_id, service_id, service_date, status, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## D6: trip_stop_times
Present columns: trip_id, stop_id, estimated_departure, actual_departure, estimated_arrival, actual_arrival, id, dataset_source, active, source_id, recorded_at, effective_at, expires_at, verified
Status: partial compatibility; compare field names and constraints with original request.

## D7: trip_status_events
Status: missing exact table; existing related tables may cover part of the concept. No duplicate replacement created.

## D8: service_disruptions
Present columns: service_id, description, id, dataset_source, active, source_id, recorded_at, effective_at, expires_at, verified
Status: partial compatibility; compare field names and constraints with original request.

## E1: fare_tables
Present columns: operator_id, category_id, name, fare_class, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## E2: fare_rules
Present columns: table_id, per_km, minimum, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## E3: trip_fare_overrides
Present columns: trip_id, origin_id, destination_id, amount, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## E4: concession_schemes
Status: missing exact table; existing related tables may cover part of the concept. No duplicate replacement created.

## E5: concession_applicability
Status: missing exact table; existing related tables may cover part of the concept. No duplicate replacement created.

## E6: fare_history
Present columns: fare_id, old_amount, new_amount, recorded_at, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## F1: trip_inventory
Present columns: trip_id, reservation_enabled, capacity, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## F2: seat_availability_snapshots
Present columns: origin_station_id, destination_station_id, seat_class, trip_id, available, id, dataset_source, active, source_id, recorded_at, effective_at, expires_at, verified
Status: partial compatibility; compare field names and constraints with original request.

## F3: reservation_channels
Present columns: operator_id, name, instructions, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## F4: reservation_enquiry_references
Status: missing exact table; existing related tables may cover part of the concept. No duplicate replacement created.

## G1: vehicle_locations
Present columns: trip_id, vehicle_id, latitude, longitude, id, dataset_source, active, source_id, recorded_at, effective_at, expires_at, verified
Status: partial compatibility; compare field names and constraints with original request.

## G2: trip_delay_events
Present columns: trip_id, station_id, delay_minutes, id, dataset_source, active, source_id, recorded_at, effective_at, expires_at, verified
Status: partial compatibility; compare field names and constraints with original request.

## G3: platform_assignments
Present columns: trip_id, bay_id, id, dataset_source, active, source_id, recorded_at, effective_at, expires_at, verified
Status: partial compatibility; compare field names and constraints with original request.

## G4: operational_alerts
Present columns: trip_id, station_id, message, id, dataset_source, active, source_id, recorded_at, effective_at, expires_at, verified
Status: partial compatibility; compare field names and constraints with original request.

## G5: station_facilities
Present columns: facility_type, accessible, is_available, station_id, name, description, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## G6: station_contact_points
Present columns: station_id, contact_type, label, contact_value, opening_hours, last_verified_at, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## H1: nlp_intents
Present columns: display_name, required_slots_json, optional_slots_json, code, description, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## H2: nlp_utterances
Present columns: normalized_text, dataset_split, source_type, quality_status, intent_id, language, text, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## H3: nlp_entity_types
Present columns: code, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## H4: nlp_entity_annotations
Present columns: utterance_id, entity_type_id, start_offset, end_offset, surface_text, canonical_value, review_status, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## H5: nlp_entity_aliases
Present columns: type_id, entity_id, language, text, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## H6: nlp_response_templates
Present columns: response_status, required_placeholders_json, intent_id, language, text, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## H7: conversation_sessions
Present columns: station_id, operator_id, language, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## H8: conversation_messages
Present columns: sequence_number, detected_intent_id, session_id, role, text, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## H9: conversation_context
Present columns: origin_station_id, destination_station_id, travel_date, passenger_count, last_trip_id, session_id, values, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## H10: enquiry_execution_logs
Present columns: session_id, intent_id, parameters, result_count, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## I1: data_sources
Present columns: operator_id, source_type, trust_level, is_official, is_demo, code, name, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## I2: data_import_batches
Present columns: resource, digest, row_count, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## I3: data_quality_issues
Present columns: source_id, batch_id, description, resolved, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## I4: admin_users
Present columns: username, password_hash, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## I5: admin_roles
Present columns: role_code, description, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## I6: admin_user_roles
Present columns: user_id, role_id, operator_id, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.

## I7: audit_logs
Present columns: actor, entity_type, entity_id, operation, recorded_at, id, dataset_source, active
Status: partial compatibility; compare field names and constraints with original request.
