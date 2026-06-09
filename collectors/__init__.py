"""Job source collectors."""

from collectors.ashby import AshbyCollector
from collectors.greenhouse import GreenhouseCollector
from collectors.html_page import HtmlPageCollector
from collectors.lever import LeverCollector


COLLECTORS = {
    "ashby": AshbyCollector,
    "greenhouse": GreenhouseCollector,
    "html": HtmlPageCollector,
    "lever": LeverCollector,
}


def create_collector(source_config, rate_limiter, request_settings):
    source_type = str(source_config.get("type", "")).casefold()
    try:
        collector_class = COLLECTORS[source_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported source type: {source_type}") from exc
    return collector_class(source_config, rate_limiter, request_settings)

