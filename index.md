---
layout: default
title: "The Gossip Room - Real-Time Celebrity Drama"
description: "Track celebrity drama scores, rising stars, and explosive entertainment news in real-time."
---

# 🎭 The Gossip Room

**Real-time celebrity gossip with drama scoring and trending analysis**

## 📊 Drama Index
Coming soon: Live celebrity drama scores and trending analysis!

## 🔥 Latest Gossip
{% if site.posts.size > 0 %}
  {% for post in paginator.posts %}
### [{{ post.title }}]({{ post.url | relative_url }})
*{{ post.date | date: "%B %d, %Y" }}*

{{ post.excerpt | strip_html | truncatewords: 30 }}

---
  {% endfor %}

  <!-- Pagination -->
  {% if paginator.total_pages > 1 %}
**Pages:** 
    {% if paginator.previous_page %}
[← Prev]({{ paginator.previous_page_path | relative_url }}) | 
    {% endif %}
    {% for page in (1..paginator.total_pages) %}
      {% if page == paginator.page %}
**{{ page }}** | 
      {% else %}
[{{ page }}]({{ site.paginate_path | relative_url | replace: ':num', page }}) | 
      {% endif %}
    {% endfor %}
    {% if paginator.next_page %}
[Next →]({{ paginator.next_page_path | relative_url }})
    {% endif %}
  {% endif %}
{% else %}
No posts yet. The drama is loading... 🎬
{% endif %}
