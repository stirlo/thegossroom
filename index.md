---
layout: default
title: "The Gossip Room - Real-Time Celebrity Drama"
description: "Track celebrity drama scores, rising stars, and explosive entertainment news in real-time."
---

# 🎭 The Gossip Room

## 📊 Drama Index - Live Celebrity Tracking

<div class="drama-stats">
  {% assign total_recent_drama = 0 %}
  {% assign active_celebrities = 0 %}
  {% assign current_time = site.time | date: '%s' | plus: 0 %}
  {% assign week_ago = current_time | minus: 604800 %}

  {% for celebrity_data in site.data.celebrities %}
    {% assign celebrity_info = celebrity_data[1] %}
    {% if celebrity_info.status != 'memorial' %}
      {% assign active_celebrities = active_celebrities | plus: 1 %}
      {% assign base_score = celebrity_info.drama_score | default: 0 %}

      {% assign last_activity = celebrity_info.last_updated | default: '2024-01-01' | date: '%s' | plus: 0 %}
      {% if last_activity > week_ago %}
        {% assign time_multiplier = 2 %}
      {% else %}
        {% assign time_multiplier = 1 %}
      {% endif %}

      {% assign weighted_score = base_score | times: time_multiplier %}
      {% assign total_recent_drama = total_recent_drama | plus: weighted_score %}
    {% endif %}
  {% endfor %}

  {% assign drama_temperature = total_recent_drama | divided_by: active_celebrities | default: 0 %}

  <h3>🔥 Current Drama Temperature: 
    <span class="drama-score drama-temp-{{ drama_temperature | divided_by: 100 | plus: 1 }}">
      {{ drama_temperature | round }}°
    </span>
  </h3>
  <p><em>Updated hourly from {{ active_celebrities }} active celebrities</em></p>
</div>

## 🏷️ Trending Drama Tags

<div class="tag-cloud-compact">
{% assign sorted_tags = site.tags | sort %}
{% for tag in sorted_tags limit: 25 %}
  {% if tag[1].size > 1 %}
    <span class="tag-bubble">
      <a href="/tag/{{ tag[0] | slugify }}/" class="tag-display clickable-tag">
        #{{ tag[0] | replace: '_', ' ' | replace: '-', ' ' }} 
        <small>({{ tag[1].size }})</small>
      </a>
    </span>
  {% endif %}
{% endfor %}
</div>

## 🚨 Celebrity Categories

<div id="celebrity-categories">

### 💥 Explosive Drama (1500+ Score)
<div id="explosive">
{% assign explosive_count = 0 %}
{% for celebrity_data in site.data.celebrities %}
  {% assign celebrity_name = celebrity_data[0] %}
  {% assign celebrity_info = celebrity_data[1] %}
  {% if celebrity_info.drama_score >= 1500 %}
    {% assign explosive_count = explosive_count | plus: 1 %}
    <div class="celebrity-card clickable-celebrity" data-celebrity="{{ celebrity_name | slugify }}">
      <a href="/tag/{{ celebrity_name | slugify }}/" class="celebrity-link">
        <strong>{{ celebrity_name | replace: '_', ' ' | upcase }}</strong> 
        <span class="drama-score">{{ celebrity_info.drama_score }}</span>
        <div class="tags">
          {% for tag in celebrity_info.tags limit: 3 %}
            <span class="tag">{{ tag }}</span>
          {% endfor %}
        </div>
      </a>
    </div>
  {% endif %}
  {% if explosive_count >= 10 %}{% break %}{% endif %}
{% endfor %}

{% if explosive_count == 0 %}
  <p><em>No explosive drama right now... suspiciously quiet! 🤔</em></p>
{% endif %}
</div>

### 🔥 Hot This Week (800-1499 Score)
<div id="hot-this-week">
{% assign hot_count = 0 %}
{% for celebrity_data in site.data.celebrities %}
  {% assign celebrity_name = celebrity_data[0] %}
  {% assign celebrity_info = celebrity_data[1] %}
  {% if celebrity_info.drama_score >= 800 and celebrity_info.drama_score < 1500 %}
    {% assign hot_count = hot_count | plus: 1 %}
    <div class="celebrity-card clickable-celebrity" data-celebrity="{{ celebrity_name | slugify }}">
      <a href="/tag/{{ celebrity_name | slugify }}/" class="celebrity-link">
        <strong>{{ celebrity_name | replace: '_', ' ' | title }}</strong> 
        <span class="drama-score">{{ celebrity_info.drama_score }}</span>
        <div class="tags">
          {% for tag in celebrity_info.tags limit: 3 %}
            <span class="tag">{{ tag }}</span>
          {% endfor %}
        </div>
      </a>
    </div>
  {% endif %}
  {% if hot_count >= 15 %}{% break %}{% endif %}
{% endfor %}

{% if hot_count == 0 %}
  <p><em>Building up the heat... 🌡️</em></p>
{% endif %}
</div>

### ⭐ Rising Stars (300-799 Score)
<div id="rising-stars">
{% assign rising_count = 0 %}
{% for celebrity_data in site.data.celebrities %}
  {% assign celebrity_name = celebrity_data[0] %}
  {% assign celebrity_info = celebrity_data[1] %}
  {% if celebrity_info.drama_score >= 300 and celebrity_info.drama_score < 800 %}
    {% assign rising_count = rising_count | plus: 1 %}
    <div class="celebrity-card clickable-celebrity" data-celebrity="{{ celebrity_name | slugify }}">
      <a href="/tag/{{ celebrity_name | slugify }}/" class="celebrity-link">
        <strong>{{ celebrity_name | replace: '_', ' ' | title }}</strong> 
        <span class="drama-score">{{ celebrity_info.drama_score }}</span>
        <div class="tags">
          {% for tag in celebrity_info.tags limit: 2 %}
            <span class="tag">{{ tag }}</span>
          {% endfor %}
        </div>
      </a>
    </div>
  {% endif %}
  {% if rising_count >= 20 %}{% break %}{% endif %}
{% endfor %}

