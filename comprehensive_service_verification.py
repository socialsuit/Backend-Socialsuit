#!/usr/bin/env python3
"""
Comprehensive Backend Service Verification Script
=================================================

This script performs comprehensive testing of all backend services including:
- Health checks on all endpoints
- Authentication testing (email, wallet, protected routes)
- Media handling (upload, optimization, caching, transformations)
- Scheduling services (smart scheduling, post recycling)
- Analytics & reporting
- AI services (caption generation, engagement, A/B testing)
- Database connections (PostgreSQL, MongoDB, Redis, Cloudinary)
- Environment variable validation
- Performance benchmarking

Author: AI Assistant
Date: 2024
"""

import asyncio
import aiohttp
import json
import time
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Data class for storing test results."""
    service: str
    endpoint: str
    method: str
    status_code: int
    response_time: float
    success: bool
    error_message: Optional[str] = None
    response_data: Optional[Dict] = None
    headers: Optional[Dict] = None

@dataclass
class ServiceVerificationReport:
    """Complete service verification report."""
    timestamp: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    success_rate: float
    total_duration: float
    services_tested: List[str]
    test_results: List[TestResult]
    environment_check: Dict[str, Any]
    database_connections: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    recommendations: List[str]

class ComprehensiveServiceVerifier:
    """Comprehensive service verification class."""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.session = None
        self.test_results: List[TestResult] = []
        self.start_time = time.time()
        
        # Define all endpoints to test
        self.endpoints = {
            "health": [
                {"path": "/health", "method": "GET"},
                {"path": "/healthz", "method": "GET"},
                {"path": "/ping", "method": "GET"}
            ],
            "authentication": [
                {"path": "/api/v1/social-suit/auth/register", "method": "POST"},
                {"path": "/api/v1/social-suit/auth/login", "method": "POST"},
                {"path": "/api/v1/social-suit/auth/wallet/connect", "method": "POST"},
                {"path": "/api/v1/social-suit/auth/protected/profile", "method": "GET"}
            ],
            "media": [
                {"path": "/api/v1/social-suit/media/upload", "method": "POST"},
                {"path": "/api/v1/social-suit/media/optimize", "method": "POST"},
                {"path": "/api/v1/social-suit/thumbnail/generate", "method": "POST"}
            ],
            "scheduling": [
                {"path": "/api/v1/social-suit/schedule/best-times", "method": "GET"},
                {"path": "/api/v1/social-suit/schedule/list", "method": "GET"},
                {"path": "/api/v1/social-suit/recycle/posts", "method": "GET"}
            ],
            "analytics": [
                {"path": "/api/v1/social-suit/analytics/dashboard", "method": "GET"},
                {"path": "/api/v1/social-suit/analytics/reports", "method": "GET"},
                {"path": "/api/v1/social-suit/analytics/metrics", "method": "GET"}
            ],
            "ai_services": [
                {"path": "/api/v1/social-suit/content/generate", "method": "GET"},
                {"path": "/api/v1/social-suit/engage/analyze", "method": "POST"},
                {"path": "/api/v1/social-suit/ab-test/create", "method": "POST"}
            ],
            "platform_connect": [
                {"path": "/api/v1/social-suit/connect/platforms", "method": "GET"},
                {"path": "/api/v1/social-suit/callback/oauth", "method": "GET"}
            ]
        }
        
        # Test data for different services
        self.test_data = {
            'auth': {
                'register': '/api/v1/social-suit/auth/register',
                'login': '/api/v1/social-suit/auth/login',
                'protected': '/api/v1/social-suit/auth/protected'
            },
            'media': {
                'upload': '/api/v1/social-suit/media/upload',
                'delete': '/api/v1/social-suit/media/delete',
                'optimize': '/api/v1/social-suit/media/optimize'
            },
            'scheduling': {
                'best_times': '/api/v1/social-suit/schedule/best-times',
                'list': '/api/v1/social-suit/schedule',
                'update': '/api/v1/social-suit/schedule/update'
            },
            'analytics': {
                'dashboard': '/api/v1/social-suit/analytics/dashboard',
                'reports': '/api/v1/social-suit/analytics/reports',
                'metrics': '/api/v1/social-suit/analytics/metrics'
            },
            'ai_services': {
                'caption': '/api/v1/social-suit/content/generate',
                'engagement': '/api/v1/social-suit/engage/analyze',
                'ab_test': '/api/v1/social-suit/ab-test/create'
            },
            'platform_connect': {
                'platforms': '/api/v1/social-suit/connect/platforms',
                'oauth_callback': '/api/v1/social-suit/callback/oauth'
            }
        }
        
        # Environment variables to check
        self.required_env_vars = [
            "DATABASE_URL", "MONGO_URI", "REDIS_URL", "CLOUDINARY_URL",
            "JWT_SECRET", "SECRET_KEY", "CORS_ALLOW_ORIGINS"
        ]

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def test_endpoint(self, service: str, endpoint: Dict[str, str], 
                          headers: Optional[Dict] = None, 
                          data: Optional[Dict] = None) -> TestResult:
        """Test a single endpoint."""
        start_time = time.time()
        
        try:
            url = f"{self.base_url}{endpoint['path']}"
            method = endpoint['method'].upper()
            
            # Default headers
            default_headers = {"Content-Type": "application/json"}
            if headers:
                default_headers.update(headers)
            
            # Make request
            async with self.session.request(
                method=method,
                url=url,
                headers=default_headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response_time = time.time() - start_time
                response_data = None
                
                try:
                    response_data = await response.json()
                except:
                    response_data = {"text": await response.text()}
                
                success = 200 <= response.status < 400
                
                return TestResult(
                    service=service,
                    endpoint=endpoint['path'],
                    method=method,
                    status_code=response.status,
                    response_time=response_time,
                    success=success,
                    response_data=response_data,
                    headers=dict(response.headers)
                )
                
        except Exception as e:
            response_time = time.time() - start_time
            return TestResult(
                service=service,
                endpoint=endpoint['path'],
                method=endpoint['method'],
                status_code=0,
                response_time=response_time,
                success=False,
                error_message=str(e)
            )

    async def test_health_endpoints(self) -> List[TestResult]:
        """Test all health check endpoints."""
        logger.info("🏥 Testing health endpoints...")
        results = []
        
        for endpoint in self.endpoints["health"]:
            result = await self.test_endpoint("health", endpoint)
            results.append(result)
            logger.info(f"  {endpoint['path']}: {'✅' if result.success else '❌'} ({result.status_code})")
        
        return results

    async def test_authentication_endpoints(self) -> List[TestResult]:
        """Test authentication endpoints."""
        logger.info("🔐 Testing authentication endpoints...")
        results = []
        
        # Test data for authentication
        test_data = {
            "/api/v1/social-suit/auth/register": {
                "email": "test@example.com",
                "password": "testpassword123",
                "username": "testuser"
            },
            "/api/v1/social-suit/auth/login": {
                "email": "test@example.com",
                "password": "testpassword123"
            },
            "/api/v1/social-suit/auth/wallet/connect": {
                "wallet_address": "0x1234567890abcdef",
                "signature": "test_signature"
            }
        }
        
        for endpoint in self.endpoints["authentication"]:
            data = test_data.get(endpoint['path'])
            result = await self.test_endpoint("authentication", endpoint, data=data)
            results.append(result)
            logger.info(f"  {endpoint['path']}: {'✅' if result.success else '❌'} ({result.status_code})")
        
        return results

    async def test_media_endpoints(self) -> List[TestResult]:
        """Test media handling endpoints."""
        logger.info("🖼️ Testing media endpoints...")
        results = []
        
        # Test data for media endpoints
        test_data = {
            "/api/v1/social-suit/media/upload": {
                "file_type": "image",
                "file_name": "test.jpg"
            },
            "/api/v1/social-suit/media/optimize": {
                "image_url": "https://example.com/test.jpg",
                "width": 400,
                "height": 300
            },
            "/api/v1/social-suit/thumbnail/generate": {
                "video_url": "https://example.com/test.mp4"
            }
        }
        
        for endpoint in self.endpoints["media"]:
            data = test_data.get(endpoint['path'])
            result = await self.test_endpoint("media", endpoint, data=data)
            results.append(result)
            logger.info(f"  {endpoint['path']}: {'✅' if result.success else '❌'} ({result.status_code})")
        
        return results

    async def test_scheduling_endpoints(self) -> List[TestResult]:
        """Test scheduling endpoints."""
        logger.info("📅 Testing scheduling endpoints...")
        results = []
        
        # Test data for scheduling
        test_data = {
            "/api/v1/social-suit/schedule/create": {
                "content": "Test scheduled post",
                "platforms": ["twitter", "facebook"],
                "schedule_time": "2024-12-31T12:00:00Z"
            }
        }
        
        for endpoint in self.endpoints["scheduling"]:
            data = test_data.get(endpoint['path'])
            result = await self.test_endpoint("scheduling", endpoint, data=data)
            results.append(result)
            logger.info(f"  {endpoint['path']}: {'✅' if result.success else '❌'} ({result.status_code})")
        
        return results

    async def test_analytics_endpoints(self) -> List[TestResult]:
        """Test analytics endpoints."""
        logger.info("📊 Testing analytics endpoints...")
        results = []
        
        for endpoint in self.endpoints["analytics"]:
            result = await self.test_endpoint("analytics", endpoint)
            results.append(result)
            logger.info(f"  {endpoint['path']}: {'✅' if result.success else '❌'} ({result.status_code})")
        
        return results

    async def test_ai_service_endpoints(self) -> List[TestResult]:
        """Test AI service endpoints."""
        logger.info("🤖 Testing AI service endpoints...")
        results = []
        
        # Test data for AI services
        test_data = {
            "/api/v1/social-suit/content/generate": {
                "prompt": "Tech innovation and the future of work",
                "style": "casual",
                "hashtags": 5
            },
            "/api/v1/social-suit/engage/analyze": {
                "content": "Test post content",
                "platform": "twitter"
            },
            "/api/v1/social-suit/ab-test/create": {
                "variant_a": "Version A",
                "variant_b": "Version B",
                "metric": "engagement"
            }
        }
        
        for endpoint in self.endpoints["ai_services"]:
            data = test_data.get(endpoint['path'])
            result = await self.test_endpoint("ai_services", endpoint, data=data)
            results.append(result)
            logger.info(f"  {endpoint['path']}: {'✅' if result.success else '❌'} ({result.status_code})")
        
        return results

    async def test_platform_connect_endpoints(self) -> List[TestResult]:
        """Test platform connection endpoints."""
        logger.info("🔗 Testing platform connection endpoints...")
        results = []
        
        for endpoint in self.endpoints["platform_connect"]:
            result = await self.test_endpoint("platform_connect", endpoint)
            results.append(result)
            logger.info(f"  {endpoint['path']}: {'✅' if result.success else '❌'} ({result.status_code})")
        
        return results

    def check_environment_variables(self) -> Dict[str, Any]:
        """Check environment variable configuration."""
        logger.info("🔧 Checking environment variables...")
        
        # Load environment variables from .env file
        from dotenv import load_dotenv
        load_dotenv()
        
        env_check = {
            "total_vars": len(self.required_env_vars),
            "configured_vars": 0,
            "missing_vars": [],
            "configured_vars_list": [],
            "status": "unknown"
        }
        
        for var in self.required_env_vars:
            value = os.getenv(var)
            if value:
                env_check["configured_vars"] += 1
                env_check["configured_vars_list"].append(var)
                logger.info(f"  ✅ {var}: Configured")
            else:
                env_check["missing_vars"].append(var)
                logger.info(f"  ❌ {var}: Missing")
        
        # Determine overall status
        if env_check["configured_vars"] == env_check["total_vars"]:
            env_check["status"] = "all_configured"
        elif env_check["configured_vars"] > 0:
            env_check["status"] = "partially_configured"
        else:
            env_check["status"] = "none_configured"
        
        return env_check

    async def check_database_connections(self) -> Dict[str, Any]:
        """Check database connection status."""
        logger.info("🗄️ Checking database connections...")
        
        db_check = {
            "postgresql": {"status": "unknown", "details": ""},
            "mongodb": {"status": "unknown", "details": ""},
            "redis": {"status": "unknown", "details": ""},
            "cloudinary": {"status": "unknown", "details": ""}
        }
        
        # Check via health endpoint that might include DB status
        try:
            result = await self.test_endpoint("database", {"path": "/healthz", "method": "GET"})
            if result.success and result.response_data:
                # Parse response for database status
                db_check["overall_health"] = result.response_data
        except Exception as e:
            logger.error(f"Failed to check database connections: {e}")
        
        return db_check

    def calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics from test results."""
        if not self.test_results:
            return {}
        
        response_times = [r.response_time for r in self.test_results if r.success]
        
        if not response_times:
            return {"error": "No successful requests to analyze"}
        
        return {
            "average_response_time": sum(response_times) / len(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "total_requests": len(self.test_results),
            "successful_requests": len([r for r in self.test_results if r.success]),
            "failed_requests": len([r for r in self.test_results if not r.success])
        }

    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        # Analyze failed tests
        failed_tests = [r for r in self.test_results if not r.success]
        if failed_tests:
            recommendations.append(f"Fix {len(failed_tests)} failed endpoint(s)")
        
        # Analyze response times
        slow_tests = [r for r in self.test_results if r.success and r.response_time > 2.0]
        if slow_tests:
            recommendations.append(f"Optimize {len(slow_tests)} slow endpoint(s) (>2s response time)")
        
        # Check for missing authentication
        auth_failures = [r for r in self.test_results if r.service == "authentication" and not r.success]
        if auth_failures:
            recommendations.append("Review authentication configuration and database connections")
        
        # Check for media service issues
        media_failures = [r for r in self.test_results if r.service == "media" and not r.success]
        if media_failures:
            recommendations.append("Verify Cloudinary configuration and media processing setup")
        
        return recommendations

    async def run_comprehensive_verification(self) -> ServiceVerificationReport:
        """Run comprehensive service verification."""
        logger.info("🚀 Starting comprehensive service verification...")
        
        # Run all tests
        test_groups = [
            self.test_health_endpoints(),
            self.test_authentication_endpoints(),
            self.test_media_endpoints(),
            self.test_scheduling_endpoints(),
            self.test_analytics_endpoints(),
            self.test_ai_service_endpoints(),
            self.test_platform_connect_endpoints()
        ]
        
        # Execute all test groups
        all_results = []
        for test_group in test_groups:
            results = await test_group
            all_results.extend(results)
            self.test_results.extend(results)
        
        # Check environment and databases
        env_check = self.check_environment_variables()
        db_check = await self.check_database_connections()
        
        # Calculate metrics
        performance_metrics = self.calculate_performance_metrics()
        recommendations = self.generate_recommendations()
        
        # Calculate summary statistics
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r.success])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        total_duration = time.time() - self.start_time
        
        # Get unique services tested
        services_tested = list(set(r.service for r in self.test_results))
        
        # Create comprehensive report
        report = ServiceVerificationReport(
            timestamp=datetime.now().isoformat(),
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            success_rate=success_rate,
            total_duration=total_duration,
            services_tested=services_tested,
            test_results=self.test_results,
            environment_check=env_check,
            database_connections=db_check,
            performance_metrics=performance_metrics,
            recommendations=recommendations
        )
        
        logger.info(f"✅ Verification complete! {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
        
        return report

    def save_results_to_json(self, report: ServiceVerificationReport, filename: str = "service_verification_results.json"):
        """Save results to JSON file."""
        # Convert dataclasses to dictionaries
        report_dict = asdict(report)
        
        with open(filename, 'w') as f:
            json.dump(report_dict, f, indent=2, default=str)
        
        logger.info(f"📄 Results saved to {filename}")

    def generate_markdown_report(self, report: ServiceVerificationReport, filename: str = "service_verification_report.md"):
        """Generate detailed Markdown report."""
        
        markdown_content = f"""# 🔍 Comprehensive Backend Service Verification Report

**Generated:** {report.timestamp}  
**Total Duration:** {report.total_duration:.2f} seconds

## 📊 Executive Summary

- **Total Tests:** {report.total_tests}
- **Passed:** {report.passed_tests} ✅
- **Failed:** {report.failed_tests} ❌
- **Success Rate:** {report.success_rate:.1f}%

## 🏥 Services Tested

{', '.join(report.services_tested)}

## 📈 Performance Metrics

"""
        
        if report.performance_metrics:
            markdown_content += f"""
- **Average Response Time:** {report.performance_metrics.get('average_response_time', 0):.3f}s
- **Min Response Time:** {report.performance_metrics.get('min_response_time', 0):.3f}s
- **Max Response Time:** {report.performance_metrics.get('max_response_time', 0):.3f}s
- **Total Requests:** {report.performance_metrics.get('total_requests', 0)}
- **Successful Requests:** {report.performance_metrics.get('successful_requests', 0)}
- **Failed Requests:** {report.performance_metrics.get('failed_requests', 0)}
"""
        
        markdown_content += f"""

## 🔧 Environment Configuration

- **Total Variables:** {report.environment_check['total_vars']}
- **Configured:** {report.environment_check['configured_vars']}
- **Missing:** {len(report.environment_check['missing_vars'])}
- **Status:** {report.environment_check['status']}

### Missing Environment Variables
"""
        
        if report.environment_check['missing_vars']:
            for var in report.environment_check['missing_vars']:
                markdown_content += f"- ❌ `{var}`\n"
        else:
            markdown_content += "- ✅ All required variables configured\n"
        
        markdown_content += """

## 🗄️ Database Connections

"""
        
        for db_name, db_info in report.database_connections.items():
            if isinstance(db_info, dict):
                status_icon = "✅" if db_info.get('status') == 'connected' else "❌"
                markdown_content += f"- **{db_name.title()}:** {status_icon} {db_info.get('status', 'unknown')}\n"
        
        markdown_content += """

## 📋 Detailed Test Results

| Service | Endpoint | Method | Status | Response Time | Result |
|---------|----------|--------|--------|---------------|--------|
"""
        
        for result in report.test_results:
            status_icon = "✅" if result.success else "❌"
            markdown_content += f"| {result.service} | `{result.endpoint}` | {result.method} | {result.status_code} | {result.response_time:.3f}s | {status_icon} |\n"
        
        markdown_content += """

## 🔍 Failed Tests Details

"""
        
        failed_tests = [r for r in report.test_results if not r.success]
        if failed_tests:
            for result in failed_tests:
                markdown_content += f"""
### ❌ {result.service.title()} - {result.endpoint}

- **Method:** {result.method}
- **Status Code:** {result.status_code}
- **Response Time:** {result.response_time:.3f}s
- **Error:** {result.error_message or 'HTTP Error'}

"""
        else:
            markdown_content += "✅ No failed tests!\n"
        
        markdown_content += """

## 💡 Recommendations

"""
        
        if report.recommendations:
            for i, rec in enumerate(report.recommendations, 1):
                markdown_content += f"{i}. {rec}\n"
        else:
            markdown_content += "✅ No specific recommendations - all systems operating normally!\n"
        
        markdown_content += f"""

## 🔗 Additional Information

- **Base URL:** {self.base_url}
- **Test Script:** `comprehensive_service_verification.py`
- **Results File:** `service_verification_results.json`

---

*Report generated by Comprehensive Service Verification Tool*
"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        logger.info(f"📄 Markdown report saved to {filename}")

async def main():
    """Main function to run comprehensive service verification."""
    print("🚀 Starting Comprehensive Backend Service Verification")
    print("=" * 60)
    
    async with ComprehensiveServiceVerifier() as verifier:
        # Run comprehensive verification
        report = await verifier.run_comprehensive_verification()
        
        # Save results
        verifier.save_results_to_json(report)
        verifier.generate_markdown_report(report)
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 VERIFICATION SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {report.passed_tests}/{report.total_tests} ({report.success_rate:.1f}%)")
        print(f"⏱️  Duration: {report.total_duration:.2f} seconds")
        print(f"🏥 Services: {', '.join(report.services_tested)}")
        
        if report.recommendations:
            print(f"\n💡 Recommendations:")
            for i, rec in enumerate(report.recommendations, 1):
                print(f"   {i}. {rec}")
        
        print(f"\n📄 Reports saved:")
        print(f"   - JSON: service_verification_results.json")
        print(f"   - Markdown: service_verification_report.md")

if __name__ == "__main__":
    asyncio.run(main())