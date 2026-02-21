"""
Unit tests for GitHub rate limit fallback mechanism
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from github import GitHubRateLimitExceeded, fetch_repo_tree, process_repo_files, get_cached_repo_snapshot
from main import analyze_repository
from schemas import AnalyzeRequest


class TestRateLimitFallback:
    """Test GitHub rate limit fallback behavior"""
    
    @pytest.mark.asyncio
    async def test_rate_limit_exception_raised_on_403(self):
        """Test that GitHubRateLimitExceeded is raised when 403 with rate limit info is returned."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Mock response with 403 status and rate limit headers
            mock_response = AsyncMock()
            mock_response.status_code = 403
            mock_response.headers = {
                'X-RateLimit-Remaining': '0',
                'X-RateLimit-Reset': str(int((datetime.now() + timedelta(minutes=10)).timestamp()))
            }
            mock_response.text = '{"message": "API rate limit exceeded"}'
            mock_client.get.return_value = mock_response
            
            with pytest.raises(GitHubRateLimitExceeded) as exc_info:
                await fetch_repo_tree("test", "repo")
            
            assert "rate limit exceeded" in str(exc_info.value).lower()
            assert exc_info.value.remaining_calls == 0

    @pytest.mark.asyncio
    async def test_fallback_with_cached_snapshot(self):
        """Test fallback uses cached snapshot when available."""
        # Setup mock cache with data
        mock_snapshot = {
            'files': [
                {'path': 'README.md', 'size': 1000, 'language': 'markdown', 'download_url': ''},
                {'path': 'package.json', 'size': 500, 'language': 'json', 'download_url': ''}
            ],
            'timestamp': datetime.now(),
            'repo': 'test/repo'
        }
        
        with patch('github.get_cached_repo_snapshot') as mock_get_cache:
            mock_get_cache.return_value = mock_snapshot
            
            with patch('main.process_repo_files') as mock_process:
                mock_process.side_effect = GitHubRateLimitExceeded(
                    reset_time=datetime.now() + timedelta(minutes=10),
                    remaining_calls=0
                )
                
                # Mock request
                request = AnalyzeRequest(repo_url="https://github.com/test/repo")
                
                # Call the endpoint function directly
                result = await analyze_repository(request)
                
                # Verify cached data was returned
                assert result.repo == "test/repo"
                assert len(result.files) == 2
                assert result.limited == True
                assert result.reason == "github_rate_limit"
                assert result.analysis_mode == "cached"

    @pytest.mark.asyncio
    async def test_fallback_with_synthetic_files(self):
        """Test fallback creates synthetic files when no cache available."""
        with patch('github.get_cached_repo_snapshot') as mock_get_cache:
            mock_get_cache.return_value = None  # No cache available
            
            with patch('main.process_repo_files') as mock_process:
                mock_process.side_effect = GitHubRateLimitExceeded(
                    reset_time=datetime.now() + timedelta(minutes=10),
                    remaining_calls=0
                )
                
                # Mock request
                request = AnalyzeRequest(repo_url="https://github.com/test/repo")
                
                # Call the endpoint function directly
                result = await analyze_repository(request)
                
                # Verify synthetic files were created
                assert result.repo == "test/repo"
                assert len(result.files) >= 3  # Should have minimum 3 files
                assert result.limited == True
                assert result.reason == "github_rate_limit"
                assert result.analysis_mode == "fallback"
                
                # Check that we have essential files
                file_paths = [f.path for f in result.files]
                assert "README.md" in file_paths
                assert "package.json" in file_paths
                assert "requirements.txt" in file_paths

    @pytest.mark.asyncio
    async def test_rate_limit_detection_in_headers(self):
        """Test that rate limit is properly detected from response headers."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Mock response that indicates rate limit exhausted
            mock_response = AsyncMock()
            mock_response.status_code = 403
            mock_response.headers = {
                'X-RateLimit-Remaining': '0',
                'X-RateLimit-Reset': str(int((datetime.now() + timedelta(minutes=15)).timestamp()))
            }
            mock_response.text = "API rate limit exceeded for this user"
            mock_client.get.return_value = mock_response
            
            with pytest.raises(GitHubRateLimitExceeded) as exc_info:
                await fetch_repo_tree("user", "repo")
            
            assert exc_info.value.remaining_calls == 0
            # Reset time should be approximately 15 minutes from now
            time_diff = (exc_info.value.reset_time - datetime.now()).total_seconds()
            assert 800 <= time_diff <= 1000  # ~15 minutes with some tolerance

    @pytest.mark.asyncio
    async def test_fallback_logging_activated(self):
        """Test that proper logging occurs during fallback activation."""
        with patch('logging.Logger.info') as mock_logger:
            with patch('github.get_cached_repo_snapshot') as mock_get_cache:
                mock_get_cache.return_value = None
                
                with patch('main.process_repo_files') as mock_process:
                    mock_process.side_effect = GitHubRateLimitExceeded(
                        reset_time=datetime.now() + timedelta(minutes=10),
                        remaining_calls=0
                    )
                    
                    request = AnalyzeRequest(repo_url="https://github.com/test/repo")
                    
                    # Call function
                    await analyze_repository(request)
                    
                    # Verify logging calls
                    log_calls = [call[0][0] for call in mock_logger.call_args_list]
                    rate_limit_logs = [log for log in log_calls if "[RATE_LIMIT]" in log]
                    fallback_logs = [log for log in log_calls if "[FALLBACK]" in log]
                    
                    assert len(rate_limit_logs) > 0
                    assert len(fallback_logs) > 0
                    assert any("synthetic fallback analysis" in log for log in fallback_logs)

    @pytest.mark.asyncio
    async def test_empty_files_never_returned(self):
        """Test that fallback system never returns completely empty files array."""
        with patch('github.get_cached_repo_snapshot') as mock_get_cache:
            mock_get_cache.return_value = None  # No cache
            
            with patch('main.process_repo_files') as mock_process:
                mock_process.side_effect = GitHubRateLimitExceeded(
                    reset_time=datetime.now() + timedelta(minutes=10),
                    remaining_calls=0
                )
                
                request = AnalyzeRequest(repo_url="https://github.com/test/repo")
                result = await analyze_repository(request)
                
                # Verify we never return empty files
                assert len(result.files) >= 3
                assert all(f.path for f in result.files)  # All files have paths

    @pytest.mark.asyncio
    async def test_retry_after_field_set_correctly(self):
        """Test that retry_after field is set correctly with ISO format."""
        reset_time = datetime.now() + timedelta(minutes=10)
        
        with patch('github.get_cached_repo_snapshot') as mock_get_cache:
            mock_get_cache.return_value = None
            
            with patch('main.process_repo_files') as mock_process:
                mock_process.side_effect = GitHubRateLimitExceeded(
                    reset_time=reset_time,
                    remaining_calls=0
                )
                
                request = AnalyzeRequest(repo_url="https://github.com/test/repo")
                result = await analyze_repository(request)
                
                # Verify retry_after is set correctly
                assert result.retry_after == reset_time.isoformat()
                assert result.limited == True
                assert result.reason == "github_rate_limit"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])