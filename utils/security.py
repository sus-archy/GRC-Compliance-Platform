"""
Security utilities for the GRC Platform.

This module provides functions to sanitize user input and prevent
security vulnerabilities like XSS (Cross-Site Scripting).
"""

import html
import re
from typing import Optional, Union


def escape_html(text: Optional[str]) -> str:
    """
    Escape HTML special characters to prevent XSS attacks.
    
    This function converts special characters to their HTML entity equivalents:
    - & becomes &amp;
    - < becomes &lt;
    - > becomes &gt;
    - " becomes &quot;
    - ' becomes &#x27;
    
    Args:
        text: The text to escape. If None or empty, returns empty string.
        
    Returns:
        The escaped text safe for rendering in HTML.
    """
    if text is None:
        return ""
    return html.escape(str(text), quote=True)


def escape_for_html_attribute(text: Optional[str]) -> str:
    """
    Escape text for use in HTML attributes.
    
    This is stricter than escape_html and removes any characters
    that could break out of an attribute context.
    
    Args:
        text: The text to escape.
        
    Returns:
        The escaped text safe for use in HTML attributes.
    """
    if text is None:
        return ""
    # First do standard HTML escaping
    escaped = html.escape(str(text), quote=True)
    # Also escape backticks and other potentially dangerous chars
    escaped = escaped.replace("`", "&#x60;")
    return escaped


def sanitize_css_value(value: Optional[str]) -> str:
    """
    Sanitize a value for use in inline CSS.
    
    Removes or escapes characters that could be used for CSS injection.
    
    Args:
        value: The CSS value to sanitize.
        
    Returns:
        The sanitized CSS value.
    """
    if value is None:
        return ""
    
    value = str(value)
    
    # Remove characters that could be used for CSS injection
    # Only allow alphanumeric, spaces, hyphens, underscores, dots, percentages,
    # parentheses (for things like rgb()), commas, hash (for colors)
    sanitized = re.sub(r'[^a-zA-Z0-9\s\-_\.%#(),]', '', value)
    
    # Prevent url() injection - remove any url references
    sanitized = re.sub(r'url\s*\(', '', sanitized, flags=re.IGNORECASE)
    
    # Prevent expression() injection (IE)
    sanitized = re.sub(r'expression\s*\(', '', sanitized, flags=re.IGNORECASE)
    
    # Prevent javascript: in any context
    sanitized = re.sub(r'javascript\s*:', '', sanitized, flags=re.IGNORECASE)
    
    return sanitized


def sanitize_table_name(name: str) -> str:
    """
    Sanitize a table or column name for use in SQL queries.
    
    Only allows alphanumeric characters and underscores.
    This is used when table/column names cannot be parameterized.
    
    Args:
        name: The table or column name to sanitize.
        
    Returns:
        The sanitized name.
        
    Raises:
        ValueError: If the name is empty or contains only invalid characters.
    """
    if not name:
        raise ValueError("Table/column name cannot be empty")
    
    # Only allow alphanumeric and underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '', str(name))
    
    if not sanitized:
        raise ValueError(f"Invalid table/column name: {name}")
    
    # Ensure it doesn't start with a number
    if sanitized[0].isdigit():
        sanitized = '_' + sanitized
    
    return sanitized


def format_safe_html_metric(value: Union[str, int, float], label: str,
                           gradient_start: str = "#667eea",
                           gradient_end: str = "#764ba2") -> str:
    """
    Format a metric value and label into safe HTML for display.
    
    All user content is escaped to prevent XSS.
    
    Args:
        value: The metric value to display.
        label: The label for the metric.
        gradient_start: Start color for the gradient background.
        gradient_end: End color for the gradient background.
        
    Returns:
        Safe HTML string for the metric card.
    """
    safe_value = escape_html(str(value))
    safe_label = escape_html(str(label))
    safe_start = sanitize_css_value(gradient_start)
    safe_end = sanitize_css_value(gradient_end)
    
    return f"""
    <div class="metric-card" style="background: linear-gradient(135deg, {safe_start} 0%, {safe_end} 100%);">
        <h3>{safe_value}</h3>
        <p>{safe_label}</p>
    </div>
    """


def format_safe_source_badge(name: str) -> str:
    """
    Format a source/framework name as a safe HTML badge.
    
    Args:
        name: The source name to display.
        
    Returns:
        Safe HTML string for the badge.
    """
    safe_name = escape_html(str(name))
    return f'<span class="source-badge source-active">{safe_name}</span>'


def format_safe_source_badges(sources: list) -> str:
    """
    Format multiple source/framework names as safe HTML badges.
    
    Args:
        sources: List of source dictionaries with 'short_name' and 'name' keys.
        
    Returns:
        Safe HTML string with all badges.
    """
    badges = []
    for source in sources:
        name = source.get('short_name') or source.get('name', 'Unknown')
        badges.append(format_safe_source_badge(name))
    return " ".join(badges)


def format_safe_tag(text: str, tag_class: str = "tag") -> str:
    """
    Format text as a safe HTML tag/badge.
    
    Args:
        text: The text to display in the tag.
        tag_class: The CSS class for the tag.
        
    Returns:
        Safe HTML string for the tag.
    """
    safe_text = escape_html(str(text))
    safe_class = escape_for_html_attribute(tag_class)
    return f'<span class="{safe_class}">{safe_text}</span>'


def format_safe_div(content: str, class_name: str = "",
                    style: str = "", safe_content: bool = False) -> str:
    """
    Format content in a safe HTML div.
    
    Args:
        content: The content to put in the div.
        class_name: CSS class for the div.
        style: Inline style for the div (will be sanitized).
        safe_content: If True, content is assumed already escaped.
                     If False (default), content will be escaped.
        
    Returns:
        Safe HTML string for the div.
    """
    if not safe_content:
        content = escape_html(content)
    
    safe_class = escape_for_html_attribute(class_name)
    safe_style = sanitize_css_value(style)
    
    class_attr = f' class="{safe_class}"' if safe_class else ""
    style_attr = f' style="{safe_style}"' if safe_style else ""
    
    return f"<div{class_attr}{style_attr}>{content}</div>"


def format_safe_html_box(content: str, box_class: str = "guidance-box") -> str:
    """
    Format content in a safe styled box (for guidance, testing, etc.).
    
    Args:
        content: The content to display (will be escaped).
        box_class: The CSS class for the box styling.
        
    Returns:
        Safe HTML string for the styled box.
    """
    safe_content = escape_html(str(content))
    safe_class = escape_for_html_attribute(box_class)
    
    # Convert newlines to <br> tags for better readability
    safe_content = safe_content.replace('\n', '<br>')
    
    return f'<div class="{safe_class}">{safe_content}</div>'


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal attacks.
    
    Removes any path components and special characters that could
    be used to escape the intended directory.
    
    Args:
        filename: The filename to sanitize.
        
    Returns:
        The sanitized filename.
    """
    if not filename:
        return ""
    
    # Get just the filename, removing any path components
    import os
    filename = os.path.basename(str(filename))
    
    # Remove null bytes and other dangerous characters
    filename = filename.replace('\x00', '')
    
    # Remove any leading/trailing dots (hidden files, parent dir)
    filename = filename.strip('.')
    
    # Replace any remaining problematic characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Ensure the filename is not empty
    if not filename:
        return "unnamed_file"
    
    return filename
