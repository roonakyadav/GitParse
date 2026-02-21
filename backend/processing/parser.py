"""
Language-specific code parser using AST and tree-sitter.

Supports Python, JavaScript/TypeScript, Java, and Go parsing.
Falls back to plain text parsing for unsupported languages.
"""

import ast
import re
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import optional dependencies
try:
    import javalang
    JAVA_AVAILABLE = True
except ImportError:
    JAVA_AVAILABLE = False
    logger.warning("javalang not available - Java parsing disabled")

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not available - using fallback token counting")

try:
    import tree_sitter
    import tree_sitter_javascript, tree_sitter_typescript
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    logger.warning("tree-sitter not available - JS/TS parsing disabled")


def parse_file(file_path: str, content: str, language: str) -> Dict[str, Any]:
    """
    Parse a file and extract structural information.
    
    Args:
        file_path: Path to the file
        content: File content
        language: Programming language
        
    Returns:
        Dictionary with parsed structure including functions, classes, imports, etc.
    """
    try:
        if language == 'python':
            return _parse_python(content, file_path)
        elif language in ['javascript', 'typescript']:
            return _parse_javascript_typescript(content, file_path, language)
        elif language == 'java':
            return _parse_java(content, file_path)
        elif language == 'go':
            return _parse_go(content, file_path)
        else:
            return _parse_text(content, file_path)
    except Exception as e:
        logger.error(f"Failed to parse {file_path}: {str(e)}")
        return _parse_text(content, file_path)


def _parse_python(content: str, file_path: str) -> Dict[str, Any]:
    """Parse Python code using AST."""
    try:
        tree = ast.parse(content)
        result = {
            'file_path': file_path,
            'language': 'python',
            'functions': [],
            'classes': [],
            'imports': [],
            'globals': [],
            'comments': [],
            'docstrings': []
        }
        
        # Extract imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    result['imports'].append({
                        'type': 'import',
                        'module': alias.name,
                        'alias': alias.asname,
                        'line': node.lineno
                    })
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    result['imports'].append({
                        'type': 'from_import',
                        'module': module,
                        'name': alias.name,
                        'alias': alias.asname,
                        'line': node.lineno
                    })
        
        # Extract functions and classes
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                result['functions'].append({
                    'name': node.name,
                    'line': node.lineno,
                    'end_line': node.end_lineno,
                    'args': [arg.arg for arg in node.args.args],
                    'docstring': ast.get_docstring(node) or '',
                    'decorators': [d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list]
                })
            elif isinstance(node, ast.ClassDef):
                result['classes'].append({
                    'name': node.name,
                    'line': node.lineno,
                    'end_line': node.end_lineno,
                    'bases': [base.id if isinstance(base, ast.Name) else str(base) for base in node.bases],
                    'docstring': ast.get_docstring(node) or '',
                    'methods': [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                })
        
        # Extract comments and docstrings
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Single line comments
            if '#' in line:
                comment_start = line.find('#')
                comment = line[comment_start + 1:].strip()
                if comment:
                    result['comments'].append({
                        'line': i,
                        'text': comment,
                        'type': 'single_line'
                    })
        
        return result
        
    except SyntaxError as e:
        logger.warning(f"Python syntax error in {file_path}: {e}")
        return _parse_text(content, file_path)


def _parse_javascript_typescript(content: str, file_path: str, language: str) -> Dict[str, Any]:
    """Parse JavaScript/TypeScript using regex (fallback if tree-sitter unavailable)."""
    result = {
        'file_path': file_path,
        'language': language,
        'functions': [],
        'classes': [],
        'imports': [],
        'globals': [],
        'comments': [],
        'docstrings': []
    }
    
    lines = content.split('\n')
    
    # Extract imports
    import_patterns = [
        r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]',
        r'import\s+[\'"]([^\'"]+)[\'"]',
        r'require\([\'"]([^\'"]+)[\'"]\)'
    ]
    
    for i, line in enumerate(lines, 1):
        for pattern in import_patterns:
            match = re.search(pattern, line)
            if match:
                result['imports'].append({
                    'type': 'import',
                    'module': match.group(1),
                    'line': i,
                    'raw': line.strip()
                })
    
    # Extract functions
    function_patterns = [
        r'function\s+(\w+)\s*\(',
        r'const\s+(\w+)\s*=\s*\(',
        r'(\w+)\s*:\s*\([^)]*\)\s*=>',
        r'async\s+function\s+(\w+)\s*\('
    ]
    
    for i, line in enumerate(lines, 1):
        for pattern in function_patterns:
            match = re.search(pattern, line)
            if match:
                result['functions'].append({
                    'name': match.group(1),
                    'line': i,
                    'raw': line.strip()
                })
    
    # Extract classes
    class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?'
    for i, line in enumerate(lines, 1):
        match = re.search(class_pattern, line)
        if match:
            result['classes'].append({
                'name': match.group(1),
                'line': i,
                'extends': match.group(2) if match.group(2) else None,
                'raw': line.strip()
            })
    
    # Extract comments
    for i, line in enumerate(lines, 1):
        if '//' in line:
            comment_start = line.find('//')
            comment = line[comment_start + 2:].strip()
            if comment:
                result['comments'].append({
                    'line': i,
                    'text': comment,
                    'type': 'single_line'
                })
        elif '/*' in line:
            result['comments'].append({
                'line': i,
                'text': line.strip(),
                'type': 'multi_line_start'
            })
    
    return result


