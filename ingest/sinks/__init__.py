from ingest.sinks.base import Sink
from ingest.sinks.composite_sink import CompositeSink
from ingest.sinks.log_sink import LogSink
from ingest.sinks.metricgraph_sink import MetricGraphSink
from ingest.sinks.webhook_sink import WebhookSink

__all__ = ["Sink", "LogSink", "MetricGraphSink", "WebhookSink", "CompositeSink"]
