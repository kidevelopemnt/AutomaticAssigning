from datetime import datetime, timedelta


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

    def get(self, pk=None, default=None, **kwargs):
        if pk:
            kwargs[self.model_cls.pk_field] = pk
        matches = self.filter(**kwargs)
        if not matches and not default:
            raise ValueError("No matching object found.")
        if not matches:
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
    pass


class AssignmentPosition(Model):
    def __init__(self, name: str, object_to_assign: AssignmentObject):
        """

        :param name: Name of the position (e.x. "Captain" "Flight Attendant" "Assistant Referee"
        :param object_to_assign: Object that will be assigned (e.x. CrewMember, Aircraft, Official)
        """

        self.name = name
        self.object_to_assign = object_to_assign

        super().__init__()


class AssignmentRule(Model):
    def __init__(self, rule_text):
        self.rule_text = rule_text

        super().__init__()

    def evaluate(self):
        if self.rule_text == "ALWAYS":
            return True
        if self.rule_text == "NEVER":
            return False

        # TODO: Evaluate rule text

    def __eq__(self, other):
        if type(other) is AssignmentRule:
            return self.rule_text == other.rule_text
        return False


ALWAYS_RULE = AssignmentRule("ALWAYS")
NEVER_RULE = AssignmentRule("NEVER")


class AssignmentSlot(Model):
    def __init__(self, position: AssignmentPosition, amount: int = 1, rule: AssignmentRule = ALWAYS_RULE):
        """

        :param position: Position that this is a slot for
        :param amount: Amount of objects to be assigned to this slot
        :param rule: Rule for when this slot should be automatically filled (default is ALWAYS)
        """

        self.position = position
        self.amount = amount
        self.rule = rule
        self.assigned_objects = []

        super().__init__()

    @property
    def should_assign(self):
        return self.rule.evaluate()


class AssignmentSlots(Model):
    def __init__(self, slots: list[AssignmentSlot]):
        """
        EXAMPLE
        class Flight(Model):
            ...
            crew = AssignmentSlots(CaptainSlot, CoCaptainSlot, FlightAttendantSlot)

        :param slots: A list of AssignmentSlot that will be assigned to this model
        """

        self.slots = slots

        super().__init__()


class EventType(Model):
    def __init__(self, name: str, default_duration: timedelta, assignment_buffer: timedelta = timedelta(minutes=15)):
        self.name = name
        self.default_duration = default_duration
        self.assignment_buffer = assignment_buffer

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

        self.assignment_buffer_override = None
        self.duration_override = None

        for k, v in kwargs.items():
            # Allow user to type "duration" instead of "duration_override"
            if k == "duration":
                k = "duration_override"
            elif k == "assignment_buffer":
                k = "assignment_buffer_override"

            setattr(self, k, v)

        super().__init__("event_id")

    @property
    def assignment_buffer(self):
        if self.assignment_buffer_override:
            return self.assignment_buffer_override
        return self.event_type.assignment_buffer

    @property
    def duration(self):
        if self.duration_override:
            return self.duration_override
        return self.event_type.default_duration