{% if rising_count == 0 %}
  <p><em>Everyone's heating up! 🌡️</em></p>
{% endif %}
</div>

### 🧊 Cooling Down (Under 300 Score)
<div id="cooling-down">
{% assign cooling_count = 0 %}
{% for celebrity_data in site.data.celebrities %}
  {% assign celebrity_name = celebrity_data[0] %}
  {% assign celebrity_info = celebrity_data[1] %}
  {% if celebrity_info.drama_score < 300 and celebrity_info.status != 'memorial' %}
    {% assign cooling_count = cooling_count | plus: 1 %}
    <div class="celebrity-card clickable-celebrity" data-celebrity="{{ celebrity_name | slugify }}">
      <a href="/tag/{{ celebrity_name | slugify }}/" class="celebrity-link">
        <strong>{{ celebrity_name | replace: '_', ' ' | title }}</strong> 
        <span class="drama-score">{{ celebrity_info.drama_score }}</span>
      </a>
    </div>
  {% endif %}
  {% if cooling_count >= 10 %}{% break %}{% endif %}
{% endfor %}

{% if cooling_count == 0 %}
  <p><em>Everyone's heating up! 🔥</em></p>
{% endif %}
</div>

### 🕊️ Memorial
<div id="memorial">
{% assign memorial_count = 0 %}
{% for celebrity_data in site.data.celebrities %}
  {% assign celebrity_name = celebrity_data[0] %}
  {% assign celebrity_info = celebrity_data[1] %}
  {% if celebrity_info.status == 'memorial' %}
    {% assign memorial_count = memorial_count | plus: 1 %}
    <div class="celebrity-card memorial clickable-celebrity" data-celebrity="{{ celebrity_name | slugify }}">
      <a href="/tag/{{ celebrity_name | slugify }}/" class="celebrity-link">
        <strong>{{ celebrity_name | replace: '_', ' ' | title }}</strong> 
        <span class="memorial-note">{{ celebrity_info.memorial_note | default: "Remembered" }}</span>
        {% if celebrity_info.death_date %}
          <small class="death-date">({{ celebrity_info.death_date }})</small>
        {% endif %}
      </a>
    </div>
  {% endif %}
{% endfor %}

{% if memorial_count == 0 %}
  <p><em>No memorials currently tracked</em></p>
{% endif %}
</div>

</div>

## 📰 Latest Gossip

<div class="recent-posts">
{% assign sorted_posts = site.posts | sort: 'drama_score' | reverse %}
{% assign displayed_posts = 0 %}
{% for post in sorted_posts %}
  {% assign drama_score = post.drama_score | default: 0 %}
  {% if drama_score >= 100 %}
    {% assign displayed_posts = displayed_posts | plus: 1 %}
    <div class="post-preview drama-level-{{ drama_score | divided_by: 200 | plus: 1 }}">
      <h3><a href="{{ post.url | relative_url }}">{{ post.title }}</a></h3>
      <p class="post-meta">
        <span class="date">{{ post.date | date: "%B %d, %Y" }}</span> | 
        <span class="drama-level status-{{ drama_score | divided_by: 5 | plus: 1 }}">
          🔥 Drama Score: {{ drama_score }}
        </span>
        {% if post.primary_celebrity %}
          | <a href="/tag/{{ post.primary_celebrity | slugify }}/" class="primary-celeb clickable-tag">
              {{ post.primary_celebrity | replace: '_', ' ' | title }}
            </a>
        {% endif %}
      </p>
      <p>{{ post.excerpt | strip_html | truncatewords: 30 }}</p>
      <div class="post-tags">
        {% for tag in post.tags limit: 5 %}
          <a href="/tag/{{ tag | slugify }}/" class="tag clickable-tag">{{ tag }}</a>
        {% endfor %}
      </div>
    </div>
  {% endif %}
  {% if displayed_posts >= 10 %}{% break %}{% endif %}
{% endfor %}

{% if displayed_posts == 0 %}
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
      <h4>Total Posts</h4>
      <span class="big-number">{{ site.posts | size }}</span>
    </div>
    <div class="stat-item">
      <h4>Explosive Drama</h4>
      {% assign explosive_stat = 0 %}
      {% for celebrity_data in site.data.celebrities %}
        {% if celebrity_data[1].drama_score >= 1500 %}
          {% assign explosive_stat = explosive_stat | plus: 1 %}
        {% endif %}
      {% endfor %}
      <span class="big-number">{{ explosive_stat }}</span>
    </div>
    <div class="stat-item">
      <h4>Rising Stars</h4>
      {% assign rising_stat = 0 %}
      {% for celebrity_data in site.data.celebrities %}
        {% if celebrity_data[1].drama_score >= 300 and celebrity_data[1].drama_score < 800 %}
          {% assign rising_stat = rising_stat | plus: 1 %}
        {% endif %}
      {% endfor %}
      <span class="big-number">{{ rising_stat }}</span>
    </div>
  </div>
</div>

---

<div class="update-info">
  <p><em>🤖 Automatically updated every hour from 25+ celebrity news sources</em></p>
  <p><em>⚡ Real-time drama scoring • 🎯 Auto-discovery of new celebrities • 📊 Historical trend tracking</em></p>
</div>
