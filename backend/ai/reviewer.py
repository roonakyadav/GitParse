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
        self.max_chunks_per_request = 15
        # Cache disabled - all AI calls will be fresh
        pass

    # Cache methods removed - caching is disabled
    
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
                    elif chunk_id == 'GLOBAL':
                        # For global analysis, keep the issue but mark appropriately
                        updated_issue['file'] = 'Cross-file analysis'
                        updated_issue['lines'] = 'N/A'
                        updated_issue['snippet'] = 'Cross-file analysis'
                    else:
                        # If no specific chunk_id, or chunk_id not found in mapping, mark as global analysis
                        updated_issue['file'] = 'Cross-file analysis'
                        updated_issue['lines'] = 'N/A'
                        updated_issue['snippet'] = 'Cross-file analysis'
                        updated_issue['chunk_id'] = 'GLOBAL'
                    
                    updated_issues.append(updated_issue)
                
                result[issue_type] = updated_issues
        
        return result
    
    # Cache validation removed - caching is disabled
    
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
        
        # Cache disabled - always run fresh AI analysis
        review_logger.info("Running fresh AI analysis (cache disabled)")
        
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
            
            # Cache disabled - do not store results
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
            
            # Check if results are empty and trigger heuristic analysis if needed
            all_empty = all(
                len(result.get("issues", [])) == 0 and 
                len(result.get("security", [])) == 0 and 
                len(result.get("architecture", [])) == 0 and 
                len(result.get("skills", [])) == 0
                for result in valid_results
            )
            
            if all_empty:
                review_logger.warning("All analysis results are empty, applying heuristic analysis")
                heuristic_results = []
                for review_type in review_types:
                    heuristic_result = self._heuristic_analysis(important_chunks, review_type)
                    heuristic_results.append(heuristic_result)
                
                # Merge heuristic results with existing results
                for i, heuristic_result in enumerate(heuristic_results):
                    if review_types[i] in ["quality", "security", "architecture", "skills"]:
                        valid_results[i] = heuristic_result
            
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
            
            # Apply heuristic analysis to supplement any remaining empty sections
            if len(final_result.issues) == 0:
                review_logger.info("Applying heuristic analysis for quality issues")
                heuristic_quality = self._heuristic_analysis(important_chunks, "quality")
                final_result.issues.extend([Issue(**issue) for issue in heuristic_quality.get("issues", [])])
            
            if len(final_result.security) == 0:
                review_logger.info("Applying heuristic analysis for security issues")
                heuristic_security = self._heuristic_analysis(important_chunks, "security")
                final_result.security.extend([SecurityIssue(**issue) for issue in heuristic_security.get("security", [])])
            
            if len(final_result.architecture) == 0:
                review_logger.info("Applying heuristic analysis for architecture issues")
                heuristic_architecture = self._heuristic_analysis(important_chunks, "architecture")
                final_result.architecture.extend([ArchitectureIssue(**issue) for issue in heuristic_architecture.get("architecture", [])])
            
            if len(final_result.skills) == 0:
                review_logger.info("Applying heuristic analysis for skills")
                heuristic_skills = self._heuristic_analysis(important_chunks, "skills")
                final_result.skills.extend([SkillGap(**skill) for skill in heuristic_skills.get("skills", [])])
            
            # Calculate individual scores for breakdown
            code_quality_score = self._calculate_component_score(final_result.issues, "quality")
            security_score = self._calculate_component_score(final_result.security, "security")
            architecture_score = self._calculate_component_score(final_result.architecture, "architecture")
            skills_score = self._calculate_component_score(final_result.skills, "skills")
            
            # Calculate overall score as weighted average
            overall_score = self._calculate_overall_score(
                code_quality_score, 
                security_score, 
                architecture_score, 
                skills_score
            )
            
            # Create score breakdown
            score_breakdown = {
                "code_quality": code_quality_score,
                "security": security_score,
                "architecture": architecture_score,
                "skills": skills_score
            }
            
            # Log the breakdown for transparency
            review_logger.info(f"Score breakdown: {score_breakdown}")
            review_logger.info(f"Overall score: {overall_score}")
            
            # Generate project resume summary
            project_resume = await self._generate_project_resume(
                overall_score,
                score_breakdown,
                final_result.issues,
                final_result.security,
                final_result.architecture,
                final_result.skills
            )
            review_logger.info("Generated project resume summary")
            
            # Convert to dict for JSON response
            response_data = {
                "success": True,
                "issues": [issue.dict() for issue in final_result.issues],
                "security": [issue.dict() for issue in final_result.security],
                "architecture": [issue.dict() for issue in final_result.architecture],
                "skills": [skill.dict() for skill in final_result.skills],
                "score": overall_score,
                "score_breakdown": score_breakdown,
                "project_resume": project_resume,
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
                content = chunk.get("content", "")
                file_path = chunk.get("file", "unknown")
                start_line = chunk.get("start_line", 1)
                
                # Check for missing docstrings in functions
                if "def " in content and ('"""' not in content and "'''" not in content):
                    issues.append({
                        "type": "quality",
                        "severity": "low",
                        "message": "Missing function docstring",
                        "file": file_path,
                        "line": start_line,
                        "suggestion": "Add docstring to document function purpose and parameters"
                    })
                
                # Check for inconsistent naming (using basic patterns)
                import re
                snake_case_pattern = r'def [a-z_][a-zA-Z0-9_]*\('
                camel_case_pattern = r'def [a-zA-Z][a-zA-Z0-9]*\('
                if re.search(snake_case_pattern, content) and re.search(camel_case_pattern, content):
                    issues.append({
                        "type": "quality",
                        "severity": "low",
                        "message": "Inconsistent naming convention detected",
                        "file": file_path,
                        "line": start_line,
                        "suggestion": "Choose one naming convention and stick to it throughout the codebase"
                    })
                
                # Check for missing type hints
                def_without_hints = re.findall(r'def ([^:]+)\(([^)]*)\):', content)
                for func_match in def_without_hints:
                    params = func_match[1]
                    if ':' not in params and '->' not in content:
                        issues.append({
                            "type": "quality",
                            "severity": "low",
                            "message": "Missing type hints in function signature",
                            "file": file_path,
                            "line": start_line,
                        	"suggestion": "Add type hints to improve code readability and maintainability"
                        })
                
                # Check for TODO comments
                if "todo" in content.lower() or "fixme" in content.lower():
                    issues.append({
                        "type": "quality",
                        "severity": "medium",
                        "message": "TODO/FIXME comments found",
                        "file": file_path,
                        "line": start_line,
                        "suggestion": "Complete TODO items or remove comments"
                    })
                
                # Check for missing error handling
                if "def " in content and "try:" not in content and "except" not in content:
                    issues.append({
                        "type": "quality",
                        "severity": "medium",
                        "message": "Function may lack error handling",
                        "file": file_path,
                        "line": start_line,
                        "suggestion": "Consider adding try-catch blocks"
                    })
                
                # Check for long functions
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
            
            result["issues"] = issues
            if issues:
                result["score"] = max(50, 75 - len(issues) * 5)
        
        elif review_type == "security":
            security = []
            
            for chunk in chunks:
                content = chunk.get("content", "").lower()
                file_path = chunk.get("file", "unknown")
                start_line = chunk.get("start_line", 1)
                
                # Check for missing logging
                if any(word in content for word in ["error", "exception", "fail", "invalid"]):
                    if "log" not in content and "print(" not in content:
                        security.append({
                            "type": "security",
                            "severity": "low",
                            "message": "Missing logging for error conditions",
                            "file": file_path,
                            "line": start_line,
                            "cwe": "CWE-565",
                            "suggestion": "Add proper logging for error conditions"
                        })
                
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
            
            # Check for README depth
            has_readme = any('readme' in chunk.get('file', '').lower() for chunk in chunks)
            if not has_readme:
                architecture.append({
                    "type": "architecture",
                    "severity": "low",
                    "message": "Missing or inadequate documentation",
                    "file": "README.md",
                    "line": 1,
                    "principle": "Documentation",
                    "suggestion": "Add comprehensive README with project structure, setup instructions, and usage examples"
                })
            
            # Check for test directory
            has_tests = any('test' in chunk.get('file', '').lower() for chunk in chunks)
            if not has_tests:
                architecture.append({
                    "type": "architecture",
                    "severity": "medium",
                    "message": "No tests detected in codebase",
                    "file": "tests/",
                    "line": 1,
                    "principle": "Testability",
                    "suggestion": "Create comprehensive unit and integration tests"
                })
            
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
            
            # Check for missing type hints overall
            if ":" not in all_content and "->" not in all_content:
                skills.append({
                    "category": "language",
                    "skill": "Type Hints",
                    "level": "beginner",
                    "gap": "No type hints detected",
                    "resource": "Python typing documentation",
                    "priority": "medium"
                })
            
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
            
            # Testing skills
            if "test" not in all_content and "spec" not in all_content:
                skills.append({
                    "category": "pattern",
                    "skill": "Testing",
                    "level": "beginner",
                    "gap": "No tests found",
                    "resource": "pytest documentation",
                    "priority": "high"
                })
            
            # Error handling skills
            if "try" not in all_content and "except" not in all_content:
                skills.append({
                    "category": "pattern",
                    "skill": "Error Handling",
                    "level": "beginner",
                    "gap": "No error handling patterns found",
                    "resource": "Python exception handling best practices",
                    "priority": "high"
                })
            
            result["skills"] = skills
            if skills:
                high_priority = sum(1 for s in skills if s["priority"] == "high")
                result["score"] = max(50, 75 - high_priority * 10)
        
        return result
    
    def _calculate_component_score(self, items: List, component_type: str) -> float:
        """Calculate individual component score (0-100) based on issues found."""
        if not items:
            return 90.0  # High score when no issues found
        
        # Count issues by severity
        high_count = sum(1 for item in items if getattr(item, "severity", getattr(item, "priority", "low")) == "high")
        medium_count = sum(1 for item in items if getattr(item, "severity", getattr(item, "priority", "low")) == "medium")
        low_count = sum(1 for item in items if getattr(item, "severity", getattr(item, "priority", "low")) == "low")
        
        # Calculate base score (start high, deduct for issues)
        base_score = 95.0
        score = base_score - (high_count * 15) - (medium_count * 8) - (low_count * 3)
        
        # Ensure score is between 0 and 100
        return max(0.0, min(100.0, score))
    
    def _calculate_overall_score(self, code_quality: float, security: float, architecture: float, skills: float) -> float:
        """Calculate overall score as weighted average of component scores."""
        # Weighted average: quality(30%), security(25%), architecture(25%), skills(20%)
        overall = (code_quality * 0.30 + 
                  security * 0.25 + 
                  architecture * 0.25 + 
                  skills * 0.20)
        return round(overall, 1)
    
    async def _generate_project_resume(self, overall_score: float, score_breakdown: dict, issues: list, security: list, architecture: list, skills: list) -> str:
        """Generate professional recruiter-style project resume summary."""
        from .client import get_groq_client
        from .prompts import RESUME_SUMMARY_PROMPT, SYSTEM_PROMPT
        
        review_logger = logging.getLogger("ai.review")
        review_logger.info("Generating project resume summary")
        
        try:
            # Create summaries of each analysis area
            issues_summary = self._summarize_issues(issues)
            skills_summary = self._summarize_skills(skills)
            architecture_summary = self._summarize_architecture(architecture)
            
            # Format the prompt with analysis data
            prompt = RESUME_SUMMARY_PROMPT.format(
                system_prompt=SYSTEM_PROMPT,
                overall_score=overall_score,
                score_breakdown=score_breakdown,
                issues_summary=issues_summary,
                skills_summary=skills_summary,
                architecture_summary=architecture_summary
            )
            
            # Call Groq API for resume summary
            client = get_groq_client()
            response = await client.call_groq(prompt)
            
            # Parse the response to extract project resume
            import json
            try:
                parsed_response = json.loads(response)
                project_resume = parsed_response.get("project_resume", "")
                if project_resume and len(project_resume.strip()) > 0:
                    # Validate length (120-180 words)
                    word_count = len(project_resume.split())
                    if word_count < 120:
                        review_logger.warning(f"Project resume too short: {word_count} words")
                    elif word_count > 180:
                        review_logger.warning(f"Project resume too long: {word_count} words")
                    
                    review_logger.info(f"Successfully generated project resume: {word_count} words")
                    return project_resume.strip()
            except json.JSONDecodeError:
                review_logger.error("Failed to parse resume summary JSON response")
                pass
            
        except Exception as e:
            review_logger.error(f"Failed to generate project resume: {str(e)}", exc_info=True)
            pass
        
        # Fallback: generate a reasonable summary programmatically
        return self._generate_fallback_resume(overall_score, score_breakdown)
    
    def _summarize_issues(self, issues: list) -> str:
        """Create a summary of code quality issues."""
        if not issues:
            return "No significant code quality issues identified. Demonstrates clean coding practices."
        
        high_count = sum(1 for issue in issues if getattr(issue, "severity", "low") == "high")
        medium_count = sum(1 for issue in issues if getattr(issue, "severity", "low") == "medium")
        low_count = sum(1 for issue in issues if getattr(issue, "severity", "low") == "low")
        
        summary = f"Identified {len(issues)} code quality items: "
        if high_count > 0:
            summary += f"{high_count} high priority, "
        if medium_count > 0:
            summary += f"{medium_count} medium priority, "
        if low_count > 0:
            summary += f"{low_count} low priority issues. "
        
        summary += "Focus areas include maintainability and code standards."
        return summary
    
    def _summarize_skills(self, skills: list) -> str:
        """Create a summary of skills analysis."""
        if not skills:
            return "Demonstrates solid technical foundation with established practices."
        
        high_priority = sum(1 for skill in skills if getattr(skill, "priority", "low") == "high")
        categories = list(set(getattr(skill, "category", "general") for skill in skills))
        
        summary = f"Analysis identified {len(skills)} skill development opportunities "
        if high_priority > 0:
            summary += f"({high_priority} high priority). "
        else:
            summary += ". "
        
        if categories:
            summary += f"Key areas: {', '.join(categories[:3])}. "
        
        summary += "Shows commitment to continuous learning and improvement."
        return summary
    
    def _summarize_architecture(self, architecture: list) -> str:
        """Create a summary of architecture feedback."""
        if not architecture:
            return "Well-structured architecture with good design principles demonstrated."
        
        high_count = sum(1 for item in architecture if getattr(item, "severity", "low") == "high")
        principles = list(set(getattr(item, "principle", "general") for item in architecture))
        
        summary = f"Architecture review identified {len(architecture)} structural considerations "
        if high_count > 0:
            summary += f"({high_count} high priority). "
        else:
            summary += ". "
        
        if principles:
            summary += f"Key principles: {', '.join(principles[:2])}. "
        
        summary += "Reflects thoughtful approach to system design."
        return summary
    
    def _generate_fallback_resume(self, overall_score: float, score_breakdown: dict) -> str:
        """Generate fallback resume summary when AI fails."""
        review_logger = logging.getLogger("ai.review")
        review_logger.info("Generating fallback project resume summary")
        
        # Create a professional summary based on scores
        quality_desc = "strong" if score_breakdown["code_quality"] >= 80 else "solid" if score_breakdown["code_quality"] >= 60 else "developing"
        security_desc = "robust" if score_breakdown["security"] >= 80 else "adequate" if score_breakdown["security"] >= 60 else "basic"
        arch_desc = "well-structured" if score_breakdown["architecture"] >= 80 else "organized" if score_breakdown["architecture"] >= 60 else "functional"
        skills_desc = "advanced" if score_breakdown["skills"] >= 80 else "competent" if score_breakdown["skills"] >= 60 else "emerging"
        
        summary = f"This project demonstrates {quality_desc} development practices with {security_desc} security implementation. "
        summary += f"The {arch_desc} architecture reflects {skills_desc} technical capabilities. "
        summary += "Shows attention to code quality, security considerations, and maintainable design patterns. "
        summary += "Well-suited for production environments with opportunities for further enhancement."
        
        return summary.strip()
    
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
        
        # Calculate fallback scores
        code_quality_score = self._calculate_component_score(fallback_result.get("issues", []), "quality")
        security_score = self._calculate_component_score(fallback_result.get("security", []), "security")
        architecture_score = self._calculate_component_score(fallback_result.get("architecture", []), "architecture")
        skills_score = self._calculate_component_score(fallback_result.get("skills", []), "skills")
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(
            code_quality_score, 
            security_score, 
            architecture_score, 
            skills_score
        )
        
        # Create score breakdown
        score_breakdown = {
            "code_quality": code_quality_score,
            "security": security_score,
            "architecture": architecture_score,
            "skills": skills_score
        }
        
        # Generate project resume for fallback
        project_resume = self._generate_fallback_resume(overall_score, score_breakdown)
        
        # Add metadata about fallback
        fallback_result["success"] = True
        fallback_result["fallback_analysis"] = True
        fallback_result["chunks_analyzed"] = len(chunks)
        fallback_result["total_chunks"] = len(index_data.get("chunks", []))
        fallback_result["failed_reviews"] = 4  # All review types failed
        fallback_result["score"] = overall_score
        fallback_result["score_breakdown"] = score_breakdown
        fallback_result["project_resume"] = project_resume
        
        review_logger.info(f"Fallback analysis created with score {overall_score}")
        review_logger.info(f"Score breakdown: {score_breakdown}")
        review_logger.info("Generated fallback project resume summary")
        return fallback_result

# Global review engine instance
review_engine = ReviewEngine()
