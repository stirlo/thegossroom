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

## 🏷️ Trending Drama Tags

<div class="tag-cloud-compact">
{% assign sorted_tags = site.tags | sort %}
{% assign drama_tags = sorted_tags | where_exp: "tag", "tag[1].size > 1" %}
{% for tag in drama_tags limit: 25 %}
  <span class="tag-bubble">
    <a href="/tag/{{ tag[0] | slugify }}/" class="tag-display">
      #{{ tag[0] | replace: '_', ' ' | replace: '-', ' ' }} 
      <small>({{ tag[1].size }})</small>
    </a>
  </span>
{% endfor %}
</div>

## 🚨 Celebrity Categories

<div id="celebrity-categories">

### 💥 Explosive Drama (1500+ Score)
<div id="explosive">
{% assign explosive_celebs = "" | split: "" %}
{% for celebrity_data in site.data.celebrities %}
  {% assign celebrity_info = celebrity_data[1] %}
  {% if celebrity_info.drama_score >= 1500 %}
    {% assign explosive_celebs = explosive_celebs | push: celebrity_data %}
  {% endif %}
{% endfor %}

{% if explosive_celebs.size > 0 %}
  {% assign explosive_sorted = explosive_celebs | sort: '[1].drama_score' | reverse %}
  {% for celebrity_data in explosive_sorted limit: 10 %}
    {% assign celebrity_name = celebrity_data[0] %}
    {% assign celebrity_info = celebrity_data[1] %}
    <div class="celebrity-card">
      <strong>{{ celebrity_name | replace: '_', ' ' | upcase }}</strong> 
      <span class="drama-score">{{ celebrity_info.drama_score }}</span>
      <div class="tags">
        {% for tag in celebrity_info.tags limit: 3 %}
          <span class="tag">{{ tag }}</span>
        {% endfor %}
      </div>
    </div>
  {% endfor %}
{% else %}
  <p><em>No explosive drama right now... suspiciously quiet! 🤔</em></p>
{% endif %}
</div>

### 🔥 Hot This Week (800-1499 Score)
<div id="hot-this-week">
{% assign hot_celebs = "" | split: "" %}
{% for celebrity_data in site.data.celebrities %}
  {% assign celebrity_info = celebrity_data[1] %}
  {% if celebrity_info.drama_score >= 800 and celebrity_info.drama_score < 1500 %}
    {% assign hot_celebs = hot_celebs | push: celebrity_data %}
  {% endif %}
{% endfor %}

{% if hot_celebs.size > 0 %}
  {% assign hot_sorted = hot_celebs | sort: '[1].drama_score' | reverse %}
  {% for celebrity_data in hot_sorted limit: 15 %}
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
{% else %}
  <p><em>Building up the heat... 🌡️</em></p>
{% endif %}
</div>

### ⭐ Rising Stars (300-799 Score)
<div id="rising-stars">
{% assign rising_celebs = "" | split: "" %}
{% for celebrity_data in site.data.celebrities %}
  {% assign celebrity_info = celebrity_data[1] %}
  {% if celebrity_info.drama_score >= 300 and celebrity_info.drama_score < 800 %}
    {% assign rising_celebs = rising_celebs | push: celebrity_data %}
  {% endif %}
{% endfor %}

{% if rising_celebs.size > 0 %}
  {% assign rising_sorted = rising_celebs | sort: '[1].drama_score' | reverse %}
  {% for celebrity_data in rising_sorted limit: 20 %}
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
{% else %}
  <p><em>Everyone's heating up! 🌡️</em></p>
{% endif %}
</div>

### 🧊 Cooling Down (Under 300 Score)
<div id="cooling-down">
{% assign cooling_celebs = "" | split: "" %}
{% for celebrity_data in site.data.celebrities %}
  {% assign celebrity_info = celebrity_data[1] %}
  {% if celebrity_info.drama_score < 300 and celebrity_info.status != 'memorial' %}
    {% assign cooling_celebs = cooling_celebs | push: celebrity_data %}
  {% endif %}
{% endfor %}

{% if cooling_celebs.size > 0 %}
  {% assign cooling_sorted = cooling_celebs | sort: '[1].drama_score' | reverse %}
  {% for celebrity_data in cooling_sorted limit: 10 %}
    {% assign celebrity_name = celebrity_data[0] %}
    {% assign celebrity_info = celebrity_data[1] %}
    <div class="celebrity-card">
      <strong>{{ celebrity_name | replace: '_', ' ' | title }}</strong> 
      <span class="drama-score">{{ celebrity_info.drama_score }}</span>
    </div>
  {% endfor %}
{% else %}
  <p><em>Everyone's heating up! 🔥</em></p>
{% endif %}
</div>

### 🕊️ Memorial
<div id="memorial">
{% assign memorial_celebs = site.data.celebrities | where: "status", "memorial" %}
{% if memorial_celebs.size > 0 %}
  {% for celebrity_data in memorial_celebs %}
    {% assign celebrity_name = celebrity_data[0] %}
    {% assign celebrity_info = celebrity_data[1] %}
    <div class="celebrity-card memorial">
      <strong>{{ celebrity_name | replace: '_', ' ' | title }}</strong> 
      <span class="memorial-note">{{ celebrity_info.memorial_note | default: "Remembered" }}</span>
      {% if celebrity_info.death_date %}
        <small class="death-date">({{ celebrity_info.death_date }})</small>
      {% endif %}
    </div>
  {% endfor %}
{% else %}
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
      {% assign explosive_count = 0 %}
      {% for celebrity_data in site.data.celebrities %}
        {% if celebrity_data[1].drama_score >= 1500 %}
          {% assign explosive_count = explosive_count | plus: 1 %}
        {% endif %}
      {% endfor %}
      <span class="big-number">{{ explosive_count }}</span>
    </div>
    <div class="stat-item">
      <h4>Rising Stars</h4>
      {% assign rising_count = 0 %}
      {% for celebrity_data in site.data.celebrities %}
        {% if celebrity_data[1].drama_score >= 300 and celebrity_data[1].drama_score < 800 %}
          {% assign rising_count = rising_count | plus: 1 %}
        {% endif %}
      {% endfor %}
      <span class="big-number">{{ rising_count }}</span>
    </div>
  </div>
</div>

---

<div class="update-info">
  <p><em>🤖 Automatically updated every hour from 25+ celebrity news sources</em></p>
  <p><em>⚡ Real-time drama scoring • 🎯 Auto-discovery of new celebrities • 📊 Historical trend tracking</em></p>
</div>
