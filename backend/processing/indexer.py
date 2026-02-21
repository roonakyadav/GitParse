"""
Repository indexing for searchable code structure.

Creates comprehensive index of files, chunks, dependencies, and metadata.
Optimized for AI processing and analysis workflows.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from .parser import parse_file
from .chunker import chunk_ast
from .tokenizer import count_tokens, estimate_chunk_tokens
from .dependency import build_dependency_map

logger = logging.getLogger(__name__)


def create_repository_index(repo_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a comprehensive index from repository analysis.
    
    Args:
        repo_analysis: Phase 1 repository analysis output
        
    Returns:
        Comprehensive repository index with chunks, dependencies, and metadata
    """
    logger.info(f"Creating repository index for {repo_analysis.get('repo', 'unknown')}")
    
    start_time = datetime.now()
    
    # Initialize index structure
    index = {
        'repo': repo_analysis.get('repo', 'unknown'),
        'created_at': start_time.isoformat(),
        'total_files': 0,
        'total_chunks': 0,
        'total_tokens': 0,
        'max_tokens': 0,
        'min_tokens': float('inf'),
        'avg_tokens': 0,
        'files': [],
        'chunks': [],
        'dependencies': {},
        'languages': {},
        'file_types': {},
        'processing_stats': {}
    }
    
    # Process each file
    files_data = []
    chunks_data = []
    parsed_files = []
    
    for file_info in repo_analysis.get('files', []):
        try:
            # Skip binary files and very large files
            if _should_skip_file(file_info):
                continue
            
            # Parse file content (simulate for now - in real implementation, download content)
            parsed = _simulate_file_parsing(file_info)
            if not parsed:
                continue
            
            # Create chunks
            chunks = chunk_ast(parsed)
            
            # Fallback: if no chunks created, create raw text chunks
            if not chunks:
                logger.warning(f"No chunks created for {file_info['path']}, using fallback chunking")
                chunks = _create_fallback_chunks(file_info, parsed)
            
            # Ensure at least one chunk if file has content
            if not chunks and file_info.get('size', 0) > 0:
                logger.warning(f"Still no chunks for {file_info['path']}, creating minimal chunk")
                chunks = [_create_minimal_chunk(file_info, parsed)]
            
            # Add file metadata
            file_entry = {
                'path': file_info['path'],
                'size': file_info['size'],
                'language': file_info['language'],
                'download_url': file_info['download_url'],
                'chunks_count': len(chunks),
                'parsed_data': parsed,
                'processing_status': 'success'
            }
            
            files_data.append(file_entry)
            parsed_files.append(file_entry)
            chunks_data.extend(chunks)
            
            # Update statistics
            index['languages'][file_info['language']] = index['languages'].get(file_info['language'], 0) + 1
            
            # Update file types
            ext = file_info['path'].split('.')[-1] if '.' in file_info['path'] else 'no_extension'
            index['file_types'][ext] = index['file_types'].get(ext, 0) + 1
            
        except Exception as e:
            logger.error(f"Failed to process file {file_info.get('path', 'unknown')}: {e}")
            # Add failed file entry
            file_entry = {
                'path': file_info['path'],
                'size': file_info['size'],
                'language': file_info['language'],
                'download_url': file_info['download_url'],
                'chunks_count': 0,
                'processing_status': 'failed',
                'error': str(e)
            }
            files_data.append(file_entry)
    
    # Build dependency map
    try:
        dependency_map = build_dependency_map(parsed_files)
        index['dependencies'] = dependency_map
    except Exception as e:
        logger.error(f"Failed to build dependency map: {e}")
        index['dependencies'] = {
            'error': str(e),
            'dependency_map': {},
            'reverse_dependency_map': {},
            'language_dependencies': {},
            'graph': {
                'adjacency': {},
                'nodes': [],
                'edges': [],
                'circular_dependencies': [],
                'top_level_files': [],
                'leaf_files': []
            },
            'metrics': {
                'total_files': 0,
                'total_dependencies': 0,
                'average_dependencies_per_file': 0
            },
            'total_files': 0,
            'total_dependencies': 0
        }
    
    # Process chunks and calculate token statistics
    processed_chunks = []
    total_tokens = 0
    max_tokens = 0
    min_tokens = float('inf')
    
    for chunk in chunks_data:
        try:
            # Estimate tokens for chunk
            token_count = estimate_chunk_tokens(chunk)
            
            # Add token information to chunk
            chunk['token_count'] = token_count
            chunk['created_at'] = start_time.isoformat()
            
            processed_chunks.append(chunk)
            
            # Update statistics
            total_tokens += token_count
            max_tokens = max(max_tokens, token_count)
            min_tokens = min(min_tokens, token_count)
            
        except Exception as e:
            logger.error(f"Failed to process chunk: {e}")
            chunk['processing_status'] = 'failed'
            chunk['error'] = str(e)
            processed_chunks.append(chunk)
    
    # Update index statistics
    index['files'] = files_data
    index['chunks'] = processed_chunks
    index['total_files'] = len(files_data)
    index['total_chunks'] = len(processed_chunks)
    index['total_tokens'] = total_tokens
    index['max_tokens'] = max_tokens if max_tokens != float('inf') else 0
    index['min_tokens'] = min_tokens if min_tokens != float('inf') else 0
    index['avg_tokens'] = total_tokens / len(processed_chunks) if processed_chunks else 0
    
    # Add processing statistics
    end_time = datetime.now()
    processing_time = (end_time - start_time).total_seconds()
    
    index['processing_stats'] = {
        'processing_time_seconds': processing_time,
        'files_processed': len([f for f in files_data if f.get('processing_status') == 'success']),
        'files_failed': len([f for f in files_data if f.get('processing_status') == 'failed']),
        'chunks_created': len(processed_chunks),
        'chunks_within_limits': len([c for c in processed_chunks if 300 <= c.get('token_count', 0) <= 800]),
        'chunks_too_large': len([c for c in processed_chunks if c.get('token_count', 0) > 800]),
        'chunks_too_small': len([c for c in processed_chunks if 0 < c.get('token_count', 0) < 300])
    }
    
    logger.info(f"Repository indexing completed in {processing_time:.2f}s")
    logger.info(f"Processed {index['total_files']} files, created {index['total_chunks']} chunks")
    
    # CRITICAL: Ensure we have chunks for analysis
    if index['total_chunks'] == 0:
        logger.error("No chunks were created during indexing!")
        # Create emergency chunks from file list
        emergency_chunks = _create_emergency_chunks(repo_analysis.get('files', []))
        index['chunks'] = emergency_chunks
        index['total_chunks'] = len(emergency_chunks)
        index['processing_stats']['emergency_chunks_created'] = len(emergency_chunks)
        logger.warning(f"Created {len(emergency_chunks)} emergency chunks to prevent analysis failure")
    
    # Final validation
    if index['total_chunks'] == 0:
        raise ValueError("Failed to create any chunks during processing. Cannot proceed with analysis.")
    
    return index


