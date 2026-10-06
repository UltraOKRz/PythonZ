# UI Frames Module
from .base import BaseUIFrame
from .frame_title import TitleFrame
from .frame_map import MapBannerFrame
from .frame_timer import TimerFrame
from .frame_wallet import WalletFrame
from .frame_badges import BadgesFrame
from .frame_boost import BoostTopFrame
from .frame_safe import SafeZoneFrame
from .frame_pool import PoolInfoFrame
from .frame_hot import HotFarmFrame
from .frame_footer import StatusFooterFrame

__all__ = [
    "BaseUIFrame",
    "TitleFrame",
    "MapBannerFrame",
    "TimerFrame",
    "WalletFrame",
    "BadgesFrame",
    "BoostTopFrame",
    "SafeZoneFrame",
    "PoolInfoFrame",
    "HotFarmFrame",
    "StatusFooterFrame"
]
