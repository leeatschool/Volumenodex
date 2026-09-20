"""Screenplay data models: Screenplay Codex and Categorized Terms/Phrases Library."""

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any


# ==============================================================================
# 1. SCREENPLAY CODEX DATA MODELS (Screenplay-Optimized Writers Codex)
# ==============================================================================

@dataclass
class ScreenplayCharacter:
    """Character / Cast member dossier optimized for script writing."""
    id: str = field(default_factory=lambda: f"sc_char_{uuid.uuid4().hex[:8]}")
    name: str = "CHARACTER NAME"
    role: str = "Lead"  # Lead / Protagonist, Antagonist, Supporting, Minor, Cameo, Voiceover
    aliases: List[str] = field(default_factory=list)
    actor_notes: str = ""          # Casting idea, vocal timbre, actor archetype
    dialogue_voice: str = ""       # Cadence, idioms, sentence structure, speech mannerisms
    character_arc: str = ""        # Dramatic need, flaw, internal shift across acts
    wardrobe_notes: str = ""       # Costume, visual signature, recurring prop
    appearance: str = ""           # Age, physical presence, demeanor on camera
    first_scene: str = ""          # Establishing scene / entrance
    notes: str = ""                # General screenplay notes
    icon_type: str = "person"      # person, quill, corvus, ink, scout, ignis, custom
    custom_image_path: Optional[str] = None
    mention_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScreenplayCharacter":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ScreenplayScene:
    """Scene & Location profile with lighting setups, setting notes, and props."""
    id: str = field(default_factory=lambda: f"sc_scene_{uuid.uuid4().hex[:8]}")
    heading: str = "EXT. LOCATION - DAY"  # Full slugline
    int_ext: str = "EXT."                  # INT., EXT., INT./EXT.
    location_name: str = "LOCATION"
    time_of_day: str = "DAY"              # DAY, NIGHT, DUSK, DAWN, CONTINUOUS, LATER
    lighting_setup: str = ""              # e.g. LOW LIGHTING, LIT BY STREET LIGHTS ALONE
    setting_notes: str = ""               # Environment, sensory textures, mood
    stage_directions: str = ""            # Camera tracking, visual composition
    props: str = ""                       # Key props involved in scene
    characters_present: List[str] = field(default_factory=list)
    scene_number: int = 1
    synopsis: str = ""
    status: str = "Draft"                 # Draft, In Progress, Polished, Locked
    mention_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScreenplayScene":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ScreenplayAct:
    """Act breakdown and dramatic narrative beat."""
    id: str = field(default_factory=lambda: f"sc_act_{uuid.uuid4().hex[:8]}")
    act_number: str = "ACT I"            # ACT I, ACT IIA, ACT IIB, ACT III, COLD OPEN
    title: str = "The Hook & Inciting Incident"
    turning_point: str = ""
    synopsis: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScreenplayAct":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ScreenplayCodexManager:
    """Manages screenplay-specific cast, scene locations, acts, and live mentions."""

    def __init__(self):
        self.characters: List[ScreenplayCharacter] = []
        self.scenes: List[ScreenplayScene] = []
        self.acts: List[ScreenplayAct] = []

    def init_sample_defaults(self) -> None:
        """Loads a realistic, screenplay-ready cast and location dossier."""
        char1 = ScreenplayCharacter(
            id="sc_char_marcus",
            name="DETECTIVE MARCUS VANCE",
            role="Lead",
            aliases=["Marcus", "Vance", "Detective Vance"],
            actor_notes="Late 40s. Weathered, world-weary baritone. Think a gravel-voiced detective archetype.",
            dialogue_voice="Speaks in curt, clipped sentences. Rarely asks questions directly; uses silence as leverage.",
            character_arc="Driven by guilt over an unsolved arson; must choose between revenge and saving his partner.",
            wardrobe_notes="Worn charcoal wool overcoat, scuffed wingtips, silver vintage pocket watch.",
            appearance="Tall, slouched posture, silver streaks at temples, vigilant dark eyes.",
            first_scene="EXT. HARBOR DOCKS - NIGHT",
            notes="Has served 22 years on the metropolitan homicide desk.",
            icon_type="person"
        )
        char2 = ScreenplayCharacter(
            id="sc_char_elena",
            name="ELENA ROSTOVA",
            role="Antagonist",
            aliases=["Elena", "Rostova", "The Courier"],
            actor_notes="Mid 30s. Polished, icy confidence. Fluent multilingual diction with a slight accent.",
            dialogue_voice="Calculated, polite, unsettlingly calm even when threatened. Never raises her voice.",
            character_arc="Operates on strict mathematical self-preservation until her brother is captured.",
            wardrobe_notes="Tailored dark navy trench, black leather gloves, concealed titanium stylus.",
            appearance="Athletic build, razor-sharp jawline, dark hair pinned in a sleek chignon.",
            first_scene="INT. EMBASSY BALLROOM - NIGHT",
            notes="Former intelligence analyst turned high-stakes corporate broker.",
            icon_type="scout"
        )
        self.characters.extend([char1, char2])

        scene1 = ScreenplayScene(
            id="sc_scene_harbor",
            heading="EXT. HARBOR DOCKS - NIGHT",
            int_ext="EXT.",
            location_name="HARBOR DOCKS",
            time_of_day="NIGHT",
            lighting_setup="LOW LIGHTING, LIT BY STREET LIGHTS ALONE",
            setting_notes="Thick cold sea mist clinging to rusted freight cranes. Rain puddles shimmering in orange sodium light.",
            stage_directions="Camera glides along the wet asphalt, tracking low behind Marcus's long trench coat.",
            props="[PROP: Encrypted satellite transceiver, stained paper cargo manifest]",
            characters_present=["DETECTIVE MARCUS VANCE", "ELENA ROSTOVA"],
            scene_number=1,
            synopsis="Marcus stakes out the midnight cargo drop. Elena arrives under the fog barrier."
        )
        scene2 = ScreenplayScene(
            id="sc_scene_safehouse",
            heading="INT. ABANDONED ARCHIVE - DAY",
            int_ext="INT.",
            location_name="ABANDONED ARCHIVE",
            time_of_day="DAY",
            lighting_setup="DUSTY SUNBEAMS FILTERING THROUGH CRACKED SKYLIGHTS",
            setting_notes="Towering steel shelving collapsed under piles of water-damaged microfiche boxes. Dead quiet.",
            stage_directions="High crane shot tilting down as footsteps echo across the concrete floor.",
            props="[PROP: Microfilm reader, brass skeleton key]",
            characters_present=["DETECTIVE MARCUS VANCE"],
            scene_number=2,
            synopsis="Marcus uncovers the redacted police ledger from the 1998 waterfront fire."
        )
        self.scenes.extend([scene1, scene2])

        act1 = ScreenplayAct(
            id="sc_act_1",
            act_number="ACT I",
            title="The Waterfront Standoff",
            turning_point="Elena vanishes into the fog, leaving behind a cipher key that implicates the precinct.",
            synopsis="Introduction of Marcus Vance, the nocturnal stakeout at the docks, and the inciting cargo handoff."
        )
        act2 = ScreenplayAct(
            id="sc_act_2",
            act_number="ACT II",
            title="The Corrupt Ledger & The Chase",
            turning_point="Marcus discovers his commanding officer is receiving payoffs from Rostova's syndicate.",
            synopsis="The investigation deepens into city hall archives, high-speed vehicle pursuits through neon alleys."
        )
        self.acts.extend([act1, act2])

    def add_character(self, character: ScreenplayCharacter) -> None:
        self.characters.append(character)

    def remove_character(self, char_id: str) -> None:
        self.characters = [c for c in self.characters if c.id != char_id]

    def add_scene(self, scene: ScreenplayScene) -> None:
        self.scenes.append(scene)

    def remove_scene(self, scene_id: str) -> None:
        self.scenes = [s for s in self.scenes if s.id != scene_id]

    def add_act(self, act: ScreenplayAct) -> None:
        self.acts.append(act)

    def remove_act(self, act_id: str) -> None:
        self.acts = [a for a in self.acts if a.id != act_id]

    def find_mention(self, text: str) -> Optional[Any]:
        """Finds if text contains any character name, alias, or scene location."""
        if not text:
            return None
        t_lower = text.lower()

        for char in self.characters:
            if char.name.lower() in t_lower:
                return char
            for alias in char.aliases:
                if alias.strip() and alias.lower() in t_lower:
                    return char

        for scene in self.scenes:
            if scene.location_name.lower() in t_lower:
                return scene
            if scene.heading.lower() in t_lower:
                return scene

        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "characters": [c.to_dict() for c in self.characters],
            "scenes": [s.to_dict() for s in self.scenes],
            "acts": [a.to_dict() for a in self.acts]
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        if not data:
            return
        chars = data.get("characters", [])
        if chars:
            self.characters = [ScreenplayCharacter.from_dict(c) for c in chars]
        scenes = data.get("scenes", [])
        if scenes:
            self.scenes = [ScreenplayScene.from_dict(s) for s in scenes]
        acts = data.get("acts", [])
        if acts:
            self.acts = [ScreenplayAct.from_dict(a) for a in acts]


