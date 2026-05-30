"""
Intent Parser - Convert natural language to Revit building operations.

Parses user's natural language descriptions and extracts structured
building intents that can be executed via the RevitClient.

Usage:
    parser = IntentParser()
    intent = parser.parse("在三楼建一面5米长的墙")
    # -> BuildingIntent(action="create_wall", params={...})
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BuildingIntent:
    """A parsed building intent from natural language.

    Attributes:
        action: The action to perform (create_wall, create_room, etc.)
        params: Parameters for the action
        confidence: Confidence score (0-1)
        raw_text: Original user input
        needs_confirmation: Whether user should confirm before executing
    """

    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    raw_text: str = ""
    needs_confirmation: bool = False
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "params": self.params,
            "confidence": self.confidence,
            "raw_text": self.raw_text,
            "needs_confirmation": self.needs_confirmation,
            "explanation": self.explanation,
        }


# ---------------------------------------------------------------------------
# Pattern-based intent parser (simple MVP version)
# ---------------------------------------------------------------------------


# Chinese patterns for common building operations
WALL_PATTERNS = [
    # "建一面5米长的墙" / "创建一面墙" / "添加墙体"
    re.compile(r"(?:建|创建|添加|画|绘制|make|create|add|build).{0,10}(?:墙|墙体|wall)", re.I | re.U),
    re.compile(r"(?:墙|墙体|wall).{0,10}(?:建|创建|添加|画|绘制|create|add|build)", re.I | re.U),
    re.compile(r"(?:create|add|build|make)\s+(?:a\s+)?(?:\d+\s*(?:meter|m|米)\s+)?wall", re.I),
]

ROOM_PATTERNS = [
    # "建一个会议室" / "创建房间" / "添加一个卧室"
    re.compile(r"(?:建|创建|添加|设计|create|add|build|make).{0,15}(?:房间|room|会议室|卧室|客厅|厨房|卫生间|办公室|meeting|bedroom|office|kitchen|bathroom)", re.I | re.U),
    re.compile(r"(?:房间|会议室|卧室|客厅|厨房|卫生间|办公室|room|meeting|bedroom|office).{0,10}(?:建|创建|添加|create|add|build)", re.I | re.U),
    re.compile(r"(?:create|add|build|make)\s+(?:a\s+)?(?:room|会议室|卧室|客厅|厨房|卫生间|办公室|meeting\s*room|bedroom|office)", re.I),
]

DELETE_PATTERNS = [
    re.compile(r"(?:删除|移除|去掉|拆掉).{0,5}(?:墙|门|窗|房间)", re.I),
    re.compile(r"(?:delete|remove).{0,5}(?:wall|door|window|room)", re.I),
]

# Dimension extraction patterns
DIMENSION_PATTERNS = {
    "length": re.compile(r"(\d+(?:\.\d+)?)\s*(?:米|m|meter)", re.I),
    "width": re.compile(r"(?:宽|width)\s*(\d+(?:\.\d+)?)\s*(?:米|m)", re.I),
    "height": re.compile(r"(?:高|height)\s*(\d+(?:\.\d+)?)\s*(?:米|m)", re.I),
    "area": re.compile(r"(\d+(?:\.\d+)?)\s*(?:平方|平米|sqm)", re.I),
}

# Floor/level patterns
LEVEL_PATTERNS = [
    re.compile(r"(?:在|第)?(\d+)\s*(?:楼|层|floor|level)", re.I),
    re.compile(r"(?:floor|level)\s*(\d+)", re.I),
]

# Room type patterns
ROOM_TYPE_MAP = {
    "会议室": "meeting",
    "meeting": "meeting",
    "卧室": "bedroom",
    "bedroom": "bedroom",
    "客厅": "living_room",
    "living": "living_room",
    "厨房": "kitchen",
    "kitchen": "kitchen",
    "卫生间": "bathroom",
    "bathroom": "bathroom",
    "办公室": "office",
    "office": "office",
    "走廊": "corridor",
    "corridor": "corridor",
}


class IntentParser:
    """Parse natural language into building intents.

    This is a simple pattern-based parser for the MVP.
    For production, this should use an LLM for more robust parsing.
    """

    def __init__(self):
        self.wall_patterns = WALL_PATTERNS
        self.room_patterns = ROOM_PATTERNS
        self.delete_patterns = DELETE_PATTERNS
        self.dimension_patterns = DIMENSION_PATTERNS
        self.level_patterns = LEVEL_PATTERNS

    def parse(self, text: str) -> Optional[BuildingIntent]:
        """Parse natural language text into a building intent.

        Args:
            text: User's natural language input

        Returns:
            BuildingIntent if parsed successfully, None otherwise
        """
        text = text.strip()
        if not text:
            return None

        # Try to identify the action
        action = self._detect_action(text)

        if action == "create_wall":
            return self._parse_wall_intent(text)
        elif action == "create_room":
            return self._parse_room_intent(text)
        elif action == "delete":
            return self._parse_delete_intent(text)
        elif action == "query":
            return self._parse_query_intent(text)

        # Unknown intent - return with low confidence
        return BuildingIntent(
            action="unknown",
            raw_text=text,
            confidence=0.0,
            explanation="I couldn't understand the building operation. Try: '建一面5米长的墙' or 'create a wall'",
        )

    def _detect_action(self, text: str) -> Optional[str]:
        """Detect the action from text."""
        # Check for delete first (more specific)
        for pattern in self.delete_patterns:
            if pattern.search(text):
                return "delete"

        # Check for wall creation
        for pattern in self.wall_patterns:
            if pattern.search(text):
                return "create_wall"

        # Check for room creation
        for pattern in self.room_patterns:
            if pattern.search(text):
                return "create_room"

        # Check for query patterns
        query_keywords = ["查看", "列出", "显示", "list", "show", "what", "how many"]
        for keyword in query_keywords:
            if keyword.lower() in text.lower():
                return "query"

        return None

    def _parse_wall_intent(self, text: str) -> BuildingIntent:
        """Parse a wall creation intent."""
        params: Dict[str, Any] = {}

        # Extract length
        length_match = self.dimension_patterns["length"].search(text)
        if length_match:
            length_m = float(length_match.group(1))
            params["length_mm"] = length_m * 1000  # Convert to mm
        else:
            # Default: 5 meters
            params["length_mm"] = 5000

        # Extract height
        height_match = self.dimension_patterns["height"].search(text)
        if height_match:
            height_m = float(height_match.group(1))
            params["height_mm"] = height_m * 1000
        else:
            # Default: 3 meters
            params["height_mm"] = 3000

        # Extract level
        level_match = None
        for pattern in self.level_patterns:
            level_match = pattern.search(text)
            if level_match:
                break

        if level_match:
            floor_num = int(level_match.group(1))
            params["level"] = f"Level {floor_num}"
        else:
            params["level"] = "Level 1"

        # Default wall geometry: horizontal wall along X axis
        params["start"] = {"x": 0, "y": 0, "z": 0}
        params["end"] = {
            "x": params["length_mm"],
            "y": 0,
            "z": 0,
        }

        # Build explanation
        length_m = params["length_mm"] / 1000
        height_m = params["height_mm"] / 1000
        explanation = (
            f"Create a wall: {length_m}m long, {height_m}m high, "
            f"on {params['level']}"
        )

        return BuildingIntent(
            action="create_wall",
            params=params,
            confidence=0.8,
            raw_text=text,
            needs_confirmation=True,
            explanation=explanation,
        )

    def _parse_room_intent(self, text: str) -> BuildingIntent:
        """Parse a room creation intent."""
        params: Dict[str, Any] = {}

        # Detect room type
        room_type = "room"
        for keyword, rtype in ROOM_TYPE_MAP.items():
            if keyword in text.lower():
                room_type = rtype
                break

        params["room_type"] = room_type

        # Extract dimensions
        length_match = self.dimension_patterns["length"].search(text)
        if length_match:
            params["length_mm"] = float(length_match.group(1)) * 1000
        else:
            # Default room sizes by type
            default_sizes = {
                "meeting": {"length_mm": 4000, "width_mm": 3000},
                "bedroom": {"length_mm": 4000, "width_mm": 3500},
                "living_room": {"length_mm": 6000, "width_mm": 4000},
                "kitchen": {"length_mm": 4000, "width_mm": 3000},
                "bathroom": {"length_mm": 3000, "width_mm": 2000},
                "office": {"length_mm": 4000, "width_mm": 3000},
            }
            defaults = default_sizes.get(room_type, {"length_mm": 4000, "width_mm": 3000})
            params.update(defaults)

        width_match = self.dimension_patterns["width"].search(text)
        if width_match:
            params["width_mm"] = float(width_match.group(1)) * 1000

        # Extract level
        for pattern in self.level_patterns:
            match = pattern.search(text)
            if match:
                params["level"] = f"Level {int(match.group(1))}"
                break
        else:
            params["level"] = "Level 1"

        explanation = (
            f"Create a {room_type}: "
            f"{params.get('length_mm', 4000)/1000}m x {params.get('width_mm', 3000)/1000}m, "
            f"on {params['level']}"
        )

        return BuildingIntent(
            action="create_room",
            params=params,
            confidence=0.7,
            raw_text=text,
            needs_confirmation=True,
            explanation=explanation,
        )

    def _parse_delete_intent(self, text: str) -> BuildingIntent:
        """Parse a delete intent."""
        params: Dict[str, Any] = {}

        # Try to extract element ID
        id_match = re.search(r"(?:id|#|编号)\s*(\d+)", text, re.I)
        if id_match:
            params["element_id"] = int(id_match.group(1))

        # Detect element type
        if "墙" in text or "wall" in text.lower():
            params["element_type"] = "wall"
        elif "门" in text or "door" in text.lower():
            params["element_type"] = "door"
        elif "窗" in text or "window" in text.lower():
            params["element_type"] = "window"
        elif "房间" in text or "room" in text.lower():
            params["element_type"] = "room"

        return BuildingIntent(
            action="delete",
            params=params,
            confidence=0.6 if "element_id" in params else 0.3,
            raw_text=text,
            needs_confirmation=True,
            explanation=f"Delete {params.get('element_type', 'element')}" +
                        (f" (ID: {params['element_id']})" if "element_id" in params else ""),
        )

    def _parse_query_intent(self, text: str) -> BuildingIntent:
        """Parse a query intent."""
        params: Dict[str, Any] = {}

        text_lower = text.lower()

        if "墙" in text or "wall" in text_lower:
            params["query_type"] = "walls"
        elif "房间" in text or "room" in text_lower:
            params["query_type"] = "rooms"
        elif "层" in text or "floor" in text_lower or "level" in text_lower:
            params["query_type"] = "levels"
        elif "模型" in text or "model" in text_lower:
            params["query_type"] = "model"
        else:
            params["query_type"] = "model"

        return BuildingIntent(
            action="query",
            params=params,
            confidence=0.9,
            raw_text=text,
            needs_confirmation=False,
            explanation=f"Query {params['query_type']}",
        )


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


def parse_intent(text: str) -> Optional[BuildingIntent]:
    """Parse natural language into a building intent.

    Args:
        text: User's natural language input

    Returns:
        BuildingIntent or None
    """
    parser = IntentParser()
    return parser.parse(text)
