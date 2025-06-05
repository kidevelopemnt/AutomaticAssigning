from automatic_assigning.models import AssignmentObject, AssignmentSlot, AssignmentGroup, Event, EventGroup, EventType
from datetime import timedelta


class FieldGroup(EventGroup):
    def __init__(self, name):
        super().__init__(name, try_keep_assignments_in_group=True)


class AgeGroup(EventType):
    def __init__(self, name, duration: timedelta):
        super().__init__(name, duration)


class Referee(AssignmentObject):
    def __init__(self, name):
        self.name = name
        super().__init__([], True)


class Game(Event):
    def __init__(self, event_id, name, age_group, start_time, field):
        super().__init__(event_id, name, age_group, start_time, groups=[field])

        center_slot = AssignmentSlot("Center Referee", Referee)
        assistant_slot = AssignmentSlot("Assistant Referee", Referee, 2)
        self.referees = AssignmentGroup(center_slot, assistant_slot)