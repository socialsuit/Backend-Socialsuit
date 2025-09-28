"""
PostgreSQL-specific optimization service for Social Suit
Handles PostgreSQL query optimization, indexing, and performance tuning
"""

from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
import asyncio
import logging
import asyncpg
from contextlib import asynccontextmanager

from app.services.database.postgresql import get_db_pool
from app.services.database.redis import RedisManager
from app.services.database.query_optimizer import query_performance_tracker

logger = logging.getLogger(__name__)

class PostgreSQLOptimizer:
    """
    PostgreSQL-specific optimization service
    """
    
    def __init__(self):
        self.redis_manager = RedisManager()
        
    async def create_optimized_indexes(self) -> Dict[str, List[str]]:
        """
        Create optimized indexes for all tables
        """
        results = {}
        
        try:
            async with get_db_pool() as pool:
                async with pool.acquire() as conn:
                    # User table indexes
                    user_indexes = await self._create_user_indexes(conn)
                    results['users'] = user_indexes
                    
                    # Scheduled posts indexes
                    posts_indexes = await self._create_scheduled_posts_indexes(conn)
                    results['scheduled_posts'] = posts_indexes
                    
                    # Analytics indexes
                    analytics_indexes = await self._create_analytics_indexes(conn)
                    results['analytics'] = analytics_indexes
                    
                    # Performance indexes
                    performance_indexes = await self._create_performance_indexes(conn)
                    results['performance'] = performance_indexes
                    
                    # AB testing indexes
                    ab_test_indexes = await self._create_ab_test_indexes(conn)
                    results['ab_tests'] = ab_test_indexes
                    
                    logger.info(f"Created optimized indexes for {len(results)} table groups")
                    
        except Exception as e:
            logger.error(f"Error creating optimized indexes: {e}")
            raise
            
        return results
    
    async def _create_user_indexes(self, conn: asyncpg.Connection) -> List[str]:
        """Create optimized indexes for users table"""
        indexes = []
        
        index_definitions = [
            # Primary lookup indexes
            ("idx_users_email", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users (email)"),
            ("idx_users_wallet_address", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_wallet_address ON users (wallet_address)"),
            ("idx_users_email_wallet", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_wallet ON users (email, wallet_address)"),
            
            # Status and verification indexes
            ("idx_users_verified", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_verified ON users (is_verified) WHERE is_verified = true"),
            ("idx_users_active", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_active ON users (is_active) WHERE is_active = true"),
            
            # Time-based indexes
            ("idx_users_created_at", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_created_at ON users (created_at DESC)"),
            ("idx_users_last_login", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_last_login ON users (last_login DESC) WHERE last_login IS NOT NULL"),
            
            # Composite indexes for common queries
            ("idx_users_verified_created", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_verified_created ON users (is_verified, created_at DESC)"),
            ("idx_users_active_login", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_active_login ON users (is_active, last_login DESC)"),
            
            # Full-text search index
            ("idx_users_search", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_search ON users USING gin(to_tsvector('english', coalesce(username, '') || ' ' || coalesce(email, '')))"),
        ]
        
        for index_name, sql in index_definitions:
            try:
                await conn.execute(sql)
                indexes.append(index_name)
                logger.info(f"Created index: {index_name}")
            except Exception as e:
                logger.warning(f"Failed to create index {index_name}: {e}")
        
        return indexes
    
    async def _create_scheduled_posts_indexes(self, conn: asyncpg.Connection) -> List[str]:
        """Create optimized indexes for scheduled_posts table"""
        indexes = []
        
        index_definitions = [
            # Primary query patterns
            ("idx_scheduled_posts_user_id", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scheduled_posts_user_id ON scheduled_posts (user_id, scheduled_time DESC)"),
            ("idx_scheduled_posts_status", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scheduled_posts_status ON scheduled_posts (status, scheduled_time ASC)"),
            ("idx_scheduled_posts_platform", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scheduled_posts_platform ON scheduled_posts (platform, scheduled_time DESC)"),
            
            # Composite indexes for complex queries
            ("idx_scheduled_posts_user_status", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scheduled_posts_user_status ON scheduled_posts (user_id, status, created_at DESC)"),
            ("idx_scheduled_posts_user_platform", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scheduled_posts_user_platform ON scheduled_posts (user_id, platform, scheduled_time DESC)"),
            ("idx_scheduled_posts_platform_status", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scheduled_posts_platform_status ON scheduled_posts (platform, status, scheduled_time ASC)"),
            
            # Time-based indexes
            ("idx_scheduled_posts_scheduled_time", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scheduled_posts_scheduled_time ON scheduled_posts (scheduled_time ASC)"),
            ("idx_scheduled_posts_created_at", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scheduled_posts_created_at ON scheduled_posts (created_at DESC)"),
            ("idx_scheduled_posts_updated_at", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scheduled_posts_updated_at ON scheduled_posts (updated_at DESC)"),
            
            # Status-specific indexes
            ("idx_scheduled_posts_pending", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scheduled_posts_pending ON scheduled_posts (scheduled_time ASC) WHERE status = 'pending'"),
            ("idx_scheduled_posts_failed", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scheduled_posts_failed ON scheduled_posts (updated_at DESC) WHERE status = 'failed'"),
            ("idx_scheduled_posts_published", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scheduled_posts_published ON scheduled_posts (published_at DESC) WHERE status = 'published'"),
            
            # Content search index
            ("idx_scheduled_posts_content", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scheduled_posts_content ON scheduled_posts USING gin(to_tsvector('english', coalesce(content, '') || ' ' || coalesce(title, '')))"),
        ]
        
        for index_name, sql in index_definitions:
            try:
                await conn.execute(sql)
                indexes.append(index_name)
                logger.info(f"Created index: {index_name}")
            except Exception as e:
                logger.warning(f"Failed to create index {index_name}: {e}")
        
        return indexes
    
    async def _create_analytics_indexes(self, conn: asyncpg.Connection) -> List[str]:
        """Create optimized indexes for analytics tables"""
        indexes = []
        
        # Post engagement indexes
        engagement_indexes = [
            ("idx_post_engagement_user_platform", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_post_engagement_user_platform ON post_engagement (user_id, platform, created_at DESC)"),
            ("idx_post_engagement_user_time", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_post_engagement_user_time ON post_engagement (user_id, created_at DESC)"),
            ("idx_post_engagement_platform_time", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_post_engagement_platform_time ON post_engagement (platform, created_at DESC)"),
            ("idx_post_engagement_total", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_post_engagement_total ON post_engagement (total_engagement DESC, created_at DESC)"),
            ("idx_post_engagement_rate", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_post_engagement_rate ON post_engagement (engagement_rate DESC, created_at DESC)"),
        ]
        
        # User metrics indexes
        metrics_indexes = [
            ("idx_user_metrics_user_time", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_metrics_user_time ON user_metrics (user_id, created_at DESC)"),
            ("idx_user_metrics_platform", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_metrics_platform ON user_metrics (platform, created_at DESC)"),
            ("idx_user_metrics_followers", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_metrics_followers ON user_metrics (follower_count DESC, created_at DESC)"),
            ("idx_user_metrics_engagement", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_metrics_engagement ON user_metrics (engagement_rate DESC, created_at DESC)"),
        ]
        
        # Content performance indexes
        content_indexes = [
            ("idx_content_performance_user", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_performance_user ON content_performance (user_id, created_at DESC)"),
            ("idx_content_performance_type", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_performance_type ON content_performance (content_type, engagement_rate DESC)"),
            ("idx_content_performance_platform", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_performance_platform ON content_performance (platform, engagement_rate DESC)"),
            ("idx_content_performance_rate", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_performance_rate ON content_performance (engagement_rate DESC, created_at DESC)"),
        ]
        
        all_indexes = engagement_indexes + metrics_indexes + content_indexes
        
        for index_name, sql in all_indexes:
            try:
                await conn.execute(sql)
                indexes.append(index_name)
                logger.info(f"Created index: {index_name}")
            except Exception as e:
                logger.warning(f"Failed to create index {index_name}: {e}")
        
        return indexes
    
    async def _create_performance_indexes(self, conn: asyncpg.Connection) -> List[str]:
        """Create performance monitoring indexes"""
        indexes = []
        
        index_definitions = [
            # Query performance tracking
            ("idx_query_performance_operation", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_query_performance_operation ON query_performance (operation_type, timestamp DESC)"),
            ("idx_query_performance_duration", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_query_performance_duration ON query_performance (duration_ms DESC, timestamp DESC)"),
            ("idx_query_performance_database", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_query_performance_database ON query_performance (database_type, operation_type, timestamp DESC)"),
            
            # System metrics
            ("idx_system_metrics_timestamp", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics (timestamp DESC)"),
            ("idx_system_metrics_metric_type", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_system_metrics_metric_type ON system_metrics (metric_type, timestamp DESC)"),
        ]
        
        for index_name, sql in index_definitions:
            try:
                await conn.execute(sql)
                indexes.append(index_name)
                logger.info(f"Created index: {index_name}")
            except Exception as e:
                logger.warning(f"Failed to create index {index_name}: {e}")
        
        return indexes
    
    async def _create_ab_test_indexes(self, conn: asyncpg.Connection) -> List[str]:
        """Create AB testing indexes"""
        indexes = []
        
        index_definitions = [
            # Test management
            ("idx_ab_tests_user_status", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ab_tests_user_status ON ab_tests (user_id, status, created_at DESC)"),
            ("idx_ab_tests_name_user", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ab_tests_name_user ON ab_tests (test_name, user_id)"),
            ("idx_ab_tests_status_end", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ab_tests_status_end ON ab_tests (status, end_date ASC)"),
            
            # Performance analysis
            ("idx_ab_tests_conversion", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ab_tests_conversion ON ab_tests (conversion_rate DESC, created_at DESC)"),
            ("idx_ab_tests_platform_conversion", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ab_tests_platform_conversion ON ab_tests (platform, conversion_rate DESC)"),
            
            # Test variants
            ("idx_ab_test_variants_test", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ab_test_variants_test ON ab_test_variants (test_id, variant_name)"),
            ("idx_ab_test_variants_performance", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ab_test_variants_performance ON ab_test_variants (test_id, conversion_rate DESC)"),
        ]
        
        for index_name, sql in index_definitions:
            try:
                await conn.execute(sql)
                indexes.append(index_name)
                logger.info(f"Created index: {index_name}")
            except Exception as e:
                logger.warning(f"Failed to create index {index_name}: {e}")
        
        return indexes
    
    @query_performance_tracker("postgresql", "optimized_query")
    async def execute_optimized_query(self, query: str, params: Optional[List] = None,
                                    cache_key: Optional[str] = None, cache_ttl: int = 300) -> List[Dict]:
        """
        Execute optimized query with caching
        """
        # Check cache first
        if cache_key:
            cached_result = await self.redis_manager.cache_get(cache_key)
            if cached_result:
                return cached_result
        
        try:
            async with get_db_pool() as pool:
                async with pool.acquire() as conn:
                    # Add query optimization hints
                    optimized_query = self._add_query_hints(query)
                    
                    # Execute query
                    if params:
                        rows = await conn.fetch(optimized_query, *params)
                    else:
                        rows = await conn.fetch(optimized_query)
                    
                    # Convert to list of dicts
                    results = [dict(row) for row in rows]
                    
                    # Cache results
                    if cache_key and results:
                        await self.redis_manager.cache_set(cache_key, results, cache_ttl)
                    
                    return results
                    
        except Exception as e:
            logger.error(f"Error in optimized query execution: {e}")
            raise
    
    def _add_query_hints(self, query: str) -> str:
        """
        Add PostgreSQL-specific optimization hints to queries
        """
        # Add common optimization hints
        hints = []
        
        # Enable parallel query execution for large datasets
        if "COUNT(*)" in query.upper() or "SUM(" in query.upper():
            hints.append("SET max_parallel_workers_per_gather = 4")
        
        # Use hash joins for large table joins
        if "JOIN" in query.upper():
            hints.append("SET enable_hashjoin = on")
            hints.append("SET enable_mergejoin = on")
        
        # Optimize for analytics queries
        if "GROUP BY" in query.upper() or "ORDER BY" in query.upper():
            hints.append("SET work_mem = '256MB'")
        
        if hints:
            return "; ".join(hints) + "; " + query
        
        return query
    
    async def analyze_table_statistics(self) -> Dict[str, Dict]:
        """
        Analyze and update table statistics for query optimization
        """
        results = {}
        
        tables_to_analyze = [
            'users', 'scheduled_posts', 'post_engagement', 
            'user_metrics', 'content_performance', 'ab_tests'
        ]
        
        try:
            async with get_db_pool() as pool:
                async with pool.acquire() as conn:
                    for table in tables_to_analyze:
                        try:
                            # Update table statistics
                            await conn.execute(f"ANALYZE {table}")
                            
                            # Get table statistics
                            stats_query = """
                                SELECT 
                                    schemaname,
                                    tablename,
                                    n_tup_ins as inserts,
                                    n_tup_upd as updates,
                                    n_tup_del as deletes,
                                    n_live_tup as live_tuples,
                                    n_dead_tup as dead_tuples,
                                    last_vacuum,
                                    last_autovacuum,
                                    last_analyze,
                                    last_autoanalyze
                                FROM pg_stat_user_tables 
                                WHERE tablename = $1
                            """
                            
                            row = await conn.fetchrow(stats_query, table)
                            if row:
                                results[table] = dict(row)
                            
                            logger.info(f"Analyzed table: {table}")
                            
                        except Exception as e:
                            logger.warning(f"Failed to analyze table {table}: {e}")
                            
        except Exception as e:
            logger.error(f"Error analyzing table statistics: {e}")
            raise
        
        return results
    
    async def get_slow_queries(self, limit: int = 10) -> List[Dict]:
        """
        Get slow queries from pg_stat_statements
        """
        try:
            async with get_db_pool() as pool:
                async with pool.acquire() as conn:
                    # Check if pg_stat_statements extension is available
                    ext_check = await conn.fetchval(
                        "SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'"
                    )
                    
                    if not ext_check:
                        logger.warning("pg_stat_statements extension not available")
                        return []
                    
                    query = """
                        SELECT 
                            query,
                            calls,
                            total_time,
                            mean_time,
                            rows,
                            100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
                        FROM pg_stat_statements 
                        ORDER BY total_time DESC 
                        LIMIT $1
                    """
                    
                    rows = await conn.fetch(query, limit)
                    return [dict(row) for row in rows]
                    
        except Exception as e:
            logger.error(f"Error getting slow queries: {e}")
            return []
    
    async def optimize_table_maintenance(self) -> Dict[str, str]:
        """
        Perform table maintenance operations
        """
        results = {}
        
        tables_to_maintain = [
            'users', 'scheduled_posts', 'post_engagement', 
            'user_metrics', 'content_performance'
        ]
        
        try:
            async with get_db_pool() as pool:
                async with pool.acquire() as conn:
                    for table in tables_to_maintain:
                        try:
                            # Check if vacuum is needed
                            vacuum_check = await conn.fetchrow(
                                """
                                SELECT 
                                    n_dead_tup,
                                    n_live_tup,
                                    CASE 
                                        WHEN n_live_tup > 0 
                                        THEN (n_dead_tup::float / n_live_tup::float) * 100 
                                        ELSE 0 
                                    END as dead_tuple_percent
                                FROM pg_stat_user_tables 
                                WHERE tablename = $1
                                """,
                                table
                            )
                            
                            if vacuum_check and vacuum_check['dead_tuple_percent'] > 10:
                                # Perform vacuum
                                await conn.execute(f"VACUUM ANALYZE {table}")
                                results[table] = "vacuumed"
                                logger.info(f"Vacuumed table: {table}")
                            else:
                                # Just analyze
                                await conn.execute(f"ANALYZE {table}")
                                results[table] = "analyzed"
                                logger.info(f"Analyzed table: {table}")
                                
                        except Exception as e:
                            logger.warning(f"Failed to maintain table {table}: {e}")
                            results[table] = f"error: {e}"
                            
        except Exception as e:
            logger.error(f"Error in table maintenance: {e}")
            raise
        
        return results
    
    async def get_index_usage_stats(self) -> List[Dict]:
        """
        Get index usage statistics
        """
        try:
            async with get_db_pool() as pool:
                async with pool.acquire() as conn:
                    query = """
                        SELECT 
                            schemaname,
                            tablename,
                            indexname,
                            idx_tup_read,
                            idx_tup_fetch,
                            idx_scan,
                            CASE 
                                WHEN idx_scan = 0 THEN 'Unused'
                                WHEN idx_scan < 10 THEN 'Low Usage'
                                WHEN idx_scan < 100 THEN 'Medium Usage'
                                ELSE 'High Usage'
                            END as usage_level
                        FROM pg_stat_user_indexes 
                        ORDER BY idx_scan DESC
                    """
                    
                    rows = await conn.fetch(query)
                    return [dict(row) for row in rows]
                    
        except Exception as e:
            logger.error(f"Error getting index usage stats: {e}")
            return []
    
    async def get_table_sizes(self) -> List[Dict]:
        """
        Get table size information
        """
        try:
            async with get_db_pool() as pool:
                async with pool.acquire() as conn:
                    query = """
                        SELECT 
                            schemaname,
                            tablename,
                            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
                            pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
                            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size,
                            pg_total_relation_size(schemaname||'.'||tablename) as total_bytes
                        FROM pg_tables 
                        WHERE schemaname = 'public'
                        ORDER BY total_bytes DESC
                    """
                    
                    rows = await conn.fetch(query)
                    return [dict(row) for row in rows]
                    
        except Exception as e:
            logger.error(f"Error getting table sizes: {e}")
            return []
    
    async def create_materialized_views(self) -> List[str]:
        """
        Create materialized views for common analytics queries
        """
        created_views = []
        
        view_definitions = [
            # Daily user engagement summary
            ("mv_daily_user_engagement", """
                CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_user_engagement AS
                SELECT 
                    user_id,
                    platform,
                    DATE(created_at) as engagement_date,
                    COUNT(*) as total_engagements,
                    SUM(total_engagement) as total_engagement_count,
                    AVG(engagement_rate) as avg_engagement_rate,
                    MAX(engagement_rate) as max_engagement_rate
                FROM post_engagement 
                WHERE created_at >= CURRENT_DATE - INTERVAL '90 days'
                GROUP BY user_id, platform, DATE(created_at)
                WITH DATA
            """),
            
            # Weekly content performance summary
            ("mv_weekly_content_performance", """
                CREATE MATERIALIZED VIEW IF NOT EXISTS mv_weekly_content_performance AS
                SELECT 
                    user_id,
                    content_type,
                    platform,
                    DATE_TRUNC('week', created_at) as week_start,
                    COUNT(*) as content_count,
                    AVG(engagement_rate) as avg_engagement_rate,
                    MAX(engagement_rate) as best_engagement_rate,
                    MIN(engagement_rate) as worst_engagement_rate
                FROM content_performance 
                WHERE created_at >= CURRENT_DATE - INTERVAL '12 weeks'
                GROUP BY user_id, content_type, platform, DATE_TRUNC('week', created_at)
                WITH DATA
            """),
            
            # Monthly user metrics summary
            ("mv_monthly_user_metrics", """
                CREATE MATERIALIZED VIEW IF NOT EXISTS mv_monthly_user_metrics AS
                SELECT 
                    user_id,
                    DATE_TRUNC('month', created_at) as month_start,
                    AVG(follower_count) as avg_followers,
                    MAX(follower_count) as max_followers,
                    AVG(engagement_rate) as avg_engagement_rate,
                    SUM(total_posts) as total_posts
                FROM user_metrics 
                WHERE created_at >= CURRENT_DATE - INTERVAL '12 months'
                GROUP BY user_id, DATE_TRUNC('month', created_at)
                WITH DATA
            """)
        ]
        
        try:
            async with get_db_pool() as pool:
                async with pool.acquire() as conn:
                    for view_name, sql in view_definitions:
                        try:
                            await conn.execute(sql)
                            
                            # Create indexes on materialized views
                            index_sql = f"""
                                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_{view_name}_user_date 
                                ON {view_name} (user_id, {view_name.split('_')[1]}_start DESC)
                            """
                            await conn.execute(index_sql)
                            
                            created_views.append(view_name)
                            logger.info(f"Created materialized view: {view_name}")
                            
                        except Exception as e:
                            logger.warning(f"Failed to create materialized view {view_name}: {e}")
                            
        except Exception as e:
            logger.error(f"Error creating materialized views: {e}")
            raise
        
        return created_views
    
    async def refresh_materialized_views(self) -> Dict[str, bool]:
        """
        Refresh all materialized views
        """
        results = {}
        
        views_to_refresh = [
            "mv_daily_user_engagement",
            "mv_weekly_content_performance", 
            "mv_monthly_user_metrics"
        ]
        
        try:
            async with get_db_pool() as pool:
                async with pool.acquire() as conn:
                    for view_name in views_to_refresh:
                        try:
                            await conn.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}")
                            results[view_name] = True
                            logger.info(f"Refreshed materialized view: {view_name}")
                        except Exception as e:
                            logger.warning(f"Failed to refresh materialized view {view_name}: {e}")
                            results[view_name] = False
                            
        except Exception as e:
            logger.error(f"Error refreshing materialized views: {e}")
            raise
        
        return results