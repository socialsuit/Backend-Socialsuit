from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import json

from app.services.analytics.data_analyzer import AnalyticsAnalyzer
from app.services.utils.logger_config import setup_logger

# Set up logger
logger = setup_logger("chart_generator")

class ChartGenerator:
    """Generates chart data for frontend visualization"""
    
    def __init__(self):
        self.analyzer = AnalyticsAnalyzer()
    
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
            if metric == "engagement_rate":
                chart_data = self._format_comparison_for_chartjs(
                    comparative_data["engagement_comparison"]["rates"], "Engagement Rate (%)"
                )
            elif metric == "growth_rate":
                chart_data = self._format_comparison_for_chartjs(
                    comparative_data["growth_comparison"]["rates"], "Follower Growth Rate (%)"
                )
            elif metric == "followers":
                followers_data = {p: m["current_followers"] for p, m in comparative_data["platform_metrics"].items()}
                chart_data = self._format_comparison_for_chartjs(followers_data, "Followers")
            elif metric == "total_engagement":
                engagement_data = {p: m["total_engagements"] for p, m in comparative_data["platform_metrics"].items()}
                chart_data = self._format_comparison_for_chartjs(engagement_data, "Total Engagements")
            else:
                return {"error": f"Unsupported metric for platform comparison: {metric}"}
            
            return {
                "chart_type": "bar",
                "title": f"Platform Comparison: {metric.replace('_', ' ').title()}",
                "data": chart_data,
                "options": self._get_comparison_options(metric)
            }
            
        except Exception as e:
            logger.error(f"Error generating platform comparison chart for {user_id}, metric {metric}: {str(e)}")
            return {"error": str(e)}
    
    def generate_engagement_breakdown_chart(self, user_id: str, platform: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """Generate engagement breakdown chart data"""
        try:
            # If platform is specified, get platform insights, otherwise get user overview
            if platform:
                data = self.analyzer.get_platform_insights(user_id, platform, days)
                if "error" in data:
                    return data
                breakdown = data["engagement_breakdown"]
            else:
                # Get data for all platforms and combine
                platforms = self.analyzer._get_user_platforms(user_id)
                breakdown = {}
                for p in platforms:
                    platform_data = self.analyzer.get_platform_insights(user_id, p, days)
                    if "error" not in platform_data:
                        for engagement_type, count in platform_data["engagement_breakdown"].items():
                            breakdown[engagement_type] = breakdown.get(engagement_type, 0) + count
            
            # Format for chart.js
            chart_data = self._format_breakdown_for_chartjs(breakdown)
            
            title = f"Engagement Breakdown{f' - {platform}' if platform else ''}" 
            
            return {
                "chart_type": "pie",
                "title": title,
                "data": chart_data,
                "options": self._get_pie_chart_options()
            }
            
        except Exception as e:
            logger.error(f"Error generating engagement breakdown chart for {user_id}: {str(e)}")
            return {"error": str(e)}
    
    def generate_content_performance_chart(self, user_id: str, platform: str, days: int = 30, 
                                         metric: str = "engagement_rate", limit: int = 10) -> Dict[str, Any]:
        """Generate content performance chart data"""
        try:
            # Get platform insights
            data = self.analyzer.get_platform_insights(user_id, platform, days)
            
            if "error" in data:
                return data
            
            # Get content performance data
            content_data = data["content_performance"]
            
            # Sort by the specified metric
            sorted_content = sorted(content_data, key=lambda x: x.get(metric, 0), reverse=True)[:limit]
            
            # Format for chart.js
            chart_data = self._format_content_performance_for_chartjs(sorted_content, metric)
            
            return {
                "chart_type": "bar",
                "title": f"Top Content by {metric.replace('_', ' ').title()} - {platform}",
                "data": chart_data,
                "options": self._get_content_performance_options(metric)
            }
            
        except Exception as e:
            logger.error(f"Error generating content performance chart for {user_id}, platform {platform}: {str(e)}")
            return {"error": str(e)}
    
    def generate_best_times_chart(self, user_id: str, platform: str, days: int = 30) -> Dict[str, Any]:
        """Generate best posting times chart data"""
        try:
            # Get platform insights
            data = self.analyzer.get_platform_insights(user_id, platform, days)
            
            if "error" in data:
                return data
            
            # Get best posting times data
            best_times_data = data["best_posting_times"]
            
            # Format for chart.js
            days_chart = self._format_best_days_for_chartjs(best_times_data["days"])
            hours_chart = self._format_best_hours_for_chartjs(best_times_data["hours"])
            
            return {
                "days": {
                    "chart_type": "bar",
                    "title": f"Best Days to Post - {platform}",
                    "data": days_chart,
                    "options": self._get_best_times_options("days")
                },
                "hours": {
                    "chart_type": "bar",
                    "title": f"Best Times to Post - {platform}",
                    "data": hours_chart,
                    "options": self._get_best_times_options("hours")
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating best times chart for {user_id}, platform {platform}: {str(e)}")
            return {"error": str(e)}
    
    def generate_content_type_chart(self, user_id: str, platform: str, days: int = 30) -> Dict[str, Any]:
        """Generate content type performance chart data"""
        try:
            # Get platform insights
            data = self.analyzer.get_platform_insights(user_id, platform, days)
            
            if "error" in data:
                return data
            
            # Get content type performance data
            content_type_data = data["content_type_performance"]
            
            # Format for chart.js
            chart_data = self._format_content_type_for_chartjs(content_type_data)
            
            return {
                "chart_type": "radar",
                "title": f"Content Type Performance - {platform}",
                "data": chart_data,
                "options": self._get_radar_chart_options()
            }
            
        except Exception as e:
            logger.error(f"Error generating content type chart for {user_id}, platform {platform}: {str(e)}")
            return {"error": str(e)}
    
    def generate_dashboard_charts(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Generate a set of charts for the dashboard"""
        try:
            # Get user overview
            overview = self.analyzer.get_user_overview(user_id, days)
            
            if "error" in overview:
                return overview
            
            # Generate charts
            charts = {
                "follower_growth": self.generate_time_series_chart(user_id, "followers", None, days),
                "engagement_rate": self.generate_time_series_chart(user_id, "engagement_rate", None, days),
                "platform_comparison": self.generate_platform_comparison_chart(user_id, "engagement_rate", days),
                "engagement_breakdown": self.generate_engagement_breakdown_chart(user_id, None, days)
            }
            
            # Add platform-specific charts for the primary platform
            platforms = self.analyzer._get_user_platforms(user_id)
            if platforms:
                primary_platform = platforms[0]  # Use first platform as primary
                charts["content_performance"] = self.generate_content_performance_chart(user_id, primary_platform, days)
                charts["best_times"] = self.generate_best_times_chart(user_id, primary_platform, days)
            
            return {
                "user_id": user_id,
                "time_period": f"Last {days} days",
                "charts": charts,
                "overview_metrics": {
                    "total_followers": overview["total_followers"],
                    "total_engagement": overview["total_engagement"],
                    "average_engagement_rate": overview["average_engagement_rate"]
                },
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating dashboard charts for {user_id}: {str(e)}")
            return {"error": str(e)}
    
    # Helper methods for formatting chart data
    def _format_time_series_for_chartjs(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format time series data for Chart.js"""
        labels = []
        datasets = []
        
        # Define colors for each platform
        platform_colors = {
            "facebook": "rgba(59, 89, 152, 0.7)",  # Facebook blue
            "instagram": "rgba(193, 53, 132, 0.7)",  # Instagram pink/purple
            "twitter": "rgba(29, 161, 242, 0.7)",  # Twitter blue
            "linkedin": "rgba(0, 119, 181, 0.7)",  # LinkedIn blue
            "tiktok": "rgba(0, 0, 0, 0.7)"  # TikTok black
        }
        
        # Process each platform's data
        for platform, data in raw_data["data"].items():
            # Extract dates for labels (use the first platform's dates)
            if not labels and data:
                labels = [item["date"] for item in data]
            
            # Create dataset for this platform
            datasets.append({
                "label": platform.capitalize(),
                "data": [item["value"] for item in data],
                "backgroundColor": platform_colors.get(platform, "rgba(75, 192, 192, 0.7)"),
                "borderColor": platform_colors.get(platform, "rgba(75, 192, 192, 1)").replace("0.7", "1"),
                "borderWidth": 2,
                "fill": False,
                "tension": 0.1  # Slight curve for line charts
            })
        
        return {
            "labels": labels,
            "datasets": datasets
        }
    
    def _format_comparison_for_chartjs(self, data: Dict[str, Union[float, int]], label: str) -> Dict[str, Any]:
        """Format comparison data for Chart.js"""
        labels = list(data.keys())
        values = list(data.values())
        
        # Define colors for each platform
        colors = [
            "rgba(59, 89, 152, 0.7)",  # Facebook blue
            "rgba(193, 53, 132, 0.7)",  # Instagram pink/purple
            "rgba(29, 161, 242, 0.7)",  # Twitter blue
            "rgba(0, 119, 181, 0.7)",  # LinkedIn blue
            "rgba(0, 0, 0, 0.7)"  # TikTok black
        ]
        
        # Ensure we have enough colors
        while len(colors) < len(labels):
            colors.append(f"rgba({hash(labels[len(colors)]) % 255}, {hash(labels[len(colors)]+"1") % 255}, {hash(labels[len(colors)]+"2") % 255}, 0.7)")
        
        return {
            "labels": [l.capitalize() for l in labels],
            "datasets": [{
                "label": label,
                "data": values,
                "backgroundColor": colors[:len(labels)],
                "borderColor": [c.replace("0.7", "1") for c in colors[:len(labels)]],
                "borderWidth": 1
            }]
        }
    
    def _format_breakdown_for_chartjs(self, breakdown: Dict[str, int]) -> Dict[str, Any]:
        """Format engagement breakdown data for Chart.js"""
        labels = list(breakdown.keys())
        values = list(breakdown.values())
        
        # Define colors for each engagement type
        colors = [
            "rgba(255, 99, 132, 0.7)",   # Red
            "rgba(54, 162, 235, 0.7)",  # Blue
            "rgba(255, 206, 86, 0.7)",  # Yellow
            "rgba(75, 192, 192, 0.7)",  # Green
            "rgba(153, 102, 255, 0.7)", # Purple
            "rgba(255, 159, 64, 0.7)",  # Orange
            "rgba(199, 199, 199, 0.7)"  # Gray
        ]
        
        # Ensure we have enough colors
        while len(colors) < len(labels):
            colors.append(f"rgba({hash(labels[len(colors)]) % 255}, {hash(labels[len(colors)]+"1") % 255}, {hash(labels[len(colors)]+"2") % 255}, 0.7)")
        
        return {
            "labels": [l.capitalize() for l in labels],
            "datasets": [{
                "data": values,
                "backgroundColor": colors[:len(labels)],
                "borderColor": [c.replace("0.7", "1") for c in colors[:len(labels)]],
                "borderWidth": 1
            }]
        }
    
    def _format_content_performance_for_chartjs(self, content_data: List[Dict[str, Any]], metric: str) -> Dict[str, Any]:
        """Format content performance data for Chart.js"""
        # Truncate post IDs for readability
        labels = [self._truncate_post_id(item["post_id"]) for item in content_data]
        values = [item.get(metric, 0) for item in content_data]
        
        return {
            "labels": labels,
            "datasets": [{
                "label": metric.replace("_", " ").title(),
                "data": values,
                "backgroundColor": "rgba(75, 192, 192, 0.7)",
                "borderColor": "rgba(75, 192, 192, 1)",
                "borderWidth": 1
            }]
        }
    
    def _format_best_days_for_chartjs(self, days_data: Dict[str, float]) -> Dict[str, Any]:
        """Format best days data for Chart.js"""
        labels = list(days_data.keys())
        values = list(days_data.values())
        
        return {
            "labels": [l.capitalize() for l in labels],
            "datasets": [{
                "label": "Engagement Score",
                "data": values,
                "backgroundColor": "rgba(54, 162, 235, 0.7)",
                "borderColor": "rgba(54, 162, 235, 1)",
                "borderWidth": 1
            }]
        }
    
    def _format_best_hours_for_chartjs(self, hours_data: Dict[str, float]) -> Dict[str, Any]:
        """Format best hours data for Chart.js"""
        labels = list(hours_data.keys())
        values = list(hours_data.values())
        
        return {
            "labels": [l.capitalize() for l in labels],
            "datasets": [{
                "label": "Engagement Score",
                "data": values,
                "backgroundColor": "rgba(255, 159, 64, 0.7)",
                "borderColor": "rgba(255, 159, 64, 1)",
                "borderWidth": 1
            }]
        }
    
    def _format_content_type_for_chartjs(self, content_type_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Format content type data for Chart.js radar chart"""
        labels = list(content_type_data.keys())
        engagement_values = [content_type_data[ct]["avg_engagement_rate"] for ct in labels]
        impression_values = [content_type_data[ct]["avg_impressions"] / 1000 for ct in labels]  # Scale down for readability
        
        return {
            "labels": [l.capitalize() for l in labels],
            "datasets": [
                {
                    "label": "Engagement Rate (%)",
                    "data": engagement_values,
                    "backgroundColor": "rgba(255, 99, 132, 0.2)",
                    "borderColor": "rgba(255, 99, 132, 1)",
                    "pointBackgroundColor": "rgba(255, 99, 132, 1)",
                    "pointBorderColor": "#fff",
                    "pointHoverBackgroundColor": "#fff",
                    "pointHoverBorderColor": "rgba(255, 99, 132, 1)"
                },
                {
                    "label": "Avg Impressions (K)",
                    "data": impression_values,
                    "backgroundColor": "rgba(54, 162, 235, 0.2)",
                    "borderColor": "rgba(54, 162, 235, 1)",
                    "pointBackgroundColor": "rgba(54, 162, 235, 1)",
                    "pointBorderColor": "#fff",
                    "pointHoverBackgroundColor": "#fff",
                    "pointHoverBorderColor": "rgba(54, 162, 235, 1)"
                }
            ]
        }
    
    # Helper methods for chart options
    def _get_time_series_options(self, metric: str) -> Dict[str, Any]:
        """Get options for time series charts"""
        return {
            "responsive": True,
            "maintainAspectRatio": False,
            "scales": {
                "y": {
                    "beginAtZero": True,
                    "title": {
                        "display": True,
                        "text": metric.replace("_", " ").title()
                    }
                },
                "x": {
                    "title": {
                        "display": True,
                        "text": "Date"
                    }
                }
            },
            "plugins": {
                "tooltip": {
                    "mode": "index",
                    "intersect": False
                },
                "legend": {
                    "position": "top"
                },
                "title": {
                    "display": True,
                    "text": f"{metric.replace('_', ' ').title()} Over Time"
                }
            }
        }
    
    def _get_comparison_options(self, metric: str) -> Dict[str, Any]:
        """Get options for comparison charts"""
        return {
            "responsive": True,
            "maintainAspectRatio": False,
            "scales": {
                "y": {
                    "beginAtZero": True,
                    "title": {
                        "display": True,
                        "text": metric.replace("_", " ").title()
                    }
                }
            },
            "plugins": {
                "legend": {
                    "position": "top"
                },
                "title": {
                    "display": True,
                    "text": f"Platform Comparison: {metric.replace('_', ' ').title()}"
                }
            }
        }
    
    def _get_pie_chart_options(self) -> Dict[str, Any]:
        """Get options for pie charts"""
        return {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {
                    "position": "right"
                },
                "tooltip": {
                    "callbacks": {
                        "label": "function(context) { return context.label + ': ' + context.raw + ' (' + Math.round(context.parsed / context.chart.data.datasets[0].data.reduce((a,b) => a+b, 0) * 100) + '%)'; }"
                    }
                }
            }
        }
    
    def _get_content_performance_options(self, metric: str) -> Dict[str, Any]:
        """Get options for content performance charts"""
        return {
            "responsive": True,
            "maintainAspectRatio": False,
            "indexAxis": "y",  # Horizontal bar chart
            "scales": {
                "x": {
                    "beginAtZero": True,
                    "title": {
                        "display": True,
                        "text": metric.replace("_", " ").title()
                    }
                }
            },
            "plugins": {
                "legend": {
                    "display": False
                },
                "tooltip": {
                    "callbacks": {
                        "title": "function(context) { return 'Post ID: ' + context[0].label; }"
                    }
                }
            }
        }
    
    def _get_best_times_options(self, type_: str) -> Dict[str, Any]:
        """Get options for best times charts"""
        return {
            "responsive": True,
            "maintainAspectRatio": False,
            "scales": {
                "y": {
                    "beginAtZero": True,
                    "max": 1,
                    "title": {
                        "display": True,
                        "text": "Engagement Score"
                    }
                }
            },
            "plugins": {
                "legend": {
                    "display": False
                },
                "title": {
                    "display": True,
                    "text": f"Best {type_.capitalize()} to Post"
                }
            }
        }
    
    def _get_radar_chart_options(self) -> Dict[str, Any]:
        """Get options for radar charts"""
        return {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {
                    "position": "top"
                },
                "title": {
                    "display": True,
                    "text": "Content Type Performance"
                }
            },
            "scales": {
                "r": {
                    "angleLines": {
                        "display": True
                    },
                    "suggestedMin": 0
                }
            }
        }
    
    def _truncate_post_id(self, post_id: str, max_length: int = 10) -> str:
        """Truncate post ID for readability in charts"""
        if len(post_id) <= max_length:
            return post_id
        return post_id[:max_length] + "..."