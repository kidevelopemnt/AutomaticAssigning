from datetime import timedelta, datetime
from unittest import TestCase
from automatic_assigning.assigner import Assigner
from automatic_assigning.models import Event, EventType, AssignmentGroup, AssignmentSlot, \
    AssignmentObject, EventGroup


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


class AssignerTest(TestCase):
    def setUp(self):
        field1 = FieldGroup("Field 1")
        field2 = FieldGroup("Field 2")
        u9_10 = AgeGroup("U9/10", timedelta(minutes=55))
        u11_12 = AgeGroup("U11/12", timedelta(hours=1, minutes=5))

        ref1 = Referee("Ref 1")
        ref2 = Referee("Ref 2")
        ref3 = Referee("Ref 3")
        ref4 = Referee("Ref 4")
        ref5 = Referee("Ref 5")
        ref6 = Referee("Ref 5")
        unavailable_ref = Referee("Ref6")

        game11 = Game("GAME11", "Game #11", u9_10, datetime(2025, 6, 9, 8, 0), field1)   # 06/09/25 08:00 AM
        game11.referees.slots[0].assigned_objects.append(ref1)
        game11.referees.slots[1].assigned_objects.append(ref2)
        game11.referees.slots[1].assigned_objects.append(ref3)
        game12 = Game("GAME12", "Game #12", u9_10, datetime(2025, 6, 9, 10, 0), field1)  # 06/09/25 10:00 AM

        game21 = Game("GAME21", "Game #21", u11_12, datetime(2025, 6, 9, 10, 0), field2)  # 06/09/25 08:00 AM
        game22 = Game("GAME22", "Game #22", u11_12, datetime(2025, 6, 9, 10, 0), field2)  # 06/09/25 10:00 AM

    def test_assigning(self):
        assigner = Assigner()
        assigner.assign_events(Game)

        game11 = Game.objects.get("GAME11")
        game12 = Game.objects.get("GAME12")
        game21 = Game.objects.get("GAME21")
        game22 = Game.objects.get("GAME22")

        self.assertEqual(game11.referees.slots[0].assigned_objects, game12.referees.slots[0].assigned_objects)
        self.assertEqual(game11.referees.slots[1].assigned_objects, game12.referees.slots[1].assigned_objects)

        self.assertEqual(game21.referees.slots[1].assigned_objects, game22.referees.slots[1].assigned_objects)
        self.assertEqual(game21.referees.slots[1].assigned_objects, game22.referees.slots[1].assigned_objects)

