/**
 * Creates an event forwarder function that dispatches events with the same type and detail.
 * Useful for components that need to forward events from child components to their parents.
 *
 * @param {Function} dispatch - The dispatch function from createEventDispatcher()
 * @returns {Function} A function that forwards events by dispatching them with the original type and detail
 *
 * @example
 * import { createEventDispatcher } from 'svelte'
 * import { createEventForwarder } from '../services/utils/eventUtils'
 *
 * const dispatch = createEventDispatcher()
 * const forwardEvent = createEventForwarder(dispatch)
 *
 * // Use in template:
 * <ChildComponent on:someEvent={forwardEvent} />
 */
export function createEventForwarder(dispatch) {
  return function forwardEvent(event) {
    dispatch(event.type, event.detail)
  }
}
