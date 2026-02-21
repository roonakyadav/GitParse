import asyncio
import logging
from typing import Dict, List, Any, Optional
import hashlib
import time

from .client import get_groq_client
from .prompts import get_prompt_template, format_chunks_for_prompt
from .parser import response_parser, ReviewResult, Issue, SecurityIssue, ArchitectureIssue, SkillGap

logger = logging.getLogger(__name__)

class ReviewEngine:
    def __init__(self):
        self.cache = {}
        self.max_chunks_per_request = 15
        self.cache_ttl = 3600  # 1 hour
    
    def _get_cache_key(self, chunks: List[Dict], review_type: str) -> str:
        """Generate cache key for chunks and review type."""
        content = str([chunk.get("content", "") for chunk in chunks[:5]]) + review_type
        return hashlib.md5(content.encode()).hexdigest()
    
    def _map_chunk_ids_to_actual_data(self, result: Dict[str, Any], chunk_mapping: Dict[str, Dict]) -> Dict[str, Any]:
        """Map chunk_id to actual file/lines/snippet data for all issues in the result."""
        logger.debug(f"Mapping chunk IDs for result with keys: {list(result.keys())}")
        
        # Process each type of issue
        for issue_type in ['issues', 'security', 'architecture', 'skills']:
            if issue_type in result:
                updated_issues = []
                for issue in result[issue_type]:
                    # Make a copy of the issue to modify
                    updated_issue = issue.copy()
                    
                    # Check if the issue has a chunk_id
                    chunk_id = updated_issue.get('chunk_id')
                    if chunk_id and chunk_id in chunk_mapping:
                        chunk_data = chunk_mapping[chunk_id]
                        
                        # Update file, lines, and snippet from the actual chunk
                        updated_issue['file'] = chunk_data['file']
                        start_line = chunk_data['start_line']
                        end_line = chunk_data['end_line']
                        updated_issue['lines'] = f"{start_line}-{end_line}"
                        
                        # Update snippet if it's not already set or if it's a placeholder
                        if not updated_issue.get('snippet') or updated_issue.get('snippet') == 'Not found in provided context':
                            content = chunk_data['content']
                            # Take a reasonable portion of the content as the snippet
                            if len(content) > 200:
                                updated_issue['snippet'] = content[:200] + "..."
                            else:
                                updated_issue['snippet'] = content
                    elif chunk_id == 'global analysis':
                        # For global analysis, keep the issue but mark appropriately
                        updated_issue['file'] = 'Multiple files'
                        updated_issue['lines'] = 'N/A'
                        updated_issue['snippet'] = 'Cross-file analysis'
                    else:
                        # If no specific chunk_id, or chunk_id not found in mapping, mark as global analysis
                        updated_issue['file'] = 'Multiple files'
                        updated_issue['lines'] = 'N/A'
                        updated_issue['snippet'] = 'Cross-file analysis'
                        updated_issue['chunk_id'] = 'global analysis'
                    
                    updated_issues.append(updated_issue)
                
                result[issue_type] = updated_issues
        
        return result
    
    def _is_cache_valid(self, timestamp: float) -> bool:
        """Check if cache entry is still valid."""
        return time.time() - timestamp < self.cache_ttl
    
    def _select_important_chunks(self, index_data: Dict, max_chunks: int = 50) -> List[Dict]:
        """Select most important chunks for analysis with minimum guarantee."""
        chunks = []
        
        # Get chunks from index
        if "chunks" in index_data:
            all_chunks = index_data["chunks"]
        else:
            # Fallback to files structure
            all_chunks = []
            for file_data in index_data.get("files", []):
                if "chunks" in file_data:
                    all_chunks.extend(file_data["chunks"])
        
        if not all_chunks:
            logger.warning("No chunks found in index data")
            return []
        
        # Add debug logging
        logger.info(f"Total chunks available: {len(all_chunks)}")
        
        # Log the first chunk to inspect the schema
        if all_chunks:
            logger.info(f"Sample chunk schema: {list(all_chunks[0].keys()) if all_chunks else 'No chunks'}")
            logger.info(f"Full sample chunk: {all_chunks[0] if all_chunks else 'No chunks'}")
        
        # Filter out empty chunks and validate content
        valid_chunks = []
        for chunk in all_chunks:
            # Support multiple possible field names for content
            content = (chunk.get("content") or 
                      chunk.get("text") or 
                      chunk.get("code") or 
                      chunk.get("body") or "")
            
            # Support multiple possible field names for file path
            file_path = (chunk.get("file_path") or 
                         chunk.get("file") or 
                         chunk.get("path") or 
                         chunk.get("filename") or "")
            
            # Support multiple possible field names for line numbers
            start_line = (chunk.get("start_line") or 
                          chunk.get("start") or 
                          chunk.get("lines", {}).get("start") if isinstance(chunk.get("lines"), dict) else None or 
                          "")
            
            end_line = (chunk.get("end_line") or 
                        chunk.get("end") or 
                        chunk.get("lines", {}).get("end") if isinstance(chunk.get("lines"), dict) else None or 
                        "")
            
            # Verify chunk has valid content and metadata
            if content and len(content.strip()) > 0 and file_path:
                # Remove the hard length threshold to ensure valid chunks pass validation
                valid_chunks.append(chunk)
            else:
                logger.debug(f"Invalid chunk data: file_path='{file_path}', content length={len(str(content)) if content else 0}, start_line={start_line}")
        
        logger.info(f"Valid chunks after filtering: {len(valid_chunks)}")
        
        # If we have fewer than our minimum, use what we have
        min_chunks = 5
        if len(valid_chunks) < min_chunks:
            logger.info(f"Only {len(valid_chunks)} valid chunks found, using all of them")
            return valid_chunks
        
        # Sort by importance (token count, dependencies, etc.)
        scored_chunks = []
        for chunk in valid_chunks:
            score = 0
            
            # Prefer larger chunks (more content)
            token_count = chunk.get("token_count", 0)
            # Support multiple possible field names for content
            content = (chunk.get("content") or 
                      chunk.get("text") or 
                      chunk.get("code") or 
                      chunk.get("body") or "")
            if token_count > 0:
                score += min(token_count / 100, 5)
            else:
                # Fallback to character count if token count not available
                score += min(len(content) / 200, 5)
            
            # Prefer chunks with dependencies
            if chunk.get("dependencies"):
                score += len(chunk["dependencies"]) * 2
            
            # Prefer chunks from important files
            # Support multiple possible field names for file path
            file_path = (chunk.get("file_path") or 
                         chunk.get("file") or 
                         chunk.get("path") or 
                         chunk.get("filename") or "")
            if any(keyword in file_path.lower() for keyword in ["main", "index", "app", "server"]):
                score += 3
            
            # Prefer chunks with complex code (heuristic)
            if "class " in content or "def " in content:
                score += 2
            if "import " in content or "require(" in content:
                score += 1
            
            # Add diversity bonus - prefer different files
            chunk["_file_hash"] = hash(file_path) % 1000
            score += chunk["_file_hash"] / 1000
            
            scored_chunks.append((score, chunk))
        
        # Sort by score and take top chunks
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        selected_chunks = [chunk for _, chunk in scored_chunks[:max(max_chunks, min_chunks)]]
        
        # Additional debug logging
        logger.info(f"Selected {len(selected_chunks)} important chunks from {len(valid_chunks)} valid chunks")
        
        # Print debug info about selected chunks
        if selected_chunks:
            avg_length = sum(len(chunk.get('content', '')) for chunk in selected_chunks) / len(selected_chunks)
            logger.info(f"Number of chunks sent to AI: {len(selected_chunks)}")
            logger.info(f"Average chunk length: {avg_length:.2f} characters")
            logger.info(f"First chunk preview: {selected_chunks[0].get('content', '')[:500] if selected_chunks else 'None'}...")
        
        return selected_chunks
    
    async def _analyze_single_review(self, chunks: List[Dict], review_type: str) -> Dict[str, Any]:
        """Analyze chunks for a single review type."""
        review_logger = logging.getLogger("ai.review")
        review_logger.info(f"Starting {review_type} analysis with {len(chunks)} chunks")
        
        # Create chunk ID mapping for evidence verification
        chunk_mapping = {}
        for i, chunk in enumerate(chunks, 1):
            chunk_id = f"CHUNK_{i}"
            chunk_mapping[chunk_id] = {
                'file': chunk.get('file_path') or chunk.get('file') or chunk.get('path') or chunk.get('filename') or 'unknown',
                'start_line': chunk.get('start_line') or chunk.get('start') or chunk.get('lines', {}).get('start') or 1,
                'end_line': chunk.get('end_line') or chunk.get('end') or chunk.get('lines', {}).get('end') or 1,
                'content': chunk.get('content') or chunk.get('text') or chunk.get('code') or chunk.get('body') or ''
            }
        
        # Check cache
        cache_key = self._get_cache_key(chunks, review_type)
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if self._is_cache_valid(timestamp):
                review_logger.info(f"ai.reviewer: Using cached result for {review_type} review")
                return cached_data
        
        try:
            # Format chunks for prompt
            formatted_chunks = format_chunks_for_prompt(chunks, self.max_chunks_per_request)
            review_logger.debug(f"Formatted chunks for {review_type}: {len(formatted_chunks)} chars")
            
            # Get prompt template
            prompt_template = get_prompt_template(review_type)
            prompt = prompt_template.replace("{{chunks}}", formatted_chunks)
            review_logger.debug(f"Generated prompt for {review_type}: {len(prompt)} chars")
            
            review_logger.info(f"Calling Groq API for {review_type} review")
            
            # Call Groq API
            client = get_groq_client()
            response = await client.call_groq(prompt)
            
            review_logger.info(f"Got response for {review_type}, length: {len(response)}")
            review_logger.debug(f"Response preview: {response[:200]}...")
            
            # Parse response
            result = response_parser.parse_review_response(response, review_type)
            review_logger.info(f"Parsed result for {review_type}: {result}")
            
            # Map chunk_id to actual file/lines/snippet data
            result = self._map_chunk_ids_to_actual_data(result, chunk_mapping)
            
            # If parsing failed completely, return structured error instead of heuristic
            if not result:
                review_logger.error(f"ai.reviewer: AI analysis and parsing failed for {review_type}")
                return {
                    "score": 0,
                    "error": f"AI analysis failed for {review_type}",
                    **{review_type: []}
                }
            
            review_logger.info(f"ai.reviewer: Completed {review_type} review: {result.get('score', 0)} score")
            
            # Cache result
            self.cache[cache_key] = (result, time.time())
            return result
            
        except Exception as e:
            review_logger.error(f"ai.reviewer: Failed to analyze {review_type} review: {str(e)}", exc_info=True)
            # Instead of returning an empty list, emit a minimal placeholder entry so
            # the downstream merge always has something to show and the frontend
            # doesn't end up with an entirely blank section.
            placeholder = []
            if review_type == "quality":
                placeholder = [{
                    "type": "quality",
                    "severity": "low",
                    "message": "AI review unavailable due to service error",
                    "file": chunks[0].get("file", "unknown") if chunks else "unknown",
                    "line": 1,
                    "suggestion": "Manual inspection recommended"
                }]
            elif review_type == "architecture":
                placeholder = [{
                    "type": "architecture",
                    "severity": "low",
                    "message": "Architecture review unavailable due to service error",
                    "file": chunks[0].get("file", "unknown") if chunks else "unknown",
                    "line": 1,
                    "suggestion": "Manual inspection recommended"
                }]
            elif review_type == "skills":
                placeholder = [{
                    "category": "tool",
                    "skill": "AI Analysis",
                    "level": "beginner",
                    "gap": "AI analysis services unavailable",
                    "resource": "Manual code review practices",
                    "priority": "medium"
                }]
            # security can remain empty if it fails, quality/architecture/skills cover requirement
            return {
                "score": 0,
                "error": f"AI analysis failed for {review_type}: {str(e)}",
                **{review_type: placeholder}
            }
    
    async def analyze_repo(self, index_data: Dict) -> Dict[str, Any]:
        """Analyze repository and return comprehensive review."""
        review_logger = logging.getLogger("ai.review")
        review_logger.info("Starting Phase 3 AI Review Engine analysis")
        
        # Select important chunks
        important_chunks = self._select_important_chunks(index_data)
        
        if not important_chunks:
            review_logger.warning("No chunks to analyze")
            return {
                "success": False,
                "error": "No code chunks found for analysis",
                "issues": [],
                "security": [],
                "architecture": [],
                "skills": [],
                "score": 0
            }
        
        # Validate chunks have meaningful content
        valid_chunks = []
        for chunk in important_chunks:
            # Support multiple possible field names for content
            content = (chunk.get("content") or 
                      chunk.get("text") or 
                      chunk.get("code") or 
                      chunk.get("body") or "")
            if content and len(content.strip()) > 0:
                valid_chunks.append(chunk)
            else:
                # Support multiple possible field names for file path
                file_path = (chunk.get("file_path") or 
                             chunk.get("file") or 
                             chunk.get("path") or 
                             chunk.get("filename") or "unknown")
                logger.warning(f"Found empty chunk: {file_path}")
        
        if not valid_chunks:
            review_logger.warning("All selected chunks have empty content")
            return {
                "success": False,
                "error": "All chunks have empty content",
                "issues": [],
                "security": [],
                "architecture": [],
                "skills": [],
                "score": 0
            }
        
        # Update important_chunks with validated chunks
        important_chunks = valid_chunks
        
        # Run all review types concurrently
        review_types = ["quality", "security", "architecture", "skills"]
        tasks = [
            self._analyze_single_review(important_chunks, review_type)
            for review_type in review_types
        ]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and collect errors
            valid_results = []
            error_count = 0
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    review_logger.error(f"Review {review_types[i]} failed: {str(result)}")
                    valid_results.append(response_parser._get_empty_result(review_types[i]))
                    error_count += 1
                elif isinstance(result, dict) and result.get("error"):
                    review_logger.error(f"Review {review_types[i]} returned error: {result['error']}")
                    valid_results.append(response_parser._get_empty_result(review_types[i]))
                    error_count += 1
                else:
                    valid_results.append(result)
            
            # If all reviews failed, return minimal fallback analysis
            if error_count == len(review_types):
                review_logger.error("All review types failed, using fallback analysis")
                return self._create_fallback_analysis(index_data, important_chunks)
            
            # Merge results
            final_result = response_parser.merge_results(valid_results)
            
            # CRITICAL: Ensure at least some analysis results
            if (len(final_result.issues) == 0 and 
                len(final_result.security) == 0 and 
                len(final_result.architecture) == 0 and 
                len(final_result.skills) == 0):
                review_logger.warning("All analysis results empty, creating fallback")
                fallback = self._create_fallback_analysis(index_data, important_chunks)
                # Merge fallback with existing results
                final_result.issues.extend([Issue(**issue) for issue in fallback.get("issues", [])])
                final_result.security.extend([SecurityIssue(**issue) for issue in fallback.get("security", [])])
                final_result.architecture.extend([ArchitectureIssue(**issue) for issue in fallback.get("architecture", [])])
                final_result.skills.extend([SkillGap(**skill) for skill in fallback.get("skills", [])])
            
            # Convert to dict for JSON response
            response_data = {
                "success": True,
                "issues": [issue.dict() for issue in final_result.issues],
                "security": [issue.dict() for issue in final_result.security],
                "architecture": [issue.dict() for issue in final_result.architecture],
                "skills": [skill.dict() for skill in final_result.skills],
                "score": final_result.score if final_result.score is not None else 50,
                "chunks_analyzed": len(important_chunks),
                "total_chunks": len(index_data.get("chunks", [])),
                "review_types": review_types,
                "failed_reviews": error_count
            }
            
            # CRITICAL: Ensure score is always a valid number
            try:
                response_data["score"] = float(response_data["score"])
                response_data["score"] = max(0, min(100, response_data["score"]))
            except (ValueError, TypeError):
                response_data["score"] = 50
            
            # Ensure all array fields are lists
            for field in ["issues", "security", "architecture", "skills"]:
                if field not in response_data or not isinstance(response_data[field], list):
                    response_data[field] = []
            
            review_logger.info(f"Phase 3 analysis completed: score {final_result.score}, {error_count} reviews failed")
            return response_data
            
        except Exception as e:
            review_logger.error(f"Repository analysis failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Analysis failed: {str(e)}",
                "issues": [],
                "security": [],
                "architecture": [],
                "skills": [],
                "score": 0
            }
    
    def _heuristic_analysis(self, chunks: List[Dict], review_type: str) -> Dict[str, Any]:
        """Provide fallback heuristic analysis when AI fails."""
        logger.info(f"ai.reviewer: Using heuristic analysis for {review_type}")
        
        result = {"score": 75}  # Default score
        
        if review_type == "quality":
            issues = []
            
            # Check for common quality issues
            for chunk in chunks:
                content = chunk.get("content", "").lower()
                file_path = chunk.get("file", "unknown")
                start_line = chunk.get("start_line", 1)
                
                # TODO comments
                if "todo" in content or "fixme" in content:
                    issues.append({
                        "type": "quality",
                        "severity": "medium",
                        "message": "TODO/FIXME comments found",
                        "file": file_path,
                        "line": start_line,
                        "suggestion": "Complete TODO items or remove comments"
                    })
                
                # Long functions
                lines = content.split('\n')
                if len(lines) > 50:
                    issues.append({
                        "type": "quality",
                        "severity": "medium",
                        "message": "Very long function detected",
                        "file": file_path,
                        "line": start_line,
                        "suggestion": "Consider breaking down into smaller functions"
                    })
                
                # No error handling
                if "def " in content and "try:" not in content and "except" not in content:
                    issues.append({
                        "type": "quality",
                        "severity": "low",
                        "message": "Function may lack error handling",
                        "file": file_path,
                        "line": start_line,
                        "suggestion": "Consider adding try-catch blocks"
                    })
            
            result["issues"] = issues
            if issues:
                result["score"] = max(50, 75 - len(issues) * 5)
        
        elif review_type == "security":
            security = []
            
            for chunk in chunks:
                content = chunk.get("content", "").lower()
                file_path = chunk.get("file", "unknown")
                start_line = chunk.get("start_line", 1)
                
                # SQL injection patterns
                if "execute(" in content and "select" in content:
                    security.append({
                        "type": "security",
                        "severity": "high",
                        "message": "Potential SQL injection vulnerability",
                        "file": file_path,
                        "line": start_line,
                        "cwe": "CWE-89",
                        "suggestion": "Use parameterized queries"
                    })
                
                # Hardcoded passwords/keys
                if any(word in content for word in ["password", "secret", "key", "token"]):
                    if "=" in content and '"' in content:
                        security.append({
                            "type": "security",
                            "severity": "critical",
                            "message": "Potential hardcoded credentials",
                            "file": file_path,
                            "line": start_line,
                            "cwe": "CWE-798",
                            "suggestion": "Use environment variables for secrets"
                        })
                
                # eval/exec usage
                if "eval(" in content or "exec(" in content:
                    security.append({
                        "type": "security",
                        "severity": "high",
                        "message": "Use of eval/exec detected",
                        "file": file_path,
                        "line": start_line,
                        "cwe": "CWE-94",
                        "suggestion": "Avoid eval/exec, use safer alternatives"
                    })
            
            result["security"] = security
            if security:
                critical_count = sum(1 for s in security if s["severity"] == "critical")
                high_count = sum(1 for s in security if s["severity"] == "high")
                result["score"] = max(20, 75 - critical_count * 20 - high_count * 10)
        
        elif review_type == "architecture":
            architecture = []
            
            # Analyze overall structure
            file_count = len(set(chunk.get("file", "unknown") for chunk in chunks))
            total_chunks = len(chunks)
            
            # Too many files in single analysis
            if file_count > 20:
                architecture.append({
                    "type": "architecture",
                    "severity": "medium",
                    "message": "Large number of files detected",
                    "file": "multiple",
                    "line": 1,
                    "principle": "Modularity",
                    "suggestion": "Consider organizing into modules"
                })
            
            # Deep dependency chains
            for chunk in chunks:
                deps = chunk.get("dependencies", [])
                if len(deps) > 10:
                    architecture.append({
                        "type": "architecture",
                        "severity": "high",
                        "message": "High coupling detected",
                        "file": chunk.get("file", "unknown"),
                        "line": chunk.get("start_line", 1),
                        "principle": "Low Coupling",
                        "suggestion": "Reduce dependencies"
                    })
            
            result["architecture"] = architecture
            if architecture:
                result["score"] = max(40, 75 - len(architecture) * 8)
        
        elif review_type == "skills":
            skills = []
            
            # Analyze technologies and patterns
            all_content = " ".join(chunk.get("content", "") for chunk in chunks).lower()
            files = [chunk.get("file", "") for chunk in chunks]
            
            # Language detection
            if any(f.endswith('.py') for f in files):
                if "class " in all_content and "def __init__" in all_content:
                    skills.append({
                        "category": "language",
                        "skill": "Python OOP",
                        "level": "intermediate",
                        "gap": "Could use more advanced patterns",
                        "resource": "Effective Python book",
                        "priority": "medium"
                    })
            
            # Framework detection
            if "react" in all_content or "jsx" in all_content or "const Component" in all_content:
                skills.append({
                    "category": "framework",
                    "skill": "React",
                    "level": "beginner",
                    "gap": "Missing hooks and modern patterns",
                    "resource": "React documentation",
                    "priority": "high"
                })
            elif any(fw in all_content for fw in ["vue", "angular", "svelte"]):
                # Detect other frameworks
                for fw in ["vue", "angular", "svelte"]:
                    if fw in all_content:
                        skills.append({
                            "category": "framework",
                            "skill": fw.capitalize(),
                            "level": "beginner",
                            "gap": "Could use more advanced patterns",
                            "resource": f"{fw.capitalize()} documentation",
                            "priority": "medium"
                        })
                        break
            
            # Testing
            if "test" not in all_content and "spec" not in all_content:
                skills.append({
                    "category": "pattern",
                    "skill": "Testing",
                    "level": "beginner",
                    "gap": "No tests found",
                    "resource": "pytest documentation",
                    "priority": "high"
                })
            
            result["skills"] = skills
            if skills:
                high_priority = sum(1 for s in skills if s["priority"] == "high")
                result["score"] = max(50, 75 - high_priority * 10)
        
        return result
    
    def _create_fallback_analysis(self, index_data: Dict, chunks: List[Dict]) -> Dict[str, Any]:
        """Create fallback analysis when AI fails completely."""
        review_logger = logging.getLogger("ai.review")
        review_logger.info("Creating fallback analysis due to AI failures")
        
        # Analyze chunks heuristically
        fallback_result = self._heuristic_analysis(chunks, "quality")
        
        # Ensure we have at least one item in each category
        if not fallback_result.get("issues"):
            fallback_result["issues"] = [{
                "type": "general",
                "severity": "low",
                "message": "Limited analysis available due to AI service issues",
                "file": chunks[0].get("file_path", "unknown") if chunks else "unknown",
                "line": 1,
                "suggestion": "Manual code review recommended"
            }]
        
        if not fallback_result.get("security"):
            fallback_result["security"] = [{
                "type": "security",
                "severity": "low", 
                "message": "Security analysis limited due to AI service issues",
                "file": chunks[0].get("file_path", "unknown") if chunks else "unknown",
                "line": 1,
                "suggestion": "Manual security review recommended"
            }]
        
        if not fallback_result.get("architecture"):
            fallback_result["architecture"] = [{
                "type": "architecture",
                "severity": "low",
                "message": "Architecture analysis limited due to AI service issues", 
                "file": chunks[0].get("file_path", "unknown") if chunks else "unknown",
                "line": 1,
                "suggestion": "Manual architecture review recommended"
            }]
        
        if not fallback_result.get("skills"):
            fallback_result["skills"] = [{
                "category": "tool",
                "skill": "AI Analysis",
                "level": "beginner",
                "gap": "AI analysis services unavailable",
                "resource": "Manual code review practices",
                "priority": "medium"
            }]
        
        # Add metadata about fallback
        fallback_result["success"] = True
        fallback_result["fallback_analysis"] = True
        fallback_result["chunks_analyzed"] = len(chunks)
        fallback_result["total_chunks"] = len(index_data.get("chunks", []))
        fallback_result["failed_reviews"] = 4  # All review types failed
        
        review_logger.info(f"Fallback analysis created with score {fallback_result.get('score', 50)}")
        return fallback_result

# Global review engine instance
review_engine = ReviewEngine()
