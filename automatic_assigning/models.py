from datetime import datetime, timedelta
from typing import Type


def resolve_lookup(obj, dotted_path):
    for part in dotted_path.split("."):
        obj = getattr(obj, part, None)
        if obj is None:
            return None
        if callable(obj):
            obj = obj()

    return obj


def matches(obj, key, value):
    known_lookups = {"eq", "contains", "in"}

    parts = key.split("__")

    # Split key into field + lookup
    if len(parts) > 1 and parts[-1] in known_lookups:
        *field_parts, lookup = parts
        field_path = ".".join(field_parts)
    else:
        field_path = ".".join(parts)
        lookup = "eq"

    actual = resolve_lookup(obj, field_path)

    if lookup == "eq":
        return actual == value
    elif lookup == "contains":
        return value in actual if actual else False
    elif lookup == "in":
        return actual in value if value else False
    else:
        raise ValueError(f"Unsupported lookup: {lookup}")


_sentinel = object()
class ModelObjectsManager:
    def __init__(self, model_cls):
        self.model_cls = model_cls

    def all(self):
        return list(self.model_cls._instances.values())

    def filter(self, **kwargs):
        results = []
        for obj in self.all():
            if all(matches(obj, k, v) for k, v in kwargs.items()):
                results.append(obj)
        return results

    def get(self, pk=None, default=_sentinel, **kwargs):
        if pk:
            kwargs[self.model_cls.pk_field] = pk
        matches = self.filter(**kwargs)
        if (len(kwargs) == 0 or not matches) and default is _sentinel:
            raise ValueError("No matching object found.")
        if (len(kwargs) == 0 or not matches):
            return default
        if len(matches) > 1:
            raise ValueError("Multiple objects found.")
        return matches[0]


class Model:
    pk_field = None

    def __init_subclass__(cls):
        super().__init_subclass__()
        cls._instances = {}  # {pk: instance}
        cls.objects = ModelObjectsManager(cls)

    def __init__(self, pk_field=None):
        cls = self.__class__

        if pk_field is None:
            # Auto-increment primary key
            pks = list(cls._instances.keys())
            pks.sort()
            last_pk = pks[-1] if pks else 0
            self.pk = last_pk + 1
            pk_field = "pk"

        cls.pk_field = pk_field
        # Register instance
        cls._instances[getattr(self, pk_field)] = self


class AssignmentObject(Model):
    """
    Base class for objects that will be assigned to a slot (CrewMember, Aircraft, Official) to inherit from
    """
    def __init__(self, availability, default_availability=False):
        self.availability = availability
        self.default_availability = default_availability

        self.schedule = []

        super().__init__()

    def is_available(self, event, group):
        start_dt = event.start_time
        end_dt = event.end_time
        # TODO: Check availability

        # TODO: Check overlap and buffer
        for event in self.schedule:
            event_start = event.start_time
            event_end = event.end_time

            if start_dt < event_end and end_dt > event_start:
                return False  # Overlaps, not available

            # Ensure break period
            if event_end + group.assignment_buffer > start_dt and event_start < end_dt:
                return False

        return self.default_availability  # If there is no availability for this dt range

    def can_be_assigned(self, event: "Event", slot: "AssignmentSlot", group: "AssignmentGroup"):
        if not self.is_available(event, group):
            return False

        if group.find_assigned_object(self):  # Make sure it isn't assigned to any slot in the group
            return False

        return True


class AssignmentRule(Model):
    def __init__(self, rule_text):
        self.rule_text = rule_text

        super().__init__()

    def evaluate_should_assign(self):
        if self.rule_text == "ALWAYS":
            return True
        if self.rule_text == "NEVER":
            return False
        return None

        # TODO: Evaluate rule text

    def __eq__(self, other):
        if type(other) is AssignmentRule:
            return self.rule_text == other.rule_text
        return False


ALWAYS_RULE = AssignmentRule("ALWAYS")
NEVER_RULE = AssignmentRule("NEVER")
ANY_RULE = AssignmentRule("ANY")


class AssignmentSlot(Model):
    def __init__(self, name: str, object_to_assign: Type[AssignmentObject], amount: int = 1,
                 should_assign_rule: AssignmentRule = ALWAYS_RULE, rule: AssignmentRule = ANY_RULE):
        """

        :param name: Name of this slot (e.x. Center Referee, Pilot, Aircraft)
        :param object_to_assign: Object to assign in this slot (e.x. CrewMember, Referee, Aircraft)
        :param amount: Amount of objects to be assigned to this slot
        :param should_assign_rule: Rule for when this slot should be automatically filled (default is ALWAYS)
        :param rule: Rule for who/what can be assigned to this slot (default is ANY)
        """

        self.name = name
        self.object_to_assign = object_to_assign
        self.amount = amount
        self.should_assign_rule = should_assign_rule
        self.assigned_objects = []

        super().__init__("name")

    @property
    def should_assign(self):
        return self.should_assign_rule.evaluate_should_assign()

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


