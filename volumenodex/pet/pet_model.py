"""Writing Pet model definitions, profiles, and personality presets."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional


class PetMood(str, Enum):
    IDLE = "idle"
    WRITING = "writing"
    ALERT = "alert"
    CELEBRATING = "celebrating"
    SLEEPING = "sleeping"
    NUDGING = "nudging"


@dataclass
class PetProfile:
    id: str
    name: str
    species_title: str
    avatar_icon: str
    personality_tone: str
    custom_image_path: Optional[str] = None
    break_interval_minutes: int = 25
    break_timer_enabled: bool = True

    idle_quotes: List[str] = field(default_factory=list)
    milestone_quotes: List[str] = field(default_factory=list)
    break_quotes: List[str] = field(default_factory=list)
    prompt_ideas: List[str] = field(default_factory=list)


DEFAULT_PETS: Dict[str, PetProfile] = {
    "corvus": PetProfile(
        id="corvus",
        name="Corvus",
        species_title="The Literary Raven",
        avatar_icon="🪶",
        personality_tone="Gothic Wit & Literary Mystery",
        break_interval_minutes=25,
        break_timer_enabled=True,
        idle_quotes=[
            "The shadows dance across the parchment. What dark twist lurks in the next sentence?",
            "Ink is thicker than sea water. Press on, mortal wordsmith.",
            "Silence is the inkwell of the brooding mind.",
            "A well-placed secret weighs more than a thousand idle words.",
        ],
        milestone_quotes=[
            "Marvelous. Another milestone claimed from the void of the blank page.",
            "A grim victory over silence! Your manuscript grows ever more potent.",
            "Nevermore shall this word count be questioned. Outstanding craft.",
        ],
        break_quotes=[
            "Even ravens must fold their wings. Step away from the altar of prose, quench your thirst, and stretch.",
            "Your eyes require respite from the lantern light. Drink water, breathe deeply, and return renewed.",
        ],
        prompt_ideas=[
            "Introduce an unexpected sound from behind a locked door.",
            "Have a character reveal a truth by telling a convincing half-lie.",
            "Describe the temperature of the room and how it betrays someone's nervousness.",
            "What did someone in this scene steal, whether an object, a glance, or a memory?",
        ],
    ),
    "quill": PetProfile(
        id="quill",
        name="Quill",
        species_title="The Scholarly Owl",
        avatar_icon="🦉",
        personality_tone="Scholarly Wisdom & Gentle Guidance",
        break_interval_minutes=25,
        break_timer_enabled=True,
        idle_quotes=[
            "Every great library was written one sentence at a time.",
            "Pondering the right word is never wasted time.",
            "The architecture of your thoughts is beginning to take form.",
        ],
        milestone_quotes=[
            "Splendid progress! Your dedication honors the craft.",
            "Another milestone conquered with scholarly precision!",
        ],
        break_quotes=[
            "A wise scribe knows when to rest. Stretch your shoulders and take a drink of water!",
            "Time for a gentle break. Rest your eyes on something distant.",
        ],
        prompt_ideas=[
            "Focus on the tactile texture of an object in the character's hand.",
            "Contrast what the character says with what their hands are doing.",
        ],
    ),
    "ink": PetProfile(
        id="ink",
        name="Ink",
        species_title="The Cozy Cat",
        avatar_icon="🐾",
        personality_tone="Warm & Cozy Cheer",
        break_interval_minutes=25,
        break_timer_enabled=True,
        idle_quotes=[
            "*Purrs softly beside your manuscript*",
            "I'm keeping your warm spot on the desk ready.",
            "That last paragraph felt cozy. What happens next?",
        ],
        milestone_quotes=[
            "*Happy purr!* Look at all those words! Treat time!",
            "You did it! That was a huge word sprint!",
        ],
        break_quotes=[
            "Stretch like a cat! Stand up, reach for the ceiling, and drink some water!",
            "Time to take a little stretch break. I'll guard your chair.",
        ],
        prompt_ideas=[
            "Add a warm or comforting sensory detail to this scene.",
            "Have an animal react to the tension in the room.",
        ],
    ),
    "scout": PetProfile(
        id="scout",
        name="Scout",
        species_title="The Loyal Hound",
        avatar_icon="🐕",
        personality_tone="Enthusiastic Cheerleader",
        break_interval_minutes=20,
        break_timer_enabled=True,
        idle_quotes=[
            "You're doing awesome! Let's chase down the next chapter!",
            "I believe in this story!",
        ],
        milestone_quotes=[
            "*Tail wagging furiously!* Milestone unlocked! You're on fire today!",
        ],
        break_quotes=[
            "Break time! Let's get up, stretch our legs, and grab a cold drink of water!",
        ],
        prompt_ideas=[
            "Throw a sudden obstacle directly in your character's path!",
        ],
    ),
    "ignis": PetProfile(
        id="ignis",
        name="Ignis",
        species_title="The Inspiration Dragon",
        avatar_icon="🐉",
        personality_tone="Fiery & Bold",
        break_interval_minutes=30,
        break_timer_enabled=True,
        idle_quotes=[
            "Let the fire of your imagination burn through the page!",
            "Don't hold back—write with audacity.",
        ],
        milestone_quotes=[
            "*Breathes a spark of triumph!* Brilliant work, wordsmith!",
        ],
        break_quotes=[
            "Even dragon flames need a moment to cool. Hydrate and stretch your wings!",
        ],
        prompt_ideas=[
            "Raise the stakes: What is the worst thing that could happen right now?",
        ],
    ),
}
