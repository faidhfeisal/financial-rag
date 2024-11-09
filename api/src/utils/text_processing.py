from typing import List, Dict, Any
import tiktoken
from ..core.config import get_settings

settings = get_settings()

def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken"""
    try:
        encoding = tiktoken.encoding_for_model(settings.EMBEDDING_MODEL)
        return len(encoding.encode(text))
    except Exception as e:
        # Fallback to approximate token count
        return len(text.split())

def chunk_text(
    text: str,
    max_tokens: int = None,
    overlap_tokens: int = None
) -> List[Dict[str, Any]]:
    """Split text into chunks with metadata"""
    max_tokens = max_tokens or settings.CHUNK_MAX_TOKENS
    overlap_tokens = overlap_tokens or settings.CHUNK_OVERLAP_TOKENS
    
    encoding = tiktoken.encoding_for_model(settings.EMBEDDING_MODEL)
    tokens = encoding.encode(text)
    
    chunks = []
    start = 0
    
    while start < len(tokens):
        # Find end of chunk
        end = start + max_tokens
        
        if end < len(tokens):
            # Try to find a natural break point
            decoded_chunk = encoding.decode(tokens[end-20:end+20])
            break_points = [
                decoded_chunk.rfind('.'),
                decoded_chunk.rfind('!'),
                decoded_chunk.rfind('?'),
                decoded_chunk.rfind('\n'),
                decoded_chunk.rfind(' ')
            ]
            
            # Use the latest valid break point
            for point in break_points:
                if point != -1:
                    end = end - (20 - point)
                    break
        
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)
        
        chunks.append({
            "text": chunk_text.strip(),
            "token_count": len(chunk_tokens),
            "start_char": len(encoding.decode(tokens[:start])),
            "end_char": len(encoding.decode(tokens[:end]))
        })
        
        # Move start position, accounting for overlap
        start = end - overlap_tokens
    
    return chunks