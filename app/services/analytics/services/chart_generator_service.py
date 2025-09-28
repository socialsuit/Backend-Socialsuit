from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import json

from app.services.analytics.services.data_analyzer_service import AnalyticsAnalyzerService
from app.services.utils.logger_config import setup_logger

# Set up logger
logger = setup_logger("chart_generator_service")

class ChartGeneratorService:
    """Generates chart data for frontend visualization"""
    
    def __init__(self, analyzer: AnalyticsAnalyzerService):
        self.analyzer = analyzer
    
    def generate_time_series_chart(self, user_id: str, metric: str, platform: Optional[str] = None, 
                                  days: int = 30, group_by: str = "day") -> Dict[str, Any]:
        """Generate time series chart data"""
        try:
            # Get raw data from analyzer
            raw_data = self.analyzer.get_chart_data(user_id, metric, platform, days, group_by)
            
            if "error" in raw_data:
                return raw_data
            
            # Format for chart.js
            chart_data = self._format_time_series_for_chartjs(raw_data)
            
            return {
                "chart_type": "line",
                "title": f"{metric.capitalize()} over time",
                "data": chart_data,
                "options": self._get_time_series_options(metric)
            }
            
        except Exception as e:
            logger.error(f"Error generating time series chart for {user_id}, metric {metric}: {str(e)}")
            return {"error": str(e)}
    
    def generate_platform_comparison_chart(self, user_id: str, metric: str, days: int = 30) -> Dict[str, Any]:
        """Generate platform comparison chart data"""
        try:
            # Get comparative analytics
            comparative_data = self.analyzer.get_comparative_analytics(user_id, days)
            
            if "error" in comparative_data:
                return comparative_data
            
            # Format for chart.js based on metric
            chart_data = self._format_platform_comparison_for_chartjs(comparative_data, metric)
            
            return {
                "chart_type": "bar",
                "title": f"{metric.capitalize()} by platform",
                "data": chart_data,
                "options": self._get_platform_comparison_options(metric)
            }
            
        except Exception as e:
            logger.error(f"Error generating platform comparison chart for {user_id}, metric {metric}: {str(e)}")
            return {"error": str(e)}
    
    def generate_engagement_breakdown_chart(self, user_id: str, platform: Optional[str] = None, 
                                           days: int = 30) -> Dict[str, Any]:
        """Generate engagement breakdown chart data"""
        try:
            # Get engagement breakdown
            engagement_data = self.analyzer.get_engagement_breakdown(user_id, platform, days)
            
            if "error" in engagement_data:
                return engagement_data
            
            # Format for chart.js
            chart_data = self._format_engagement_breakdown_for_chartjs(engagement_data)
            
            return {
                "chart_type": "pie",
                "title": "Engagement breakdown",
                "data": chart_data,
                "options": self._get_engagement_breakdown_options()
            }
            
        except Exception as e:
            logger.error(f"Error generating engagement breakdown chart for {user_id}: {str(e)}")
            return {"error": str(e)}
    
    def generate_content_performance_chart(self, user_id: str, days: int = 30, 
                                          limit: int = 5) -> Dict[str, Any]:
        """Generate content performance chart data"""
        try:
            # Get top performing content
            content_data = self.analyzer.get_top_performing_content(user_id, days, limit)
            
            if "error" in content_data:
                return content_data
            
            # Format for chart.js
            chart_data = self._format_content_performance_for_chartjs(content_data)
            
            return {
                "chart_type": "horizontalBar",
                "title": "Top performing content",
                "data": chart_data,
                "options": self._get_content_performance_options()
            }
            
        except Exception as e:
            logger.error(f"Error generating content performance chart for {user_id}: {str(e)}")
            return {"error": str(e)}
    
    # Helper methods for formatting chart data
    def _format_time_series_for_chartjs(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format time series data for Chart.js"""
        labels = [item["date"] for item in data["data"]]
        datasets = [{
            "label": data["metric"],
            "data": [item["value"] for item in data["data"]],
            "borderColor": "#4A6FFF",
            "backgroundColor": "rgba(74, 111, 255, 0.1)",
            "fill": True,
            "tension": 0.4
        }]
        
        return {
            "labels": labels,
            "datasets": datasets
        }
    
    def _format_platform_comparison_for_chartjs(self, data: Dict[str, Any], metric: str) -> Dict[str, Any]:
        """Format platform comparison data for Chart.js"""
        platforms = list(data["platforms"].keys())
        values = [data["platforms"][platform].get(metric, 0) for platform in platforms]
        
        # Platform-specific colors
        colors = {
            "facebook": "#4267B2",
            "instagram": "#C13584",
            "twitter": "#1DA1F2",
            "linkedin": "#0077B5",
            "youtube": "#FF0000",
            "tiktok": "#000000"
        }
        
        background_colors = [colors.get(platform, "#CCCCCC") for platform in platforms]
        
        return {
            "labels": platforms,
            "datasets": [{
                "label": metric,
                "data": values,
                "backgroundColor": background_colors
            }]
        }
    
    def _format_engagement_breakdown_for_chartjs(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format engagement breakdown data for Chart.js"""
        engagement_types = list(data["breakdown"].keys())
        values = [data["breakdown"][engagement_type] for engagement_type in engagement_types]
        
        # Engagement type colors
        colors = [
            "#FF6384",
            "#36A2EB",
            "#FFCE56",
            "#4BC0C0",
            "#9966FF",
            "#FF9F40"
        ]
        
        return {
            "labels": engagement_types,
            "datasets": [{
                "data": values,
                "backgroundColor": colors[:len(engagement_types)]
            }]
        }
    
    def _format_content_performance_for_chartjs(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Format content performance data for Chart.js"""
        labels = [f"{item['platform']} - {item['content_type']}" for item in data]
        values = [item["engagement_score"] for item in data]
        
        # Platform-specific colors
        colors = {
            "facebook": "#4267B2",
            "instagram": "#C13584",
            "twitter": "#1DA1F2",
            "linkedin": "#0077B5",
            "youtube": "#FF0000",
            "tiktok": "#000000"
        }
        
        background_colors = [colors.get(item["platform"], "#CCCCCC") for item in data]
        
        return {
            "labels": labels,
            "datasets": [{
                "label": "Engagement Score",
                "data": values,
                "backgroundColor": background_colors
            }]
        }
    
    # Helper methods for chart options
    def _get_time_series_options(self, metric: str) -> Dict[str, Any]:
        """Get options for time series chart"""
        return {
            "responsive": True,
            "scales": {
                "x": {
                    "title": {
                        "display": True,
                        "text": "Date"
                    }
                },
                "y": {
                    "title": {
                        "display": True,
                        "text": metric.capitalize()
                    },
                    "beginAtZero": True
                }
            }
        }
    
    def _get_platform_comparison_options(self, metric: str) -> Dict[str, Any]:
        """Get options for platform comparison chart"""
        return {
            "responsive": True,
            "scales": {
                "y": {
                    "title": {
                        "display": True,
                        "text": metric.capitalize()
                    },
                    "beginAtZero": True
                }
            }
        }
    
    def _get_engagement_breakdown_options(self) -> Dict[str, Any]:
        """Get options for engagement breakdown chart"""
        return {
            "responsive": True,
            "plugins": {
                "legend": {
                    "position": "right"
                }
            }
        }
    
    def _get_content_performance_options(self) -> Dict[str, Any]:
        """Get options for content performance chart"""
        return {
            "responsive": True,
            "indexAxis": "y",
            "scales": {
                "x": {
                    "title": {
                        "display": True,
                        "text": "Engagement Score"
                    },
                    "beginAtZero": True
                }
            }
        }