class AssignmentGroup(Model):
    def __init__(self, *slots: AssignmentSlot, **kwargs):
        """
        EXAMPLE
        class Flight(Model):
            ...
            crew = AssignmentSlots(CaptainSlot, CoCaptainSlot, FlightAttendantSlot)

        :param slots: A list of AssignmentSlot that will be assigned to this model
        """

        self.slots = slots
        self.assignment_buffer: timedelta = timedelta(minutes=15)

        for k, v in kwargs.items():
            setattr(self, k, v)

        super().__init__()

    @property
    def _assigned_objects(self):
        return [(slot, obj) for slot in self.slots for obj in slot.assigned_objects]

    @property
    def slots_names(self):
        return [slot.name for slot in self.slots]

    def get_assigned_objects_by_slot(self):
        res = []
        working_slot = None
        building = []

        for slot, obj in self._assigned_objects:
            if working_slot is None:
                working_slot = slot
            elif working_slot != slot:
                res.append((working_slot, building))
                building = []
                working_slot = slot

            building.append(obj)

        res.append((working_slot, building))
        return res

    def get_needed_assignments(self):
        needed = []
        for slot in self.slots:
            if not slot.should_assign:
                continue
            for i in range(slot.amount - len(slot.assigned_objects)):
                needed.append(slot)

        return needed

    def find_assigned_object(self, obj_to_find):
        for slot, obj in self._assigned_objects:
            if obj == obj_to_find:
                return slot

        return None

    def unassign(self, obj):
        slot = self.find_assigned_object(obj)
        if slot:
            slot.assigned_objects.remove(obj)

    def clear(self):
        for slot in self.slots:
            slot.assigned_objects = []

    def __setitem__(self, key: str, value: AssignmentObject):
        # key should be slot.name
        for slot in self.slots:
            if slot.name == key:
                if type(value) is slot.object_to_assign or value is None:
                    slot.assigned_objects.append(value)
                    return
                else:
                    raise TypeError(f"Attempted to assign incorrect type to AssignmentSlot. "
                                    f"Assigned: {type(value)}, Expected: {slot.object_to_assign}")

        raise KeyError(f"Could not find {key} in AssignmentSlots")

    def __getitem__(self, key: str):
        # key should be slot.name
        for slot in self.slots:
            if slot.name == key:
                return slot.assigned_objects

        raise KeyError(f"Could not find {key} in AssignmentSlots")

    def __iter__(self):
        yield from self._assigned_objects

    def __eq__(self, other):
        if type(other) == AssignmentGroup:
            return [s.name for s in self.slots] == [s.name for s in other.slots]

        return False

    def __repr__(self):
        return f"AssignmentGroup({', '.join([s.name for s in self.slots])})"


class EventType(Model):
    def __init__(self, name: str, default_duration: timedelta):
        self.name = name
        self.default_duration = default_duration

        super().__init__()


class Event(Model):
    def __init__(self, event_id: str, name: str, event_type: EventType, start_time: datetime, **kwargs):
        """
        Examples: Game, Flight

        :param event_id:
        :param name:
        :param event_type:
        :param start_time:
        """

        self.event_id = event_id
        self.name = name
        self.event_type = event_type
        self.start_time = start_time
        self.groups: list[EventGroup] = []

        self.duration_override = None

        for k, v in kwargs.items():
            # Allow user to type "duration" instead of "duration_override"
            if k == "duration":
                k = "duration_override"

            setattr(self, k, v)

        super().__init__("event_id")

    @property
    def assignment_groups(self):
        s = []
        for field, value in self.__dict__.items():
            if type(value) == AssignmentGroup:
                s.append(value)

        return s

    @property
    def duration(self):
        if self.duration_override:
            return self.duration_override
        return self.event_type.default_duration

    @duration.setter
    def duration(self, value):
        self.duration_override = value

    @property
    def end_time(self):
        return self.start_time + self.duration

    def get_assignment_group(self, group):
        for as_group in self.assignment_groups:
            if as_group == group:
                return as_group
        return None


class EventGroup(Model):
    def __init__(self, name, try_keep_assignments_in_group=True):
        """
        Group your events together (events can be in an infinite number of groups)
        Examples: Venue, Field, Route
        :param name:
        :param try_keep_assignments_in_group: If true, the assigner will try to keep assignments made for events in this
            group be the same across events in this group (e.x. you want to keep referees on the same field,
            you want to keep aircraft on the same route, etc.)
        """

        self.name = name
        self.try_keep_assignments_in_group = try_keep_assignments_in_group

        super().__init__()

    def get_events(self, event_type: Type[Event]):
        return event_type.objects.filter(groups__contains=self)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name
