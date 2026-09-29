from .bicep_curl import BicepCurlTracker
from .squat import SquatTracker
from .pushup import PushUpTracker
from .lunges import LungesTracker
from .shoulder_press import ShoulderPressTracker
from .jumping_jacks import JumpingJacksTracker
from .high_knees import HighKneesTracker
from .mountain_climbers import MountainClimbersTracker
from .plank import PlankTracker
from .glute_bridge import GluteBridgeTracker
from .situps import SitUpsTracker
from .crunches import CrunchesTracker
from .leg_raise import LegRaisesTracker
from .russian_twist import RussianTwistTracker
from .bicycle_crunch import BicycleCrunchTracker
from .side_lunge import SideLungeTracker
from .calf_raise import CalfRaiseTracker
from .front_raise import FrontRaiseTracker
from .lateral_raise import LateralRaiseTracker
from .tricep_extension import TricepExtensionTracker

class ExerciseRegistry:
    """
    Central Exercise Registry mapping exercise numbers to Tracker classes.
    """
    EXERCISES = {
        "1": ("Bicep Curl", BicepCurlTracker),
        "2": ("Squat", SquatTracker),
        "3": ("Push-up", PushUpTracker),
        "4": ("Lunges", LungesTracker),
        "5": ("Shoulder Press", ShoulderPressTracker),
        "6": ("Jumping Jacks", JumpingJacksTracker),
        "7": ("High Knees", HighKneesTracker),
        "8": ("Mountain Climbers", MountainClimbersTracker),
        "9": ("Plank", PlankTracker),
        "10": ("Glute Bridge", GluteBridgeTracker),
        "11": ("Sit-ups", SitUpsTracker),
        "12": ("Crunches", CrunchesTracker),
        "13": ("Leg Raises", LegRaisesTracker),
        "14": ("Russian Twists", RussianTwistTracker),
        "15": ("Bicycle Crunches", BicycleCrunchTracker),
        "16": ("Side Lunges", SideLungeTracker),
        "17": ("Calf Raises", CalfRaiseTracker),
        "18": ("Front Raises", FrontRaiseTracker),
        "19": ("Lateral Raises", LateralRaiseTracker),
        "20": ("Tricep Extensions", TricepExtensionTracker),
    }

    @classmethod
    def get_tracker(cls, choice_key):
        key = str(choice_key).strip()
        if key not in cls.EXERCISES:
            key = "1"
        name, tracker_cls = cls.EXERCISES[key]
        return tracker_cls()

    @classmethod
    def list_exercises(cls):
        return [(k, name) for k, (name, _) in cls.EXERCISES.items()]
