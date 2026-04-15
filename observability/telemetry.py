# ─────────────────────────────────────────────────────────────────────────────
# Telemetry Provider
# ─────────────────────────────────────────────────────────────────────────────
# OpenTelemetry setup for distributed tracing and metrics.
# Supports Azure Monitor, Jaeger, and OTLP exporters.
# ─────────────────────────────────────────────────────────────────────────────

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# OpenTelemetry imports
try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    TracerProvider = None
    MeterProvider = None

# Configure module logger
logger = logging.getLogger(__name__)


class ExporterType(str, Enum):
    """Type of telemetry exporter."""
    CONSOLE = "console"
    OTLP = "otlp"
    AZURE_MONITOR = "azure_monitor"
    JAEGER = "jaeger"
    NONE = "none"


@dataclass
class TelemetryConfig:
    """
    Configuration for telemetry.
    
    Attributes:
        service_name: Name of this service
        exporter_type: Type of exporter to use
        otlp_endpoint: OTLP endpoint URL
        azure_connection_string: Azure Monitor connection string
        enable_tracing: Enable distributed tracing
        enable_metrics: Enable metrics collection
        sample_rate: Trace sampling rate (0.0 to 1.0)
    """
    service_name: str = "mafga-multiagent"
    exporter_type: ExporterType = ExporterType.CONSOLE
    otlp_endpoint: Optional[str] = None
    azure_connection_string: Optional[str] = None
    enable_tracing: bool = True
    enable_metrics: bool = True
    sample_rate: float = 1.0
    additional_attributes: dict = field(default_factory=dict)


class TelemetryProvider:
    """
    Provider for OpenTelemetry tracing and metrics.
    
    This provider initializes and manages OpenTelemetry components:
    - Tracer for distributed tracing
    - Meter for metrics collection
    - Exporters for sending data to backends
    
    Supported backends:
    - Console (for development/debugging)
    - OTLP (Jaeger, Tempo, Honey, etc.)
    - Azure Monitor (Azure Application Insights)
    
    Usage:
        config = TelemetryConfig(
            service_name="my-service",
            exporter_type=ExporterType.CONSOLE,
        )
        
        provider = TelemetryProvider(config)
        provider.initialize()
        
        # Get tracer/meter
        tracer = provider.get_tracer()
        meter = provider.get_meter()
    """
    
    _instance: Optional["TelemetryProvider"] = None
    
    def __init__(self, config: TelemetryConfig):
        """
        Initialize the telemetry provider.
        
        Args:
            config: Telemetry configuration
        """
        self._config = config
        self._tracer_provider: Optional[TracerProvider] = None
        self._meter_provider: Optional[MeterProvider] = None
        self._initialized = False
    
    @classmethod
    def get_instance(cls) -> Optional["TelemetryProvider"]:
        """Get the singleton instance."""
        return cls._instance
    
    def initialize(self) -> None:
        """Initialize OpenTelemetry providers and exporters."""
        if not OTEL_AVAILABLE:
            logger.warning("OpenTelemetry not available. Install opentelemetry-sdk.")
            return
        
        if self._initialized:
            logger.debug("Telemetry already initialized")
            return
        
        logger.info(f"Initializing telemetry for {self._config.service_name}")
        
        # Create resource
        resource = Resource.create({
            SERVICE_NAME: self._config.service_name,
            **self._config.additional_attributes,
        })
        
        # Initialize tracing
        if self._config.enable_tracing:
            self._init_tracing(resource)
        
        # Initialize metrics
        if self._config.enable_metrics:
            self._init_metrics(resource)
        
        self._initialized = True
        TelemetryProvider._instance = self
        
        logger.info("Telemetry initialization complete")
    
    def _init_tracing(self, resource: Resource) -> None:
        """Initialize tracing provider and exporter."""
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        
        # Create tracer provider
        self._tracer_provider = TracerProvider(resource=resource)
        
        # Add exporter based on config
        if self._config.exporter_type == ExporterType.CONSOLE:
            exporter = ConsoleSpanExporter()
            self._tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
        
        elif self._config.exporter_type == ExporterType.OTLP:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                exporter = OTLPSpanExporter(endpoint=self._config.otlp_endpoint)
                self._tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
            except ImportError:
                logger.error("OTLP exporter not available. Install opentelemetry-exporter-otlp")
        
        elif self._config.exporter_type == ExporterType.AZURE_MONITOR:
            try:
                from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
                exporter = AzureMonitorTraceExporter(
                    connection_string=self._config.azure_connection_string
                )
                self._tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
            except ImportError:
                logger.error("Azure Monitor exporter not available. Install azure-monitor-opentelemetry-exporter")
        
        # Set as global tracer provider
        trace.set_tracer_provider(self._tracer_provider)
        logger.info(f"Tracing initialized with {self._config.exporter_type.value} exporter")
    
    def _init_metrics(self, resource: Resource) -> None:
        """Initialize metrics provider and exporter."""
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
        
        readers = []
        
        if self._config.exporter_type == ExporterType.CONSOLE:
            reader = PeriodicExportingMetricReader(
                ConsoleMetricExporter(),
                export_interval_millis=60000,  # Every 60 seconds
            )
            readers.append(reader)
        
        elif self._config.exporter_type == ExporterType.OTLP:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
                reader = PeriodicExportingMetricReader(
                    OTLPMetricExporter(endpoint=self._config.otlp_endpoint),
                    export_interval_millis=60000,
                )
                readers.append(reader)
            except ImportError:
                logger.error("OTLP metric exporter not available")
        
        elif self._config.exporter_type == ExporterType.AZURE_MONITOR:
            try:
                from azure.monitor.opentelemetry.exporter import AzureMonitorMetricExporter
                reader = PeriodicExportingMetricReader(
                    AzureMonitorMetricExporter(
                        connection_string=self._config.azure_connection_string
                    ),
                    export_interval_millis=60000,
                )
                readers.append(reader)
            except ImportError:
                logger.error("Azure Monitor metric exporter not available")
        
        # Create meter provider
        self._meter_provider = MeterProvider(resource=resource, metric_readers=readers)
        
        # Set as global meter provider
        metrics.set_meter_provider(self._meter_provider)
        logger.info(f"Metrics initialized with {self._config.exporter_type.value} exporter")
    
    def get_tracer(self, name: Optional[str] = None) -> trace.Tracer:
        """
        Get a tracer instance.
        
        Args:
            name: Optional tracer name (defaults to service name)
            
        Returns:
            OpenTelemetry Tracer
        """
        if not OTEL_AVAILABLE:
            return _NoOpTracer()
        
        return trace.get_tracer(name or self._config.service_name)
    
    def get_meter(self, name: Optional[str] = None) -> metrics.Meter:
        """
        Get a meter instance.
        
        Args:
            name: Optional meter name (defaults to service name)
            
        Returns:
            OpenTelemetry Meter
        """
        if not OTEL_AVAILABLE:
            return _NoOpMeter()
        
        return metrics.get_meter(name or self._config.service_name)
    
    def shutdown(self) -> None:
        """Shutdown telemetry providers."""
        if self._tracer_provider:
            self._tracer_provider.shutdown()
        if self._meter_provider:
            self._meter_provider.shutdown()
        
        self._initialized = False
        logger.info("Telemetry shutdown complete")