def _parse_java(content: str, file_path: str) -> Dict[str, Any]:
    """Parse Java code using javalang."""
    if not JAVA_AVAILABLE:
        return _parse_text(content, file_path)
    
    try:
        tree = javalang.parse.parse(content)
        result = {
            'file_path': file_path,
            'language': 'java',
            'functions': [],
            'classes': [],
            'imports': [],
            'globals': [],
            'comments': [],
            'docstrings': []
        }
        
        # Extract imports
        for import_decl in tree.imports:
            result['imports'].append({
                'type': 'import',
                'module': import_decl.path,
                'static': import_decl.static,
                'wildcard': import_decl.wildcard
            })
        
        # Extract classes and methods
        for path, node in tree:
            if isinstance(node, javalang.tree.ClassDeclaration):
                methods = []
                for method in node.methods:
                    methods.append({
                        'name': method.name,
                        'parameters': [p.name for p in method.parameters],
                        'return_type': str(method.return_type) if method.return_type else 'void'
                    })
                
                result['classes'].append({
                    'name': node.name,
                    'extends': node.extends.name if node.extends else None,
                    'implements': [i.name for i in node.implements] if node.implements else [],
                    'methods': methods
                })
        
        return result
        
    except javalang.parser.JavaSyntaxError as e:
        logger.warning(f"Java syntax error in {file_path}: {e}")
        return _parse_text(content, file_path)


def _parse_go(content: str, file_path: str) -> Dict[str, Any]:
    """Parse Go code using regex patterns."""
    result = {
        'file_path': file_path,
        'language': 'go',
        'functions': [],
        'classes': [],  # Go uses structs, not classes
        'imports': [],
        'globals': [],
        'comments': [],
        'docstrings': []
    }
    
    lines = content.split('\n')
    
    # Extract imports
    for i, line in enumerate(lines, 1):
        if line.strip().startswith('import '):
            import_line = line.strip()[7:].strip()
            result['imports'].append({
                'type': 'import',
                'module': import_line.strip('"'),
                'line': i
            })
        elif line.strip() == 'import':
            # Multi-line import block
            j = i + 1
            import_block = []
            while j < len(lines) and lines[j].strip() != ')':
                if lines[j].strip() and not lines[j].strip().startswith('//'):
                    import_block.append(lines[j].strip())
                j += 1
            result['imports'].append({
                'type': 'import_block',
                'modules': import_block,
                'line': i
            })
    
    # Extract functions
    func_pattern = r'func\s+(\w+)\s*\([^)]*\)(?:\s*[^{]*)?'
    for i, line in enumerate(lines, 1):
        match = re.search(func_pattern, line)
        if match:
            result['functions'].append({
                'name': match.group(1),
                'line': i,
                'raw': line.strip()
            })
    
    # Extract structs (similar to classes)
    struct_pattern = r'type\s+(\w+)\s+struct'
    for i, line in enumerate(lines, 1):
        match = re.search(struct_pattern, line)
        if match:
            result['classes'].append({
                'name': match.group(1),
                'type': 'struct',
                'line': i,
                'raw': line.strip()
            })
    
    # Extract comments
    for i, line in enumerate(lines, 1):
        if line.strip().startswith('//'):
            comment = line.strip()[2:].strip()
            if comment:
                result['comments'].append({
                    'line': i,
                    'text': comment,
                    'type': 'single_line'
                })
    
    return result


def _parse_text(content: str, file_path: str) -> Dict[str, Any]:
    """Fallback plain text parsing."""
    lines = content.split('\n')
    result = {
        'file_path': file_path,
        'language': 'text',
        'functions': [],
        'classes': [],
        'imports': [],
        'globals': [],
        'comments': [],
        'docstrings': [],
        'lines': len(lines),
        'characters': len(content)
    }
    
    # Extract basic comments (common patterns)
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if any(stripped.startswith(prefix) for prefix in ['#', '//', '/*', '*', '<!--']):
            comment = stripped.lstrip('#/ *<!-').strip()
            if comment:
                result['comments'].append({
                    'line': i,
                    'text': comment,
                    'type': 'unknown'
                })
    
    return result
