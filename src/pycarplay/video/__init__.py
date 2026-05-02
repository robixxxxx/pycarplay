"""Video decoding and display"""

from ..logging_utils import get_module_logger


LOGGER = get_module_logger(__name__)

from .video_decoder import VideoDecoder
from .video_provider import VideoFrameProvider

__all__ = ['VideoDecoder', 'VideoFrameProvider']