# ─────────────────────────────────────────────────────────────────────────────
# Module-level convenience functions
# ─────────────────────────────────────────────────────────────────────────────

_provider: Optional[TelemetryProvider] = None


def init_telemetry(config: TelemetryConfig) -> TelemetryProvider:
    """
    Initialize telemetry with the given configuration.
    
    Args:
        config: Telemetry configuration
        
    Returns:
        Initialized TelemetryProvider
    """
    global _provider
    _provider = TelemetryProvider(config)
    _provider.initialize()
    return _provider


def get_tracer(name: Optional[str] = None) -> trace.Tracer:
    """Get a tracer instance."""
    if _provider:
        return _provider.get_tracer(name)
    
    if OTEL_AVAILABLE:
        return trace.get_tracer(name or "mafga-multiagent")
    
    return _NoOpTracer()


def get_meter(name: Optional[str] = None) -> metrics.Meter:
    """Get a meter instance."""
    if _provider:
        return _provider.get_meter(name)
    
    if OTEL_AVAILABLE:
        return metrics.get_meter(name or "mafga-multiagent")
    
    return _NoOpMeter()


# ─────────────────────────────────────────────────────────────────────────────
# No-op implementations for when OpenTelemetry is not available
# ─────────────────────────────────────────────────────────────────────────────

class _NoOpSpan:
    """No-op span for when OpenTelemetry is unavailable."""
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
    
    def set_attribute(self, key, value):
        pass
    
    def set_status(self, status):
        pass
    
    def record_exception(self, exception):
        pass
    
    def add_event(self, name, attributes=None):
        pass


class _NoOpTracer:
    """No-op tracer for when OpenTelemetry is unavailable."""
    
    def start_as_current_span(self, name, **kwargs):
        return _NoOpSpan()
    
    def start_span(self, name, **kwargs):
        return _NoOpSpan()


class _NoOpMeter:
    """No-op meter for when OpenTelemetry is unavailable."""
    
    def create_counter(self, name, **kwargs):
        return _NoOpCounter()
    
    def create_histogram(self, name, **kwargs):
        return _NoOpHistogram()
    
    def create_up_down_counter(self, name, **kwargs):
        return _NoOpCounter()


class _NoOpCounter:
    """No-op counter."""
    
    def add(self, value, attributes=None):
        pass


class _NoOpHistogram:
    """No-op histogram."""
    
    def record(self, value, attributes=None):
        pass
