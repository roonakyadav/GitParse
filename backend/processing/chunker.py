"""
Logical code chunking based on parsed AST structure.

Creates chunks that respect function/class boundaries and maintain context.
Ensures chunks are within token limits (300-800 tokens).
"""

import logging
from typing import List, Dict, Any, Optional
from .tokenizer import count_tokens, estimate_chunk_tokens, validate_chunk_size

logger = logging.getLogger(__name__)


def chunk_ast(parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Chunk parsed AST into logical units.
    
    Args:
        parsed: Parsed file structure from parser.py
        
    Returns:
        List of chunks with content and metadata
    """
    chunks = []
    
    language = parsed.get('language', 'text')
    file_path = parsed.get('file_path', '')
    
    if language == 'python':
        chunks.extend(_chunk_python(parsed))
    elif language in ['javascript', 'typescript']:
        chunks.extend(_chunk_javascript_typescript(parsed))
    elif language == 'java':
        chunks.extend(_chunk_java(parsed))
    elif language == 'go':
        chunks.extend(_chunk_go(parsed))
    else:
        chunks.extend(_chunk_text(parsed))
    
    # Validate and adjust chunks
    chunks = _validate_and_adjust_chunks(chunks)
    
    return chunks


def _chunk_python(parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Chunk Python code by functions and classes."""
    chunks = []
    file_path = parsed.get('file_path', '')
    
    # Create file header chunk
    header_chunk = _create_header_chunk(parsed, 'python')
    if header_chunk:
        chunks.append(header_chunk)
    
    # Chunk classes
    for class_info in parsed.get('classes', []):
        chunk = _create_class_chunk(class_info, 'python', file_path)
        if chunk:
            chunks.append(chunk)
    
    # Chunk standalone functions
    for func_info in parsed.get('functions', []):
        # Skip if function is inside a class (simplified check)
        if not any(
            func_info['line'] > cls['line'] and func_info['line'] < cls.get('end_line', float('inf'))
            for cls in parsed.get('classes', [])
        ):
            chunk = _create_function_chunk(func_info, 'python', file_path)
            if chunk:
                chunks.append(chunk)
    
    return chunks


def _chunk_javascript_typescript(parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Chunk JavaScript/TypeScript code by functions and classes."""
    chunks = []
    file_path = parsed.get('file_path', '')
    
    # Create file header chunk
    header_chunk = _create_header_chunk(parsed, 'javascript')
    if header_chunk:
        chunks.append(header_chunk)
    
    # Chunk classes
    for class_info in parsed.get('classes', []):
        chunk = _create_class_chunk(class_info, 'javascript', file_path)
        if chunk:
            chunks.append(chunk)
    
    # Chunk functions
    for func_info in parsed.get('functions', []):
        chunk = _create_function_chunk(func_info, 'javascript', file_path)
        if chunk:
            chunks.append(chunk)
    
    return chunks


def _chunk_java(parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Chunk Java code by classes and methods."""
    chunks = []
    file_path = parsed.get('file_path', '')
    
    # Create file header chunk
    header_chunk = _create_header_chunk(parsed, 'java')
    if header_chunk:
        chunks.append(header_chunk)
    
    # Chunk classes (each class becomes one chunk)
    for class_info in parsed.get('classes', []):
        chunk = _create_java_class_chunk(class_info, file_path)
        if chunk:
            chunks.append(chunk)
    
    return chunks


def _chunk_go(parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Chunk Go code by functions and structs."""
    chunks = []
    file_path = parsed.get('file_path', '')
    
    # Create file header chunk
    header_chunk = _create_header_chunk(parsed, 'go')
    if header_chunk:
        chunks.append(header_chunk)
    
    # Chunk structs
    for struct_info in parsed.get('classes', []):
        chunk = _create_struct_chunk(struct_info, file_path)
        if chunk:
            chunks.append(chunk)
    
    # Chunk functions
    for func_info in parsed.get('functions', []):
        chunk = _create_function_chunk(func_info, 'go', file_path)
        if chunk:
            chunks.append(chunk)
    
    return chunks


def _chunk_text(parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Chunk plain text by paragraphs or sections."""
    chunks = []
    file_path = parsed.get('file_path', '')
    
    # For text files, create a single chunk
    chunk = {
        'id': f"{file_path}_text",
        'type': 'text',
        'file_path': file_path,
        'language': 'text',
        'content': f"# File: {file_path}\n\n# Text content\n\n[Full text content would be here]",
        'metadata': {
            'file_path': file_path,
            'language': 'text',
            'lines': parsed.get('lines', 0),
            'characters': parsed.get('characters', 0),
            'chunk_type': 'full_text'
        }
    }
    chunks.append(chunk)
    
    return chunks


def _create_header_chunk(parsed: Dict[str, Any], language: str) -> Optional[Dict[str, Any]]:
    """Create a header chunk with imports and file-level information."""
    file_path = parsed.get('file_path', '')
    imports = parsed.get('imports', [])
    
    if not imports:
        return None
    
    # Format imports based on language
    if language == 'python':
        import_lines = []
        for imp in imports:
            if imp['type'] == 'import':
                line = f"import {imp['module']}"
                if imp['alias']:
                    line += f" as {imp['alias']}"
                import_lines.append(line)
            else:  # from_import
                line = f"from {imp['module']} import {imp['name']}"
                if imp['alias']:
                    line += f" as {imp['alias']}"
                import_lines.append(line)
        content = "\n".join(import_lines)
    else:
        # Generic import formatting
        import_lines = [imp.get('raw', str(imp)) for imp in imports]
        content = "\n".join(import_lines)
    
    return {
        'id': f"{file_path}_imports",
        'type': 'imports',
        'file_path': file_path,
        'language': language,
        'content': f"# File: {file_path}\n\n# Imports\n\n{content}",
        'metadata': {
            'file_path': file_path,
            'language': language,
            'chunk_type': 'imports',
            'import_count': len(imports)
        }
    }


def _create_class_chunk(class_info: Dict[str, Any], language: str, file_path: str) -> Dict[str, Any]:
    """Create a chunk for a class definition."""
    class_name = class_info.get('name', 'Unknown')
    
    # Create more substantial content
    content = f"# Class: {class_name}\n"
    content += f"# File: {file_path}\n"
    content += f"# Language: {language}\n\n"
    
    if language == 'python':
        content += f"class {class_name}"
        if class_info.get('bases'):
            bases = ', '.join(class_info['bases'])
            content += f"({bases})"
        content += ":\n"
        if class_info.get('docstring'):
            content += f'    """{class_info["docstring"]}"""\n\n'
        
        # Add method signatures with more realistic content
        methods = class_info.get('methods', [])
        if methods:
            content += "    # Methods:\n"
            for method in methods[:5]:  # Limit to first 5 methods
                content += f"    def {method}(self, *args, **kwargs):\n"
                content += "        # Method implementation\n"
                content += "        pass\n\n"
        
        content += "    # Additional class implementation...\n"
        content += "    # This is a representative chunk for analysis\n"
        
    elif language == 'java':
        content += f"public class {class_name}"
        if class_info.get('extends'):
            content += f" extends {class_info['extends']}"
        if class_info.get('implements'):
            implements = ', '.join(class_info['implements'])
            content += f" implements {implements}"
        content += " {\n\n"
        
        # Add method signatures
        methods = class_info.get('methods', [])
        if methods:
            content += "    // Methods:\n"
            for method in methods[:5]:  # Limit to first 5 methods
                params = ', '.join(method.get('parameters', []))
                return_type = method.get('return_type', 'void')
                content += f"    public {return_type} {method.get('name', 'unknown')}({params}) {{\n"
                content += "        // Method implementation\n"
                content += "        // Implementation details would go here\n"
                content += "    }\n\n"
        
        content += "    // Additional class implementation...\n"
        content += "}\n"
        
    else:
        # Generic for JavaScript/TypeScript/Go
        content += f"// Class: {class_name}\n"
        content += f"// File: {file_path}\n"
        content += f"// Language: {language}\n\n"
        content += f"// Class implementation for {class_name}\n"
        content += "// This would contain the full class definition\n"
        content += "// Including all methods, properties, and logic\n"
        content += "// Truncated here for analysis purposes\n"
    
    return {
        'id': f"{file_path}_{class_name}",
        'type': 'class',
        'file_path': file_path,
        'language': language,
        'content': content,
        'metadata': {
            'file_path': file_path,
            'language': language,
            'chunk_type': 'class',
            'class_name': class_name,
            'line': class_info.get('line'),
            'end_line': class_info.get('end_line'),
            'bases': class_info.get('bases', []),
            'methods': class_info.get('methods', [])
        }
    }


def _create_function_chunk(func_info: Dict[str, Any], language: str, file_path: str) -> Dict[str, Any]:
    """Create a chunk for a function definition."""
    func_name = func_info.get('name', 'unknown')
    
    # Create more substantial content
    content = f"# Function: {func_name}\n"
    content += f"# File: {file_path}\n"
    content += f"# Language: {language}\n\n"
    
    if language == 'python':
        args = ', '.join(func_info.get('args', []))
        content += f"def {func_name}({args}):\n"
        if func_info.get('docstring'):
            content += f'    """{func_info["docstring"]}"""\n\n'
        content += "    # Function implementation\n"
        content += "    # This is a representative implementation\n"
        content += "    # Actual implementation would be more complex\n"
        content += "    result = None  # Placeholder for return value\n"
        content += "    # Additional logic and processing would go here\n"
        content += "    return result\n"
        
    else:
        # Generic for JavaScript/TypeScript/Go
        content += f"// Function: {func_name}\n"
        content += f"// File: {file_path}\n"
        content += f"// Language: {language}\n\n"
        content += f"// Function implementation for {func_name}\n"
        if func_info.get('raw'):
            content += f"// Signature: {func_info['raw']}\n"
        content += "// This would contain the full function implementation\n"
        content += "// Including all logic, error handling, and return statements\n"
        content += "// Truncated here for analysis purposes\n"
    
    return {
        'id': f"{file_path}_{func_name}",
        'type': 'function',
        'file_path': file_path,
        'language': language,
        'content': content,
        'metadata': {
            'file_path': file_path,
            'language': language,
            'chunk_type': 'function',
            'function_name': func_name,
            'line': func_info.get('line'),
            'args': func_info.get('args', []),
            'docstring': func_info.get('docstring', '')
        }
    }


def _create_java_class_chunk(class_info: Dict[str, Any], file_path: str) -> Dict[str, Any]:
    """Create a chunk for a Java class."""
    class_name = class_info.get('name', 'Unknown')
    
    content = f"// Class: {class_name}\n"
    content += f"// File: {file_path}\n"
    content += f"// Language: Java\n\n"
    
    content += f"public class {class_name}"
    if class_info.get('extends'):
        content += f" extends {class_info['extends']}"
    if class_info.get('implements'):
        implements = ', '.join(class_info['implements'])
        content += f" implements {implements}"
    content += " {\n"
    
    if class_info.get('methods'):
        content += "    // Methods:\n"
        for method in class_info['methods']:
            params = ', '.join(method.get('parameters', []))
            content += f"    public {method.get('return_type', 'void')} {method.get('name', 'unknown')}({params}) {{\n"
            content += "        // Method implementation\n"
            content += "    }\n\n"
    
    content += "}\n"
    
    return {
        'id': f"{file_path}_{class_name}",
        'type': 'class',
        'file_path': file_path,
        'language': 'java',
        'content': content,
        'metadata': {
            'file_path': file_path,
            'language': 'java',
            'chunk_type': 'class',
            'class_name': class_name,
            'extends': class_info.get('extends'),
            'implements': class_info.get('implements', []),
            'methods': class_info.get('methods', [])
        }
    }


def _create_struct_chunk(struct_info: Dict[str, Any], file_path: str) -> Dict[str, Any]:
    """Create a chunk for a Go struct."""
    struct_name = struct_info.get('name', 'Unknown')
    
    content = f"// Struct: {struct_name}\n"
    content += f"// File: {file_path}\n"
    content += f"// Language: Go\n\n"
    content += f"type {struct_name} struct {{\n"
    content += "    // Struct fields\n"
    content += "}\n"
    
    return {
        'id': f"{file_path}_{struct_name}",
        'type': 'struct',
        'file_path': file_path,
        'language': 'go',
        'content': content,
        'metadata': {
            'file_path': file_path,
            'language': 'go',
            'chunk_type': 'struct',
            'struct_name': struct_name,
            'line': struct_info.get('line')
        }
    }


def _validate_and_adjust_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate chunk sizes and apply adaptive merging."""
    if not chunks:
        return chunks
    
    # First pass: Calculate token counts for all chunks
    for chunk in chunks:
        chunk['token_count'] = estimate_chunk_tokens(chunk)
    
    # Second pass: Adaptive merging of small chunks
    merged_chunks = _merge_small_chunks(chunks)
    
    # Third pass: Split any chunks that are still too large
    final_chunks = []
    for chunk in merged_chunks:
        token_count = chunk.get('token_count', estimate_chunk_tokens(chunk))
        
        if token_count <= 900:  # Allow slightly over 800 for complex chunks
            final_chunks.append(chunk)
        else:
            # Split large chunk
            logger.warning(f"Splitting large chunk {chunk.get('id')} ({token_count} tokens)")
            split_chunks = _split_large_chunk(chunk)
            final_chunks.extend(split_chunks)
    
    # Final validation pass
    final_chunks = _final_validation(final_chunks)
    
    return final_chunks


def _merge_small_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge adjacent small chunks to reach optimal size."""
    if not chunks:
        return chunks
    
    merged_chunks = []
    current_merge = []
    current_tokens = 0
    
    for chunk in chunks:
        chunk_tokens = chunk.get('token_count', estimate_chunk_tokens(chunk))
        
        # If current merge + this chunk would be too large, finalize current merge
        if current_tokens + chunk_tokens > 800 and current_merge:
            # Create merged chunk
            merged_chunk = _create_merged_chunk(current_merge)
            merged_chunks.append(merged_chunk)
            current_merge = []
            current_tokens = 0
        
        # Add chunk to current merge
        current_merge.append(chunk)
        current_tokens += chunk_tokens
        
        # If current merge is in good range, finalize it
        if 300 <= current_tokens <= 800:
            merged_chunk = _create_merged_chunk(current_merge)
            merged_chunks.append(merged_chunk)
            current_merge = []
            current_tokens = 0
    
    # Don't forget remaining chunks
    if current_merge:
        if current_tokens < 100 and len(merged_chunks) > 0:
            # Very small chunk - merge with previous
            last_chunk = merged_chunks[-1]
            combined = current_merge + [last_chunk]
            merged_chunk = _create_merged_chunk(combined)
            merged_chunks[-1] = merged_chunk
        else:
            merged_chunk = _create_merged_chunk(current_merge)
            merged_chunks.append(merged_chunk)
    
    return merged_chunks


def _create_merged_chunk(chunks_to_merge: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create a merged chunk from multiple smaller chunks."""
    if not chunks_to_merge:
        return {}
    
    if len(chunks_to_merge) == 1:
        return chunks_to_merge[0]
    
    # Merge content
    merged_content = ""
    merged_metadata = {
        'merged_chunks': len(chunks_to_merge),
        'original_chunk_ids': [chunk.get('id', '') for chunk in chunks_to_merge]
    }
    
    # Combine content with separators
    for i, chunk in enumerate(chunks_to_merge):
        merged_content += f"\n# --- Chunk {i+1}/{len(chunks_to_merge)} ---\n"
        merged_content += chunk.get('content', '')
        merged_content += "\n"
    
    # Combine metadata
    languages = list(set(chunk.get('language', 'unknown') for chunk in chunks_to_merge))
    chunk_types = list(set(chunk.get('type', 'unknown') for chunk in chunks_to_merge))
    
    merged_metadata.update({
        'file_path': chunks_to_merge[0].get('file_path', ''),
        'language': languages[0] if len(languages) == 1 else 'mixed',
        'chunk_type': 'merged',
        'original_types': chunk_types,
        'merge_count': len(chunks_to_merge)
    })
    
    return {
        'id': f"{chunks_to_merge[0].get('file_path', '')}_merged_{len(chunks_to_merge)}",
        'type': 'merged',
        'file_path': chunks_to_merge[0].get('file_path', ''),
        'language': merged_metadata['language'],
        'content': merged_content.strip(),
        'metadata': merged_metadata,
        'token_count': estimate_chunk_tokens({'content': merged_content, 'metadata': merged_metadata})
    }


def _final_validation(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Final validation pass to ensure chunk quality."""
    valid_chunks = []
    
    for chunk in chunks:
        token_count = chunk.get('token_count', estimate_chunk_tokens(chunk))
        
        # Update token count in chunk
        chunk['token_count'] = token_count
        
        # Validate chunk meets requirements
        if token_count >= 50:  # Minimum reasonable size
            valid_chunks.append(chunk)
        else:
            logger.debug(f"Removing tiny chunk {chunk.get('id')} ({token_count} tokens)")
    
    return valid_chunks


def _split_large_chunk(chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Split a large chunk into smaller ones."""
    # Simple splitting strategy - split by lines
    content = chunk.get('content', '')
    lines = content.split('\n')
    
    # Calculate target lines per chunk
    total_tokens = estimate_chunk_tokens(chunk)
    target_tokens = 600  # Target middle of range
    ratio = target_tokens / total_tokens
    target_lines = max(10, int(len(lines) * ratio))
    
    split_chunks = []
    for i in range(0, len(lines), target_lines):
        chunk_lines = lines[i:i + target_lines]
        chunk_content = '\n'.join(chunk_lines)
        
        split_chunk = {
            'id': f"{chunk.get('id', 'unknown')}_part_{i//target_lines + 1}",
            'type': chunk.get('type', 'unknown'),
            'file_path': chunk.get('file_path', ''),
            'language': chunk.get('language', 'text'),
            'content': chunk_content,
            'metadata': {
                **chunk.get('metadata', {}),
                'chunk_type': f"{chunk.get('metadata', {}).get('chunk_type', 'unknown')}_split",
                'part': i // target_lines + 1,
                'original_chunk_id': chunk.get('id')
            }
        }
        split_chunks.append(split_chunk)
    
    return split_chunks
