"""Read-only Scryer access using an explicit endpoint and API key.

Use ScryerClient as a context manager, then call get_version, list_titles and
list_media_requests. Queries target Scryer v0.19.12; no live version is assumed.
"""

from .client import ScryerClient as ScryerClient
from .client import ScryerError as ScryerError
from .media import get_version as get_version
from .media import list_media_requests as list_media_requests
from .media import list_titles as list_titles
from .models import Collection as Collection
from .models import Episode as Episode
from .models import EpisodeAvailability as EpisodeAvailability
from .models import ExternalId as ExternalId
from .models import Facet as Facet
from .models import MediaFile as MediaFile
from .models import MediaRequest as MediaRequest
from .models import MonitorType as MonitorType
from .models import RequestStatus as RequestStatus
from .models import ScryerModel as ScryerModel
from .models import SeriesMovieLink as SeriesMovieLink
from .models import Title as Title
