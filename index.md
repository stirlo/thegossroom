---
layout: default
title: "The Gossip Room - Real-Time Celebrity Drama"
description: "Track celebrity drama scores, rising stars, and explosive entertainment news in real-time."
---

# 🎭 The Gossip Room

## 📊 Drama Index - Live Celebrity Tracking

<div class="drama-stats">
  <h3>🔥 Current Drama Temperature: <span class="drama-score">{{ site.data.celebrities | map: 'drama_score' | sum }}</span></h3>
  <p><em>Updated hourly from {{ site.data.celebrities | size }} tracked celebrities</em></p>
</div>

## 🚨 Celebrity Categories

<div id="celebrity-categories">

### 💥 Explosive Drama (1500+ Score)
<div id="explosive">
{% assign explosive_celebs = site.data.celebrities | where: "status", "explosive" %}
{% for celebrity_data in explosive_celebs limit: 10 %}
  {% assign celebrity_name = celebrity_data[0] %}
  {% assign celebrity_info = celebrity_data[1] %}
  <div class="celebrity-card">
    <strong>{{ celebrity_name | replace: '_', ' ' | upcase }}</strong> 
    <span class="drama-score">{{ celebrity_info.drama_score }}</span>
    <div class="tags">
      {% for tag in celebrity_info.tags %}
        <span class="tag">{{ tag }}</span>
      {% endfor %}
    </div>
  </div>
{% endfor %}
{% if explosive_celebs.size == 0 %}
  <p><em>No explosive drama right now... suspiciously quiet! 🤔</em></p>
{% endif %}
</div>

### 🔥 Hot This Week (800-1499 Score)
<div id="hot-this-week">
{% assign hot_celebs = site.data.celebrities | where: "status", "hot" %}
{% for celebrity_data in hot_celebs limit: 15 %}
  {% assign celebrity_name = celebrity_data[0] %}
  {% assign celebrity_info = celebrity_data[1] %}
  <div class="celebrity-card">
    <strong>{{ celebrity_name | replace: '_', ' ' | title }}</strong> 
    <span class="drama-score">{{ celebrity_info.drama_score }}</span>
    <div class="tags">
      {% for tag in celebrity_info.tags limit: 3 %}
        <span class="tag">{{ tag }}</span>
      {% endfor %}
    </div>
  </div>
{% endfor %}
{% if hot_celebs.size == 0 %}
  <p><em>Building up the heat... 🌡️</em></p>
{% endif %}
</div>

### ⭐ Rising Stars (300-799 Score)
<div id="rising-stars">
{% assign rising_celebs = site.data.celebrities | where: "status", "rising" %}
{% for celebrity_data in rising_celebs limit: 20 %}
  {% assign celebrity_name = celebrity_data[0] %}
  {% assign celebrity_info = celebrity_data[1] %}
  <div class="celebrity-card">
    <strong>{{ celebrity_name | replace: '_', ' ' | title }}</strong> 
    <span class="drama-score">{{ celebrity_info.drama_score }}</span>
    <div class="tags">
      {% for tag in celebrity_info.tags limit: 2 %}
        <span class="tag">{{ tag }}</span>
      {% endfor %}
    </div>
  </div>
{% endfor %}
</div>

### 🧊 Cooling Down (Under 300 Score)
<div id="cooling-down">
{% assign cooling_celebs = site.data.celebrities | where: "status", "cooling" %}
{% for celebrity_data in cooling_celebs limit: 10 %}
  {% assign celebrity_name = celebrity_data[0] %}
  {% assign celebrity_info = celebrity_data[1] %}
  <div class="celebrity-card">
    <strong>{{ celebrity_name | replace: '_', ' ' | title }}</strong> 
    <span class="drama-score">{{ celebrity_info.drama_score }}</span>
  </div>
{% endfor %}
</div>

### 🕊️ Memorial
<div id="memorial">
{% assign memorial_celebs = site.data.celebrities | where: "status", "memorial" %}
{% for celebrity_data in memorial_celebs %}
  {% assign celebrity_name = celebrity_data[0] %}
  {% assign celebrity_info = celebrity_data[1] %}
  <div class="celebrity-card">
    <strong>{{ celebrity_name | replace: '_', ' ' | title }}</strong> 
    <span class="memorial-note">{{ celebrity_info.memorial_note | default: "Remembered" }}</span>
  </div>
{% endfor %}
{% if memorial_celebs.size == 0 %}
  <p><em>No memorials currently tracked</em></p>
{% endif %}
</div>

</div>

## 📰 Latest Gossip

<div class="recent-posts">
{% for post in site.posts limit: 10 %}
  <div class="post-preview">
    <h3><a href="{{ post.url | relative_url }}">{{ post.title }}</a></h3>
    <p class="post-meta">
      <span class="date">{{ post.date | date: "%B %d, %Y" }}</span> | 
      <span class="drama-level status-{{ post.drama_score | divided_by: 5 | plus: 1 }}">
        Drama Score: {{ post.drama_score | default: 0 }}
      </span>
      {% if post.primary_celebrity %}
        | <span class="primary-celeb">{{ post.primary_celebrity | replace: '_', ' ' | title }}</span>
      {% endif %}
    </p>
    <p>{{ post.excerpt | strip_html | truncatewords: 30 }}</p>
    <div class="post-tags">
      {% for tag in post.tags limit: 5 %}
        <span class="tag">{{ tag }}</span>
      {% endfor %}
    </div>
  </div>
{% endfor %}

{% if site.posts.size == 0 %}
  <div class="no-posts">
    <h3>🚀 Getting Ready for Drama!</h3>
    <p>RSS feeds are being processed... First gossip posts coming soon!</p>
    <p><em>Check back in an hour for the latest celebrity drama! 🎭</em></p>
  </div>
{% endif %}
</div>

## 🔍 Drama Statistics

<div class="drama-stats">
  <div class="stat-grid">
    <div class="stat-item">
      <h4>Total Celebrities Tracked</h4>
      <span class="big-number">{{ site.data.celebrities | size }}</span>
    </div>
    <div class="stat-item">
      <h4>Total Drama Score</h4>
      <span class="big-number">{{ site.data.celebrities | map: 'drama_score' | sum }}</span>
    </div>
    <div class="stat-item">
      <h4>Explosive Drama</h4>
      <span class="big-number">{{ site.data.celebrities | where: "status", "explosive" | size }}</span>
    </div>
    <div class="stat-item">
      <h4>Rising Stars</h4>
      <span class="big-number">{{ site.data.celebrities | where: "status", "rising" | size }}</span>
    </div>
  </div>
</div>

---

<div class="update-info">
  <p><em>🤖 Automatically updated every hour from 25+ celebrity news sources</em></p>
  <p><em>⚡ Real-time drama scoring • 🎯 Auto-discovery of new celebrities • 📊 Historical trend tracking</em></p>
</div>
