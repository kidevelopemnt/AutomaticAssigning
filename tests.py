from datetime import timedelta, datetime
from unittest import TestCase
from automatic_assigning.assigner import Assigner
from automatic_assigning.models import Event, EventType, AssignmentGroup, AssignmentSlot, \
    AssignmentObject, EventGroup


class FieldGroup(EventGroup):
    def __init__(self, name):
        super().__init__(name, try_keep_assignments_in_group=True)


class AgeGroup(EventGroup):
    def __init__(self, name):
        super().__init__(name, try_keep_assignments_in_group=False)


class Referee(AssignmentObject):
    def __init__(self, name):
        self.name = name
        super().__init__()


class Game(Event):
    def __init__(self, event_id, name, start_time, field, age_group):
        super().__init__(event_id, name, EventType("Test Event", timedelta(hours=1)), start_time, groups=[field, age_group])

        center_slot = AssignmentSlot("Center Referee", Referee)
        assistant_slot = AssignmentSlot("Assistant Referee", Referee, 2)
        self.referees = AssignmentGroup(center_slot, assistant_slot)


class AssignerTest(TestCase):
    def setUp(self):
        field1 = FieldGroup("Field 1")
        field2 = FieldGroup("Field 2")
        u9_10 = AgeGroup("U9/10")
        u11_12 = AgeGroup("U11/12")

        game1 = Game("GAME1", "Game #1", datetime(2025, 6, 9, 8, 0), field1, u9_10)   # 06/09/25 08:00 AM
        game2 = Game("GAME2", "Game #2", datetime(2025, 6, 9, 10, 0), field1, u9_10)  # 06/09/25 10:00 AM

    def test_assigning(self):
        assigner = Assigner()
        assigner.assign_events(Game)

