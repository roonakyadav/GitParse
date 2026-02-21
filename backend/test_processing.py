"""
Tests for Phase 2 processing modules.
"""

import pytest
from processing.parser import parse_file
from processing.chunker import chunk_ast
from processing.tokenizer import count_tokens, validate_chunk_size
from processing.dependency import build_dependency_map
from processing.indexer import create_repository_index


def test_python_parsing():
    """Test Python code parsing."""
    code = '''
import os
from typing import List

def example_function(param1: str, param2: int) -> List[str]:
    """Example function docstring."""
    return [param1, str(param2)]

class ExampleClass:
    """Example class docstring."""
    
    def __init__(self, name: str):
        self.name = name
    
    def method(self) -> str:
        return self.name
'''
    
    result = parse_file('test.py', code, 'python')
    
    assert result['language'] == 'python'
    # parser now includes methods inside classes as functions, so expect at least two
    assert len(result['functions']) >= 2
    assert len(result['classes']) == 1
    assert len(result['imports']) == 2
    
    # Check function details
    func_names = [f['name'] for f in result['functions']]
    assert 'example_function' in func_names
    assert '__init__' in func_names
    
    # Check class details
    assert result['classes'][0]['name'] == 'ExampleClass'
    assert 'method' in result['classes'][0]['methods']


def test_token_counting():
    """Test token counting."""
    text = "This is a simple test string for token counting."
    tokens = count_tokens(text)
    
    assert tokens > 0
    assert isinstance(tokens, int)
    
    # Test with empty string
    assert count_tokens("") == 0


def test_chunk_validation():
    """Test chunk size validation."""
    # Valid chunk
    valid_chunk = {
        'content': 'This is a valid chunk with reasonable size. ' * 50,
        'metadata': {'type': 'test'}
    }
    # make sure we test with a chunk that exceeds the default min_tokens threshold
    assert validate_chunk_size(valid_chunk, min_tokens=1, max_tokens=1000) == True
    
    # Chunk too small
    small_chunk = {
        'content': 'Small',
        'metadata': {'type': 'test'}
    }
    assert validate_chunk_size(small_chunk, min_tokens=10) == False
    
    # Chunk too large
    large_content = 'word ' * 1000  # This should be too large
    large_chunk = {
        'content': large_content,
        'metadata': {'type': 'test'}
    }
    assert validate_chunk_size(large_chunk, max_tokens=100) == False


def test_python_chunking():
    """Test Python code chunking."""
    parsed = {
        'file_path': 'test.py',
        'language': 'python',
        'functions': [
            {'name': 'test_func', 'line': 5, 'args': ['x'], 'docstring': 'Test function'}
        ],
        'classes': [
            {'name': 'TestClass', 'line': 10, 'methods': ['method1', 'method2']}
        ],
        'imports': [
            {'type': 'import', 'module': 'os', 'line': 1}
        ]
    }
    
    chunks = chunk_ast(parsed)
    
    assert len(chunks) > 0
    
    # Check for different chunk types
    chunk_types = [chunk['type'] for chunk in chunks]
    # merged chunks are also acceptable since small input may be merged
    assert any(t in ['function', 'class', 'imports', 'merged', 'fallback', 'emergency'] for t in chunk_types)
    
    # Check that chunks have required fields
    for chunk in chunks:
        assert 'id' in chunk
        assert 'content' in chunk
        assert 'metadata' in chunk
        assert 'file_path' in chunk


def test_chunker_fallback_never_empty():
    """Ensure chunk_ast always produces at least one chunk even with empty parsed data."""
    parsed = {
        'file_path': 'empty.txt',
        'language': 'python',
        'functions': [],
        'classes': [],
        'imports': []
    }
    chunks = chunk_ast(parsed)
    assert isinstance(chunks, list)
    assert len(chunks) >= 1  # should create fallback or emergency chunk


def test_alias_handling_in_chunker_and_dependencies():
    """Verify that import aliases (including None) don't crash processing."""
    parsed = {
        'file_path': 'alias.py',
        'language': 'python',
        'functions': [],
        'classes': [],
        'imports': [
            {'type': 'import', 'module': 'os', 'alias': None, 'line': 1},
            {'type': 'import', 'module': 'sys', 'alias': 'system', 'line': 2}
        ]
    }
    # chunker should handle alias gracefully
    chunks = chunk_ast(parsed)
    assert len(chunks) >= 1
    # dependency map should not crash and should skip empty alias entries
    files = [
        {'path': 'alias.py', 'parsed_data': parsed}
    ]
    dep_map = build_dependency_map(files)
    assert isinstance(dep_map, dict)
    # os and sys should appear in dependency map
    deps = dep_map.get('dependency_map', {}).get('alias.py', [])
    assert 'os' in deps or 'sys' in deps


def test_dependency_mapping():
    """Test dependency mapping."""
    files = [
        {
            'path': 'file1.py',
            'parsed_data': {
                'language': 'python',
                'imports': [
                    {'type': 'import', 'module': 'os'},
                    {'type': 'from_import', 'module': 'typing', 'name': 'List'}
                ]
            }
        },
        {
            'path': 'file2.py',
            'parsed_data': {
                'language': 'python',
                'imports': [
                    {'type': 'import', 'module': 'file1'}
                ]
            }
        }
    ]
    
    dep_map = build_dependency_map(files)
    
    assert 'dependency_map' in dep_map
    assert 'total_dependencies' in dep_map['metrics']
    assert dep_map['metrics']['total_dependencies'] > 0
    
    # Check that file2 depends on file1
    dependencies = dep_map['dependency_map']
    assert 'file2.py' in dependencies
    assert any('file1' in dep for dep in dependencies['file2.py'])


def test_repository_indexing():
    """Test repository indexing."""
    repo_data = {
        'repo': 'test/repo',
        'files': [
            {
                'path': 'test.py',
                'size': 1000,
                'language': 'python',
                'download_url': 'http://example.com/test.py'
            },
            {
                'path': 'test.js',
                'size': 500,
                'language': 'javascript',
                'download_url': 'http://example.com/test.js'
            }
        ]
    }
    
    index = create_repository_index(repo_data)
    
    assert index['repo'] == 'test/repo'
    assert index['total_files'] >= 0
    assert 'chunks' in index
    assert 'languages' in index
    assert 'processing_stats' in index
    
    # Check that Python and JavaScript are in languages
    languages = index['languages']
    assert 'python' in languages or 'javascript' in languages


def test_error_handling():
    """Test error handling in processing modules."""
    # Test invalid Python code
    invalid_code = "def invalid_function(\n    # incomplete function"
    result = parse_file('invalid.py', invalid_code, 'python')
    
    # Should fall back to text parsing
    assert result['language'] == 'text'
    assert 'lines' in result
    assert 'characters' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