def _should_skip_file(file_info: Dict[str, Any]) -> bool:
    """Determine if a file should be skipped during processing."""
    # Skip very large files (>1MB)
    if file_info.get('size', 0) > 1024 * 1024:
        logger.warning(f"Skipping large file: {file_info.get('path')} ({file_info.get('size')} bytes)")
        return True
    
    # Skip binary files
    binary_extensions = {
        'png', 'jpg', 'jpeg', 'gif', 'bmp', 'svg', 'ico',
        'mp4', 'avi', 'mov', 'wmv', 'flv',
        'mp3', 'wav', 'flac', 'aac',
        'zip', 'tar', 'gz', 'rar', '7z',
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
        'exe', 'dll', 'so', 'dylib',
        'bin', 'dat', 'db', 'sqlite'
    }
    
    file_path = file_info.get('path', '')
    if '.' in file_path:
        ext = file_path.split('.')[-1].lower()
        if ext in binary_extensions:
            logger.debug(f"Skipping binary file: {file_path}")
            return True
    
    return False


def _simulate_file_parsing(file_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Simulate file parsing for demonstration.
    In real implementation, this would download and parse actual file content.
    """
    file_path = file_info.get('path', '')
    language = file_info.get('language', 'text')
    
    # Create a mock parsed structure based on file type and language
    parsed = {
        'file_path': file_path,
        'language': language,
        'functions': [],
        'classes': [],
        'imports': [],
        'globals': [],
        'comments': [],
        'docstrings': []
    }
    
    # Add mock data based on language
    if language == 'python':
        parsed['functions'] = [
            {'name': 'example_function', 'line': 10, 'args': ['param1', 'param2'], 'docstring': 'Example function'},
            {'name': 'main', 'line': 20, 'args': [], 'docstring': 'Main entry point'}
        ]
        parsed['imports'] = [
            {'type': 'import', 'module': 'os', 'line': 1},
            {'type': 'from_import', 'module': 'typing', 'name': 'List', 'line': 2}
        ]
        if 'class' in file_path or 'model' in file_path:
            parsed['classes'] = [
                {'name': 'ExampleClass', 'line': 5, 'methods': ['__init__', 'method1']}
            ]
    
    elif language in ['javascript', 'typescript']:
        parsed['functions'] = [
            {'name': 'exampleFunction', 'line': 10, 'raw': 'function exampleFunction(param1, param2) {}'},
            {'name': 'main', 'line': 20, 'raw': 'const main = () => {}'}
        ]
        parsed['imports'] = [
            {'type': 'import', 'module': 'react', 'line': 1},
            {'type': 'import', 'module': 'lodash', 'line': 2}
        ]
    
    elif language == 'java':
        parsed['classes'] = [
            {
                'name': 'ExampleClass',
                'line': 5,
                'methods': [
                    {'name': 'exampleMethod', 'parameters': ['String param'], 'return_type': 'void'}
                ]
            }
        ]
        parsed['imports'] = [
            {'type': 'import', 'module': 'java.util.List', 'line': 1}
        ]
    
    elif language == 'go':
        parsed['functions'] = [
            {'name': 'exampleFunction', 'line': 10, 'raw': 'func exampleFunction(param1, param2) {}'}
        ]
        parsed['imports'] = [
            {'type': 'import', 'module': 'fmt', 'line': 1}
        ]
        parsed['classes'] = [
            {'name': 'ExampleStruct', 'type': 'struct', 'line': 5}
        ]
    
    return parsed


def search_chunks(index: Dict[str, Any], query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search chunks by content or metadata.
    
    Args:
        index: Repository index
        query: Search query
        limit: Maximum results to return
        
    Returns:
        List of matching chunks
    """
    query_lower = query.lower()
    results = []
    
    for chunk in index.get('chunks', []):
        score = 0
        
        # Search in content
        content = chunk.get('content', '').lower()
        if query_lower in content:
            score += 10
        
        # Search in metadata
        metadata = chunk.get('metadata', {})
        for key, value in metadata.items():
            if isinstance(value, str) and query_lower in value.lower():
                score += 5
            elif isinstance(value, list) and any(query_lower in str(v).lower() for v in value):
                score += 3
        
        if score > 0:
            chunk_result = chunk.copy()
            chunk_result['search_score'] = score
            results.append(chunk_result)
    
    # Sort by score and limit results
    results.sort(key=lambda x: x['search_score'], reverse=True)
    return results[:limit]


def get_chunk_by_id(index: Dict[str, Any], chunk_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific chunk by ID.
    
    Args:
        index: Repository index
        chunk_id: Chunk ID to find
        
    Returns:
        Chunk dictionary or None if not found
    """
    for chunk in index.get('chunks', []):
        if chunk.get('id') == chunk_id:
            return chunk
    return None


def get_file_chunks(index: Dict[str, Any], file_path: str) -> List[Dict[str, Any]]:
    """
    Get all chunks for a specific file.
    
    Args:
        index: Repository index
        file_path: File path to filter by
        
    Returns:
        List of chunks for the file
    """
    return [
        chunk for chunk in index.get('chunks', [])
        if chunk.get('file_path') == file_path
    ]


def export_index(index: Dict[str, Any], format: str = 'json') -> str:
    """
    Export index in specified format.
    
    Args:
        index: Repository index
        format: Export format ('json', 'summary')
        
    Returns:
        Exported string
    """
    if format == 'json':
        return json.dumps(index, indent=2, default=str)
    elif format == 'summary':
        return _generate_summary(index)
    else:
        raise ValueError(f"Unsupported export format: {format}")


def _generate_summary(index: Dict[str, Any]) -> str:
    """Generate a human-readable summary of the index."""
    summary = f"""
Repository Analysis Summary
==========================
Repository: {index.get('repo', 'Unknown')}
Created: {index.get('created_at', 'Unknown')}

File Statistics:
- Total files: {index.get('total_files', 0)}
- Languages: {', '.join(index.get('languages', {}).keys())}
- File types: {', '.join(f"{ext} ({count})" for ext, count in index.get('file_types', {}).items())}

Chunk Statistics:
- Total chunks: {index.get('total_chunks', 0)}
- Total tokens: {index.get('total_tokens', 0):,}
- Average tokens per chunk: {index.get('avg_tokens', 0):.1f}
- Min tokens: {index.get('min_tokens', 0)}
- Max tokens: {index.get('max_tokens', 0)}

Processing Statistics:
- Processing time: {index.get('processing_stats', {}).get('processing_time_seconds', 0):.2f} seconds
- Files processed successfully: {index.get('processing_stats', {}).get('files_processed', 0)}
- Files failed: {index.get('processing_stats', {}).get('files_failed', 0)}
- Chunks within limits (300-800 tokens): {index.get('processing_stats', {}).get('chunks_within_limits', 0)}

Dependencies:
- Total dependencies: {index.get('dependencies', {}).get('total_dependencies', 0)}
- Circular dependencies: {len(index.get('dependencies', {}).get('graph', {}).get('circular_dependencies', []))}
"""
    
    return summary.strip()


def _create_fallback_chunks(file_info: Dict[str, Any], parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Create fallback chunks by splitting raw content into ~500 token blocks."""
    chunks = []
    file_path = file_info.get('path', '')
    language = parsed.get('language', 'text')
    
    # Create mock content based on file structure
    content_parts = []
    
    # Add imports
    for imp in parsed.get('imports', []):
        if language == 'python':
            if imp.get('type') == 'import':
                line = f"import {imp.get('module', '')}"
                if imp.get('alias'):  # Fix: Use .get() to handle missing alias
                    line += f" as {imp.get('alias')}"
                content_parts.append(line)
            elif imp.get('type') == 'from_import':
                line = f"from {imp.get('module', '')} import {imp.get('name', '')}"
                if imp.get('alias'):  # Fix: Use .get() to handle missing alias
                    line += f" as {imp.get('alias')}"
                content_parts.append(line)
        else:
            content_parts.append(f"// Import: {imp.get('module', '')}")
    
    # Add functions
    for func in parsed.get('functions', []):
        if language == 'python':
            func_content = f"def {func.get('name', 'unknown')}({', '.join(func.get('args', []))}):\n    pass"
        else:
            func_content = f"function {func.get('name', 'unknown')}({', '.join(func.get('args', []))}) {{\n    // TODO: implement\n}}"
        content_parts.append(func_content)
    
    # Add classes
    for cls in parsed.get('classes', []):
        if language == 'python':
            cls_content = f"class {cls.get('name', 'Unknown')}:\n    pass"
        else:
            cls_content = f"class {cls.get('name', 'Unknown')} {{\n    // TODO: implement\n}}"
        content_parts.append(cls_content)
    
    # If no structured content, create generic content
    if not content_parts:
        content_parts = [
            f"// File: {file_path}",
            f"// Language: {language}",
            f"// Size: {file_info.get('size', 0)} bytes",
            "// This is a fallback chunk created when normal chunking failed",
            "// TODO: Review this file for proper analysis"
        ]
    
    # Combine all content
    full_content = '\n\n'.join(content_parts)
    
    # Split into chunks of approximately 500 tokens
    lines = full_content.split('\n')
    target_lines = 50  # Approximate 500 tokens worth of lines
    chunk_id = 1
    
    for i in range(0, len(lines), target_lines):
        chunk_lines = lines[i:i + target_lines]
        chunk_content = '\n'.join(chunk_lines)
        
        chunk = {
            'id': f"{file_path}_fallback_{chunk_id}",
            'type': 'fallback',
            'file_path': file_path,
            'language': language,
            'content': chunk_content,
            'metadata': {
                'file_path': file_path,
                'language': language,
                'chunk_type': 'fallback',
                'chunk_number': chunk_id,
                'created_by': 'fallback_chunker'
            }
        }
        chunks.append(chunk)
        chunk_id += 1
    
    logger.info(f"Created {len(chunks)} fallback chunks for {file_path}")
    return chunks


def _create_minimal_chunk(file_info: Dict[str, Any], parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Create a minimal chunk when all else fails."""
    file_path = file_info.get('path', '')
    language = parsed.get('language', 'text')
    
    content = f"""// Minimal chunk for {file_path}
// Language: {language}
// Size: {file_info.get('size', 0)} bytes
// This file could not be properly chunked for analysis

// File Information:
- Path: {file_path}
- Language: {language}
- Size: {file_info.get('size', 0)} bytes

// Note: This is a safety chunk to ensure analysis can proceed.
// The original file content may need manual review."""
    
    return {
        'id': f"{file_path}_minimal",
        'type': 'minimal',
        'file_path': file_path,
        'language': language,
        'content': content,
        'metadata': {
            'file_path': file_path,
            'language': language,
            'chunk_type': 'minimal',
            'created_by': 'minimal_chunker',
            'reason': 'no_chunks_generated'
        }
    }


def _create_emergency_chunks(files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create emergency chunks from file list when all else fails."""
    chunks = []
    
    if not files:
        # Create a single chunk about the repository
        return [{
            'id': 'emergency_repo_info',
            'type': 'emergency',
            'file_path': 'repository_overview',
            'language': 'text',
            'content': """// Emergency Repository Analysis Chunk
// This chunk was created because no files could be processed.

Repository Analysis Summary:
- No valid files were found for chunking
- This may indicate a repository with only binary files
- Or files that are too large/small for processing

Recommendations:
1. Check if repository contains source code files
2. Verify file sizes are within reasonable limits
3. Review file extensions for supported languages

Note: Manual review of the repository is recommended.""",
            'metadata': {
                'chunk_type': 'emergency',
                'created_by': 'emergency_chunker',
                'reason': 'no_files_processed'
            }
        }]
    
    # Create chunks from file information
    content_lines = [
        "// Emergency Repository Analysis",
        "// Created when normal chunking failed",
        "",
        "Repository Files:",
    ]
    
    for file_info in files[:20]:  # Limit to first 20 files
        file_path = file_info.get('path', 'unknown')
        language = file_info.get('language', 'unknown')
        size = file_info.get('size', 0)
        
        content_lines.extend([
            f"- {file_path} ({language}, {size} bytes)"
        ])
    
    if len(files) > 20:
        content_lines.append(f"- ... and {len(files) - 20} more files")
    
    content_lines.extend([
        "",
        "Analysis Notes:",
        "- Files could not be properly chunked for AI analysis",
        "- This may be due to unsupported file types or parsing errors",
        "- Manual review of the repository is recommended"
    ])
    
    emergency_chunk = {
        'id': 'emergency_file_list',
        'type': 'emergency',
        'file_path': 'file_inventory',
        'language': 'text',
        'content': '\n'.join(content_lines),
        'metadata': {
            'chunk_type': 'emergency',
            'created_by': 'emergency_chunker',
            'total_files': len(files),
            'reason': 'chunking_failed'
        }
    }
    
    chunks.append(emergency_chunk)
    return chunks
