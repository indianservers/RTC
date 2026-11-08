import type { Conversation } from "./api";

type Action = { label: string; query: string };

export function followUpActions(response?: Conversation): Action[] {
  if (response?.follow_up_suggestions)
    return response.follow_up_suggestions.map((action) => ({
      label: action.label,
      query: action.text,
    }));
  if (
    !response ||
    response.requires_clarification ||
    !response.context.destination
  )
    return [];

  const context = response.context;

  const intent = response.intents[0];

  const actions: Action[] = [];

  const add = (label: string, query: string) => actions.push({ label, query });

  if (response.state === "NO_RESULTS") {
    if (
      context.filters?.ac !== undefined ||
      context.filters?.sleeper !== undefined ||
      context.filters?.category
    )
      add("Clear bus category filters", "Any bus type");

    if (context.filters?.max_fare)
      add("Remove fare ceiling", "Remove fare limit");

    add("Show connecting buses", "Connecting buses");

    add("What about tomorrow?", "Tomorrow");

    return actions;
  }

  if (intent === "CONNECTING_BUSES" || context.journey_mode) {
    add("Fastest journey", "Fastest bus");

    add("Cheapest journey", "Cheapest bus");

    add("Fewer transfers", "Fewest transfers");

    if (context.service_id) add("View intermediate stops", "Route stops");
  } else if (["GET_FARE", "FARE_COMPARISON", "CHEAPEST_BUS"].includes(intent)) {
    add("Show cheaper options", "Cheapest bus");

    add("Next available bus", "Next bus");
  } else if (["BUS_DELAY", "BUS_CANCELLATION"].includes(intent)) {
    add("Show alternatives", "Next bus");

    if (context.service_id) add("Which platform?", "Which platform?");
  } else {
    add("What is the fare?", "What is the fare?");

    if (context.filters?.ac !== true) add("Show AC buses", "Only AC");

    add("Show cheaper options", "Cheapest bus");
  }

  if (context.service_id) {
    add("View intermediate stops", "Route stops");

    add("Which platform?", "Which platform?");
  }

  add("What about tomorrow?", "Tomorrow");

  add("Show connecting buses", "Connecting buses");

  return actions
    .filter((a, i) => actions.findIndex((b) => b.query === a.query) === i)
    .slice(0, 7);
}
