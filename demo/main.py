from automatic_assigning import Assigner
from models import AgeGroup, FieldGroup, Game, Referee
from datetime import datetime, timedelta


def create_records():
    field1 = FieldGroup("Field 1")
    field2 = FieldGroup("Field 2")
    u9_10 = AgeGroup("U9/10", timedelta(minutes=55))
    u11_12 = AgeGroup("U11/12", timedelta(hours=1, minutes=5))

    ref1 = Referee("Ref 1")  # Super qualified, been working forever
    ref2 = Referee("Ref 2")  # U12- Center, U16- AR
    ref3 = Referee("Ref 3")  # U12- Center, U12- AR
    ref4 = Referee("Ref 4")  # U10- Center, U12- AR
    ref5 = Referee("Ref 5")  # Brand new, U10- AR
    ref6 = Referee("Ref 6")  # Brand new, U10- AR
    unavailable_ref = Referee("Ref0")

    game11 = Game("GAME11", "Game #11", u9_10, datetime(2025, 6, 9, 8, 0), field1)  # 06/09/25 08:00 AM
    game12 = Game("GAME12", "Game #12", u9_10, datetime(2025, 6, 9, 9, 30), field1)  # 06/09/25 09:30 AM
    game13 = Game("GAME13", "Game #13", u9_10, datetime(2025, 6, 9, 11, 0), field1)  # 06/09/25 11:00 AM

    game21 = Game("GAME21", "Game #21", u11_12, datetime(2025, 6, 9, 8, 0), field2)  # 06/09/25 08:00 AM
    game22 = Game("GAME22", "Game #22", u11_12, datetime(2025, 6, 9, 10, 0), field2)  # 06/09/25 10:00 AM
    game23 = Game("GAME23", "Game #23", u11_12, datetime(2025, 6, 9, 12, 0), field2)  # 06/09/25 12:00 PM


if __name__ == "__main__":
    assigner = Assigner()
    assigner.assign_events(Game)
