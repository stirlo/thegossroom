---
layout: post
title: "{{ title }}"
date: {{ date }}
categories: gossip
tags: []
drama_score: 0
primary_celebrity: ""
source: ""
source_url: ""
mentions: {}
excerpt: ""
image: ""
---

{{ content }}

**Drama Score:** {{ page.drama_score }} | **Level:** {{ page.drama_level | default: "MILD" }}

**Celebrities Mentioned:** {{ page.mentions | keys | join: ", " }}

[Read full article]({{ page.source_url }})

---
*This post was automatically generated from RSS feeds. Drama scores are calculated based on mention frequency and source reliability.*
