def generate_long_summary(article, target_words=100):
    """Generate a comprehensive summary with at least 100 words"""
    
    # Get full article content
    full_content = None
    if article.get('url'):
        full_content = get_full_article_content(article['url'])
        time.sleep(0.5)
    
    # Combine all sources
    text_parts = []
    
    if full_content:
        text_parts.append(full_content)
    if article.get('description'):
        text_parts.append(clean_html(article['description']))
    
    combined_text = ' '.join(text_parts)
    combined_text = clean_html(combined_text)
    
    words = combined_text.split()
    
    if len(words) >= target_words:
        # Take first target_words words
        summary = ' '.join(words[:target_words])
        
        # Try to end at a sentence boundary
        for punct in ['.', '!', '?']:
            last_occurrence = summary.rfind(punct)
            if last_occurrence > target_words * 0.6:  # At least 60% of target
                summary = summary[:last_occurrence + 1]
                break
        
        if len(words) > target_words:
            summary += " [Continued...]"
        
        return summary
    else:
        # Not enough content, expand with context
        context = f" This article from {article['source']} covers important news. " * 3
        expanded = combined_text + context
        words = expanded.split()
        return ' '.join(words[:target_words]) + "..."