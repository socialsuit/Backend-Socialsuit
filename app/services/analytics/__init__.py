# Analytics package initialization

# Import main classes for easier access
from app.services.analytics.data_collector import AnalyticsCollector
from app.services.analytics.data_analyzer import AnalyticsAnalyzer
from app.services.analytics.chart_generator import ChartGenerator

# Import services subpackage
from app.services.analytics.services import collect_all_platform_data, AnalyticsCollectorService, AnalyticsAnalyzerService, ChartGeneratorService