# ==============================================================================
# 2. DRAG AND DROP TERMS / PHRASES PALETTE DATA MODEL
# ==============================================================================

@dataclass
class ScreenplayPhrase:
    """A reusable drag-and-droppable screenplay snippet/term categorized by type."""
    id: str = field(default_factory=lambda: f"phrase_{uuid.uuid4().hex[:8]}")
    category: str = "Headings"       # Headings, Light Direction, Setting Notes, Stage Directions, Prop Directions, Act & Scene Markers, Custom Notes
    subcategory: str = "Exteriors"   # e.g. Exteriors, Interiors, Night, Day, Camera, Prop, Act, etc.
    title: str = "EXT. HOME - DAY"   # Display label
    text: str = "EXT. HOME - DAY\n"  # Script text inserted on drop/click
    description: str = ""            # Tooltip / contextual explanation
    is_custom: bool = False          # True for user-created reusable items

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScreenplayPhrase":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ScreenplayPhraseLibrary:
    """Preloaded library of categorized screenplay terms & phrases, with custom user persistence."""

    def __init__(self, custom_file_path: Optional[str] = None):
        self._custom_file_path = custom_file_path
        self.preloaded_phrases: List[ScreenplayPhrase] = []
        self.custom_phrases: List[ScreenplayPhrase] = []
        self._init_preloaded_phrases()
        self.load_custom_phrases()

    def _init_preloaded_phrases(self) -> None:
        """Populates the library with common screenplay conventions requested by the user."""
        items = [
            # --- 1. HEADINGS: EXTERIORS ---
            ScreenplayPhrase(
                category="Headings", subcategory="Exteriors",
                title="EXT. HOME - DAY",
                text="EXT. HOME - DAY\n",
                description="Standard exterior house daytime slugline"
            ),
            ScreenplayPhrase(
                category="Headings", subcategory="Exteriors",
                title="EXT. HOME - NIGHT",
                text="EXT. HOME - NIGHT\n",
                description="Standard exterior house nighttime slugline"
            ),
            ScreenplayPhrase(
                category="Headings", subcategory="Exteriors",
                title="EXTERIOR: HOME",
                text="EXTERIOR: HOME - DAY\n",
                description="Explicit exterior home heading format"
            ),
            ScreenplayPhrase(
                category="Headings", subcategory="Exteriors",
                title="EXT. DOWNTOWN STREET - NIGHT",
                text="EXT. DOWNTOWN STREET - NIGHT\n",
                description="Urban city street scene after dark"
            ),
            ScreenplayPhrase(
                category="Headings", subcategory="Exteriors",
                title="EXT. HIGHWAY - SUNSET",
                text="EXT. HIGHWAY - SUNSET\n",
                description="Open road during magic hour / golden hour"
            ),
            ScreenplayPhrase(
                category="Headings", subcategory="Exteriors",
                title="EXT. DEEP WOODS - NIGHT",
                text="EXT. DEEP WOODS - NIGHT\n",
                description="Atmospheric wilderness nighttime heading"
            ),
            ScreenplayPhrase(
                category="Headings", subcategory="Exteriors",
                title="EXT. ROOFTOP - DUSK",
                text="EXT. ROOFTOP - DUSK\n",
                description="Overlooking city skyline at sunset"
            ),
            ScreenplayPhrase(
                category="Headings", subcategory="Exteriors",
                title="EXT. ALLEYWAY - RAIN",
                text="EXT. ALLEYWAY - NIGHT (RAIN)\n",
                description="Noir alleyway with downpour"
            ),
            ScreenplayPhrase(
                category="Headings", subcategory="Exteriors",
                title="EXT. PARKING LOT - NIGHT",
                text="EXT. PARKING LOT - NIGHT\n",
                description="Sprawling commercial lot under high stadium lights"
            ),

            # --- 1. HEADINGS: INTERIORS ---
            ScreenplayPhrase(
                category="Headings", subcategory="Interiors",
                title="INT. LIVING ROOM - DAY",
                text="INT. LIVING ROOM - DAY\n",
                description="Domestic daytime interior"
            ),
            ScreenplayPhrase(
                category="Headings", subcategory="Interiors",
                title="INT. LIVING ROOM - NIGHT",
                text="INT. LIVING ROOM - NIGHT\n",
                description="Domestic nighttime interior"
            ),
            ScreenplayPhrase(
                category="Headings", subcategory="Interiors",
                title="INT. KITCHEN - MORNING",
                text="INT. KITCHEN - MORNING\n",
                description="Early morning domestic scene"
            ),
            ScreenplayPhrase(
                category="Headings", subcategory="Interiors",
                title="INT. BEDROOM - NIGHT",
                text="INT. BEDROOM - NIGHT\n",
                description="Late night intimate or suspense setting"
            ),
            ScreenplayPhrase(
                category="Headings", subcategory="Interiors",
                title="INT. POLICE INTERROGATION ROOM - NIGHT",
                text="INT. POLICE INTERROGATION ROOM - NIGHT\n",
                description="High tension two-way mirror setting"
            ),
            ScreenplayPhrase(
                category="Headings", subcategory="Interiors",
                title="INT. CORPORATE OFFICE - DAY",
                text="INT. CORPORATE OFFICE - DAY\n",
                description="Sterile workplace environment"
            ),
            ScreenplayPhrase(
                category="Headings", subcategory="Interiors",
                title="INT. HOSPITAL CORRIDOR - DAY",
                text="INT. HOSPITAL CORRIDOR - DAY\n",
                description="Urgent medical or institutional hallway"
            ),
            ScreenplayPhrase(
                category="Headings", subcategory="Interiors",
                title="INT. COFFEE SHOP - DAY",
                text="INT. COFFEE SHOP - DAY\n",
                description="Casual dialogue meeting location"
            ),
            ScreenplayPhrase(
                category="Headings", subcategory="Interiors",
                title="INT. DIVE BAR - NIGHT",
                text="INT. DIVE BAR - NIGHT\n",
                description="Noisy, dimly lit watering hole"
            ),
            ScreenplayPhrase(
                category="Headings", subcategory="Interiors",
                title="INTERIOR: OFFICE",
                text="INTERIOR: OFFICE - DAY\n",
                description="Explicit interior office heading format"
            ),

            # --- 1. HEADINGS: INT./EXT. & INSERTS ---
            ScreenplayPhrase(
                category="Headings", subcategory="Int./Ext. & Special",
                title="INT./EXT. CAR (MOVING) - CONTINUOUS",
                text="INT./EXT. CAR (MOVING) - CONTINUOUS\n",
                description="Vehicular chase or conversation in motion"
            ),
            ScreenplayPhrase(
                category="Headings", subcategory="Int./Ext. & Special",
                title="INT./EXT. FRONT PORCH - DUSK",
                text="INT./EXT. FRONT PORCH - DUSK\n",
                description="Threshold between inside and outside"
            ),
            ScreenplayPhrase(
                category="Headings", subcategory="Int./Ext. & Special",
                title="EST. METROPOLIS SKYLINE - DAWN",
                text="EST. METROPOLIS SKYLINE - DAWN\n",
                description="Establishing shot of urban dawn"
            ),
            ScreenplayPhrase(
                category="Headings", subcategory="Int./Ext. & Special",
                title="INSERT - SMARTPHONE SCREEN",
                text="INSERT - SMARTPHONE SCREEN\n",
                description="Close-up detail shot of incoming message"
            ),
            ScreenplayPhrase(
                category="Headings", subcategory="Int./Ext. & Special",
                title="INSERT - WRITTEN LETTER",
                text="INSERT - WRITTEN NOTE\n",
                description="Close-up detail of physical document"
            ),
            ScreenplayPhrase(
                category="Headings", subcategory="Int./Ext. & Special",
                title="POV - BINOCULARS",
                text="POV - BINOCULARS\n",
                description="Surveillance point of view"
            ),

            # --- 2. LIGHT DIRECTION & ATMOSPHERE: NIGHT ---
            ScreenplayPhrase(
                category="Light Direction", subcategory="Night",
                title="LOW LIGHTING, LIT BY STREET LIGHTS ALONE",
                text="LOW LIGHTING, LIT BY STREET LIGHTS ALONE.\n",
                description="Sodium vapor amber pools cutting through dense darkness"
            ),
            ScreenplayPhrase(
                category="Light Direction", subcategory="Night",
                title="PITCH BLACK, FLICKERING FLASHLIGHT",
                text="PITCH BLACK, BROKEN ONLY BY A FLICKERING FLASHLIGHT BEAM.\n",
                description="High suspense tunnel or blackout scene"
            ),
            ScreenplayPhrase(
                category="Light Direction", subcategory="Night",
                title="HARSH MOONLIGHT THROUGH BLINDS",
                text="HARSH MOONLIGHT FILTERING THROUGH VENETIAN BLINDS.\n",
                description="Noir banded shadows across room"
            ),
            ScreenplayPhrase(
                category="Light Direction", subcategory="Night",
                title="NEON PULSE RED AND CYAN",
                text="NEON SIGNS OUTSIDE SPILLING FLASHES OF CRIMSON AND CYAN.\n",
                description="Cyberpunk or gritty urban street reflection"
            ),
            ScreenplayPhrase(
                category="Light Direction", subcategory="Night",
                title="DEEP SHADOWS, CANDLELIGHT",
                text="DEEP CHIAROSCURO SHADOWS, LIT SOLELY BY A SINGLE CANDLE FLAME.\n",
                description="Intimate historical or occult atmosphere"
            ),
            ScreenplayPhrase(
                category="Light Direction", subcategory="Night",
                title="SWEEPING POLICE SEARCHLIGHT",
                text="SWEEPING POLICE SPOTLIGHTS CUTTING THROUGH THICK ROADSIDE FOG.\n",
                description="High-stakes pursuit illumination"
            ),

            # --- 2. LIGHT DIRECTION & ATMOSPHERE: DAY ---
            ScreenplayPhrase(
                category="Light Direction", subcategory="Day",
                title="BLINDING MIDDAY SUN",
                text="BLINDING MIDDAY SUN, HARSH OVEREXPOSURE AND HEAT SHIMMER.\n",
                description="Desert or sweltering summer exterior"
            ),
            ScreenplayPhrase(
                category="Light Direction", subcategory="Day",
                title="GOLDEN HOUR SUNSET",
                text="GOLDEN HOUR SUNSET, LONG WARM AMBER SHADOWS LENGTHENING.\n",
                description="Poetic cinematic twilight lighting"
            ),
            ScreenplayPhrase(
                category="Light Direction", subcategory="Day",
                title="SOFT DIFFUSED MORNING FOG",
                text="SOFT DIFFUSED MORNING LIGHT FILTERING THROUGH COASTAL FOG.\n",
                description="Gentle pastel morning atmosphere"
            ),
            ScreenplayPhrase(
                category="Light Direction", subcategory="Day",
                title="OVERCAST AND SHADOWLESS",
                text="DULL OVERCAST GREY, A SHADOWLESS SLATE SKY.\n",
                description="Bleak, somber Scandinavian daytime lighting"
            ),
            ScreenplayPhrase(
                category="Light Direction", subcategory="Day",
                title="STERILE FLUORESCENT TUBES",
                text="STERILE, HUMMING FLUORESCENT WHITE OFFICE LIGHTING.\n",
                description="Unforgiving bureaucratic or clinical glow"
            ),

            # --- 2. LIGHT DIRECTION: DRAMATIC & PRACTICAL ---
            ScreenplayPhrase(
                category="Light Direction", subcategory="Dramatic & Practical",
                title="PALE COMPUTER MONITOR GLOW",
                text="PALE BLUE MONITOR GLOW ILLUMINATING TIRED, HOLLOW EYES.\n",
                description="Late-night hacker or researcher setup"
            ),
            ScreenplayPhrase(
                category="Light Direction", subcategory="Dramatic & Practical",
                title="EMERGENCY KLAXON STROBE",
                text="EMERGENCY RED WARNING LIGHT PULSING IN RHYTHMIC STROBES.\n",
                description="Facility breach or submarine alert"
            ),
            ScreenplayPhrase(
                category="Light Direction", subcategory="Dramatic & Practical",
                title="SHARP SILHOUETTE IN DOORWAY",
                text="SILHOUETTED AGAINST BLINDING WHITE BACKLIGHT IN THE OPEN DOORWAY.\n",
                description="Ominous entrance or mysterious visitor"
            ),

            # --- 3. SETTING NOTES & ENVIRONMENTS ---
            ScreenplayPhrase(
                category="Setting Notes", subcategory="Environments",
                title="Cluttered Brownstone Apartment",
                text="A cramped, rain-battered brownstone apartment reeking of stale coffee and waterlogged books. Newspapers yellow on the sill.\n",
                description="Lived-in, exhausted private detective or writer home"
            ),
            ScreenplayPhrase(
                category="Setting Notes", subcategory="Environments",
                title="Sterile Server Vault",
                text="A subterranean server room, frosted glass humming with silent cooling fans. Cold dry air smelling of ionized ozone.\n",
                description="High security corporate data vault"
            ),
            ScreenplayPhrase(
                category="Setting Notes", subcategory="Environments",
                title="Echoey Industrial Pier",
                text="An abandoned dockside warehouse where rotting wooden pylons creak against the dark tide. Salt spray glazes the concrete.\n",
                description="Crime meetup or tense drop zone"
            ),
            ScreenplayPhrase(
                category="Setting Notes", subcategory="Environments",
                title="Desolate Highway Diner",
                text="A sunbaked roadside diner surrounded by miles of dried sagebrush and buzzing power lines. An old jukebox hums low.\n",
                description="Midwest or desert isolation"
            ),
            ScreenplayPhrase(
                category="Setting Notes", subcategory="Environments",
                title="Sunlit Breakfast Nook",
                text="A bright, cozy breakfast corner scattered with Sunday crosswords, half-spread marmalade, and steaming porcelain mugs.\n",
                description="Peaceful domestic sanctuary before conflict"
            ),

            # --- 4. STAGE DIRECTIONS: CAMERA & PACING ---
            ScreenplayPhrase(
                category="Stage Directions", subcategory="Camera & Transitions",
                title="FADE IN:",
                text="FADE IN:\n\n",
                description="Traditional opening transition"
            ),
            ScreenplayPhrase(
                category="Stage Directions", subcategory="Camera & Transitions",
                title="CUT TO:",
                text="\n                                            CUT TO:\n\n",
                description="Standard hard transition to next scene"
            ),
            ScreenplayPhrase(
                category="Stage Directions", subcategory="Camera & Transitions",
                title="SMASH CUT TO:",
                text="\n                                            SMASH CUT TO:\n\n",
                description="Abrupt, startling cut on high momentum"
            ),
            ScreenplayPhrase(
                category="Stage Directions", subcategory="Camera & Transitions",
                title="MATCH CUT TO:",
                text="\n                                            MATCH CUT TO:\n\n",
                description="Visual or thematic continuity cut"
            ),
            ScreenplayPhrase(
                category="Stage Directions", subcategory="Camera & Transitions",
                title="DISSOLVE TO:",
                text="\n                                            DISSOLVE TO:\n\n",
                description="Soft temporal or spatial transition"
            ),
            ScreenplayPhrase(
                category="Stage Directions", subcategory="Camera & Transitions",
                title="FADE OUT.",
                text="\n                                            FADE OUT.\n",
                description="End of act or screen fade"
            ),
            ScreenplayPhrase(
                category="Stage Directions", subcategory="Camera & Transitions",
                title="SLOW TRACKING SHOT -",
                text="SLOW TRACKING SHOT -\n",
                description="Camera follows moving character or vehicle"
            ),
            ScreenplayPhrase(
                category="Stage Directions", subcategory="Camera & Transitions",
                title="CLOSE-UP ON:",
                text="CLOSE-UP ON:\n",
                description="Pulls focus to crucial face or micro-action"
            ),
            ScreenplayPhrase(
                category="Stage Directions", subcategory="Camera & Transitions",
                title="DUTCH ANGLE -",
                text="DUTCH ANGLE - The room tilts precariously as panic sets in.\n",
                description="Disorienting tilted frame for psychological tension"
            ),

            # --- 4. STAGE DIRECTIONS: PARENTHETICALS & GESTURES ---
            ScreenplayPhrase(
                category="Stage Directions", subcategory="Parentheticals",
                title="(beat)",
                text="(beat)\n",
                description="Brief pause for comedic or dramatic timing"
            ),
            ScreenplayPhrase(
                category="Stage Directions", subcategory="Parentheticals",
                title="(whispering)",
                text="(whispering)\n",
                description="Hushed vocal delivery"
            ),
            ScreenplayPhrase(
                category="Stage Directions", subcategory="Parentheticals",
                title="(turning sharply)",
                text="(turning sharply)\n",
                description="Sudden physical reaction"
            ),
            ScreenplayPhrase(
                category="Stage Directions", subcategory="Parentheticals",
                title="(hesitating)",
                text="(hesitating)\n",
                description="Momentary uncertainty or moral dilemma"
            ),
            ScreenplayPhrase(
                category="Stage Directions", subcategory="Parentheticals",
                title="(leaning across table)",
                text="(leaning across table)\n",
                description="Aggressive or intimate shift in distance"
            ),
            ScreenplayPhrase(
                category="Stage Directions", subcategory="Parentheticals",
                title="(checking watch)",
                text="(checking watch)\n",
                description="Urgency or impatience gesture"
            ),
            ScreenplayPhrase(
                category="Stage Directions", subcategory="Parentheticals",
                title="(under breath)",
                text="(under breath)\n",
                description="Muttered confidential reaction"
            ),
            ScreenplayPhrase(
                category="Stage Directions", subcategory="Parentheticals",
                title="(voice trembling)",
                text="(voice trembling)\n",
                description="Suppressed grief or terror"
            ),

            # --- 5. PROP DIRECTIONS ---
            ScreenplayPhrase(
                category="Prop Directions", subcategory="Tactical & Weapons",
                title="Concealed Revolver",
                text="[PROP: Concealed snub-nosed revolver tucked securely inside left lapel holster]\n",
                description="Hidden sidearm note for stage and prop department"
            ),
            ScreenplayPhrase(
                category="Prop Directions", subcategory="Tactical & Weapons",
                title="Tactical Field Radio",
                text="[PROP: Heavy black tactical field radio with military-grade antenna and squelch toggle]\n",
                description="Communications gear note"
            ),
            ScreenplayPhrase(
                category="Prop Directions", subcategory="Clues & Documents",
                title="Encrypted USB Thumb Drive",
                text="[PROP: Scratched aluminum encrypted flash drive, red LED blinking on activity]\n",
                description="Crucial technological clue"
            ),
            ScreenplayPhrase(
                category="Prop Directions", subcategory="Clues & Documents",
                title="Torn Polaroid Photograph",
                text="[PROP: Faded Polaroid photograph from 1989, right edge scorched and ragged]\n",
                description="Emotional or mystery focal prop"
            ),
            ScreenplayPhrase(
                category="Prop Directions", subcategory="Clues & Documents",
                title="Sealed Manila Envelope",
                text="[PROP: Thick sealed manila folder stamped 'TOP SECRET / DEPT OF HOMELAND SECURITY']\n",
                description="Sensitive document payload"
            ),
            ScreenplayPhrase(
                category="Prop Directions", subcategory="Atmospheric & Daily",
                title="Vintage Zippo Lighter",
                text="[PROP: Engraved brass trench zippo lighter, lid snaps shut with a crisp metallic ring]\n",
                description="Signature character accessory"
            ),
            ScreenplayPhrase(
                category="Prop Directions", subcategory="Atmospheric & Daily",
                title="Steaming Paper Coffee Cup",
                text="[PROP: Crushed diner paper cup with lipstick smudge around plastic drinking rim]\n",
                description="Everyday scene texture"
            ),
            ScreenplayPhrase(
                category="Prop Directions", subcategory="Atmospheric & Daily",
                title="Skeleton Key",
                text="[PROP: Heavy tarnished iron skeleton key tied to leather lanyard]\n",
                description="Antique lock opening device"
            ),

            # --- 6. ACT & SCENE MARKERS ---
            ScreenplayPhrase(
                category="Act & Scene Markers", subcategory="Acts",
                title="ACT I: THE HOOK & STATUS QUO",
                text="\n\nACT I: THE HOOK & STATUS QUO\n\n",
                description="Opening act marker"
            ),
            ScreenplayPhrase(
                category="Act & Scene Markers", subcategory="Acts",
                title="ACT II - PART 1: ESCALATION",
                text="\n\nACT II - PART 1: THE ROAD OF TRIALS\n\n",
                description="Rising stakes and new complications"
            ),
            ScreenplayPhrase(
                category="Act & Scene Markers", subcategory="Acts",
                title="ACT II - PART 2: MIDPOINT CRISIS",
                text="\n\nACT II - PART 2: MIDPOINT CRISIS & ALL IS LOST\n\n",
                description="Major reversal or devastation"
            ),
            ScreenplayPhrase(
                category="Act & Scene Markers", subcategory="Acts",
                title="ACT III: CLIMAX & RESOLUTION",
                text="\n\nACT III: THE CLIMAX & RESOLUTION\n\n",
                description="Final confrontation and aftermath"
            ),
            ScreenplayPhrase(
                category="Act & Scene Markers", subcategory="Acts",
                title="COLD OPEN",
                text="COLD OPEN\n\n",
                description="Pre-credits teaser sequence"
            ),
            ScreenplayPhrase(
                category="Act & Scene Markers", subcategory="Acts",
                title="TAG / EPILOGUE",
                text="\n\nTAG / EPILOGUE\n\n",
                description="Post-credits or coda scene"
            ),
            ScreenplayPhrase(
                category="Act & Scene Markers", subcategory="Scenes & Sequences",
                title="SCENE 1",
                text="SCENE 1\n",
                description="Numbered scene marker"
            ),
            ScreenplayPhrase(
                category="Act & Scene Markers", subcategory="Scenes & Sequences",
                title="MONTAGE -",
                text="MONTAGE -\nA) Character trains in torrential rain.\nB) Reviewing satellite surveillance photos.\nC) Loading cargo into the truck.\nEND OF MONTAGE.\n",
                description="Screenplay montage block"
            ),
            ScreenplayPhrase(
                category="Act & Scene Markers", subcategory="Scenes & Sequences",
                title="FLASHBACK -",
                text="FLASHBACK -\nINT. OLD FAMILY HOME - 10 YEARS AGO\n",
                description="Temporal leap backwards"
            ),
            ScreenplayPhrase(
                category="Act & Scene Markers", subcategory="Scenes & Sequences",
                title="BACK TO PRESENT",
                text="BACK TO PRESENT\n",
                description="Return to primary storyline timeline"
            ),
        ]
        self.preloaded_phrases = items

    def _get_custom_storage_path(self) -> str:
        if self._custom_file_path:
            parent_dir = os.path.dirname(self._custom_file_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            return self._custom_file_path
        cache_dir = os.path.expanduser("~/.volumenodex")
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, "screenplay_custom_phrases.json")

    def load_custom_phrases(self) -> None:
        """Loads custom user phrases from local storage."""
        path = self._get_custom_storage_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.custom_phrases = [
                        ScreenplayPhrase.from_dict({**item, "is_custom": True})
                        for item in data
                    ]
            except Exception as e:
                print(f"Failed to load custom screenplay phrases: {e}")
                self.custom_phrases = []
        else:
            self.custom_phrases = []

    def save_custom_phrases(self) -> None:
        """Saves custom phrases persistently."""
        path = self._get_custom_storage_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump([p.to_dict() for p in self.custom_phrases], f, indent=2)
        except Exception as e:
            print(f"Failed to save custom screenplay phrases: {e}")

    def add_custom_phrase(self, phrase: ScreenplayPhrase) -> None:
        phrase.is_custom = True
        self.custom_phrases.append(phrase)
        self.save_custom_phrases()

    def remove_custom_phrase(self, phrase_id: str) -> None:
        self.custom_phrases = [p for p in self.custom_phrases if p.id != phrase_id]
        self.save_custom_phrases()

    def get_all_phrases(self) -> List[ScreenplayPhrase]:
        return self.preloaded_phrases + self.custom_phrases

    def get_phrases_by_category(self, category: str) -> List[ScreenplayPhrase]:
        """Returns phrases belonging to the given category, or all phrases."""
        if category in ("All", "All Categories"):
            return self.get_all_phrases()
        return [p for p in self.get_all_phrases() if p.category.lower() == category.lower()]

    def get_categories(self) -> List[str]:
        cats = [
            "Headings",
            "Light Direction",
            "Setting Notes",
            "Stage Directions",
            "Prop Directions",
            "Act & Scene Markers",
            "Custom Notes"
        ]
        return cats

    def get_all_categories(self) -> List[str]:
        return self.get_categories()
