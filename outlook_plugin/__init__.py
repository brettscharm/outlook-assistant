"""
Outlook Assistant Plugin
Seamlessly read emails and upcoming calendar events from Microsoft Outlook.
"""

from .mac_bridge import MacOutlookBridge
from .graph_bridge import GraphOutlookBridge
from .engine import OutlookEngine

__version__ = "2.17.4"
__all__ = ["MacOutlookBridge", "GraphOutlookBridge", "OutlookEngine"]
