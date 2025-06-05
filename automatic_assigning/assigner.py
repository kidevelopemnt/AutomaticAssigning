from typing import Type

from .models import AssignmentObject, AssignmentRule, AssignmentSlot, AssignmentGroup, Event


class Assigner:
    def __init__(self):
        pass

    def assign_events(self, event_class: Type[Event], events: list[Event] = None, exclude_slots: list[AssignmentSlot | AssignmentGroup] = None):
        if events is None:
            events = event_class.objects.all()

        scheduled_count = {}  # slot: amount
        for event in events:
            for group in event.assignment_groups:
                self.assign_group(event, group, scheduled_count)

        for slot, amount in scheduled_count:
            print(f"Scheduled {amount} {slot.position.name}s")
            # records.save_flights_to_db()

    def assign_group(self, event: Event, assignment_group: AssignmentGroup, scheduled_count: dict):
        event_type = type(event)

        stay_in_group = None  # TODO: Allow multiple
        for group in event.groups:
            if group.try_keep_assignments_in_group:
                stay_in_group = group

        if stay_in_group:
            event_group_index = stay_in_group.get_events(event_type).index(event)
            if event_group_index > 0:  # There was an event before this in the same group
                # Try to copy over assignments for the last slot
                prev: AssignmentGroup = stay_in_group.get_events(event_type)[event_group_index - 1].get_assignment_group(assignment_group)
                for slot in prev.slots:
                    if slot.assigned_objects:
                        this_slot: AssignmentSlot = assignment_group.slots[assignment_group.slots_names.index(slot.name)]
                        for obj in slot.assigned_objects:
                            if obj.can_be_assigned(event, this_slot, assignment_group):
                                this_slot.assigned_objects.append(obj)
                                obj.events.append(event)

        needed_slots = assignment_group.get_needed_assignments()
        slot: AssignmentSlot
        for slot in needed_slots:
            assigned = False

            for obj in slot.object_to_assign.objects.all():
                if obj.can_be_assigned(event, slot, assignment_group):
                    slot.assigned_objects.append(obj)
                    obj.events.append(event)
                    assigned = True
                    break

            if not assigned:
                print(f"[ERR] Could not assign {slot.name} for event {event.event_id}")

        # Increment counter
        return True
