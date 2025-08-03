---
layout: default
title: "The Gossip Room - Celebrity Drama Temperature Check"
description: "Real-time celebrity drama tracking with dynamic temperature scores. Who's hot, who's not, and who's absolutely explosive right now!"
---

<div class="homepage-hero">
  <h1>🔥 The Gossip Room</h1>
  <p class="hero-subtitle">Real-time celebrity drama temperature tracking</p>
  <div class="temperature-legend">
    <span class="temp-explosive">🔥 85-100° EXPLOSIVE</span>
    <span class="temp-hot">🌶️ 70-84° HOT</span>
    <span class="temp-rising">📈 50-69° RISING</span>
    <span class="temp-mild">😐 30-49° MILD</span>
    <span class="temp-cooling">❄️ 10-29° COOLING</span>
    <span class="temp-freezing">🧊 0-9° FREEZING</span>
  </div>
</div>

<!-- TEMPERATURE DASHBOARD -->
{% assign temperature_report = site.data.temperature_report %}
{% if temperature_report %}
<section class="temperature-dashboard">
  <h2>🌡️ Current Drama Temperature</h2>
  <div class="temp-stats">
    <div class="temp-stat explosive">
      <span class="number">{{ temperature_report.temperature_distribution.explosive | default: 0 }}</span>
      <span class="label">Explosive</span>
    </div>
    <div class="temp-stat hot">
      <span class="number">{{ temperature_report.temperature_distribution.hot | default: 0 }}</span>
      <span class="label">Hot</span>
    </div>
    <div class="temp-stat rising">
      <span class="number">{{ temperature_report.temperature_distribution.rising | default: 0 }}</span>
      <span class="label">Rising</span>
    </div>
    <div class="temp-stat mild">
      <span class="number">{{ temperature_report.temperature_distribution.mild | default: 0 }}</span>
      <span class="label">Mild</span>
    </div>
  </div>
</section>
{% endif %}

<!-- HOTTEST CELEBRITIES RIGHT NOW -->
<section class="hottest-now">
  <h2>🔥 Hottest Drama Right Now</h2>
  <div class="celebrity-temperature-grid">
    {% assign sorted_celebrities = site.data.celebrities | sort: 'drama_score' | reverse %}
    {% assign shown_hot = 0 %}
    {% for celebrity_data in sorted_celebrities %}
      {% assign celebrity_name = celebrity_data[0] %}
      {% assign celebrity_info = celebrity_data[1] %}
      {% if celebrity_info.drama_score >= 50 and shown_hot < 12 %}
        {% assign shown_hot = shown_hot | plus: 1 %}
        {% assign temp_class = 'mild' %}
        {% if celebrity_info.drama_score >= 85 %}
          {% assign temp_class = 'explosive' %}
        {% elsif celebrity_info.drama_score >= 70 %}
          {% assign temp_class = 'hot' %}
        {% elsif celebrity_info.drama_score >= 50 %}
          {% assign temp_class = 'rising' %}
        {% endif %}

        <div class="celebrity-temp-card temp-{{ temp_class }}">
          <a href="/tag/{{ celebrity_name | slugify }}/" class="celebrity-link">
            <h3>{{ celebrity_name | replace: '_', ' ' | title }}</h3>
            <div class="temperature">{{ celebrity_info.drama_score | default: 0 }}°</div>
            <div class="status">{{ celebrity_info.status | default: 'unknown' | upcase }}</div>
            {% if celebrity_info.temperature_change %}
              {% assign change = celebrity_info.temperature_change %}
              <div class="change {% if change > 0 %}rising{% else %}falling{% endif %}">
                {% if change > 0 %}↗️ +{{ change }}°{% else %}↘️ {{ change }}°{% endif %}
              </div>
            {% endif %}
            <div class="category">{{ celebrity_info.category | default: 'celebrity' | upcase }}</div>
          </a>
        </div>
      {% endif %}
    {% endfor %}
  </div>
</section>

<!-- RECENT EXPLOSIVE DRAMA -->
<section class="recent-posts">
  <h2>🚨 Latest Explosive Drama</h2>
  <div class="posts-grid">
    {% assign explosive_posts = site.posts | where_exp: "post", "post.drama_score >= 70" | sort: 'date' | reverse %}
    {% for post in explosive_posts limit: 8 %}
      {% assign temp_class = 'mild' %}
      {% if post.drama_score >= 85 %}
        {% assign temp_class = 'explosive' %}
      {% elsif post.drama_score >= 70 %}
        {% assign temp_class = 'hot' %}
      {% endif %}

      <article class="post-card temp-{{ temp_class }}">
        <h3><a href="{{ post.url | relative_url }}">{{ post.title }}</a></h3>
        <div class="post-meta">
          <span class="date">{{ post.date | date: "%b %d, %Y" }}</span>
          <span class="temperature">🌡️ {{ post.drama_score | default: 0 }}°</span>
          {% if post.primary_celebrity %}
            <a href="/tag/{{ post.primary_celebrity | slugify }}/" class="primary-celeb">
              {{ post.primary_celebrity | replace: '_', ' ' | title }}
            </a>
          {% endif %}
        </div>
        <p class="excerpt">{{ post.excerpt | strip_html | truncatewords: 25 }}</p>
        <div class="post-tags">
          {% for tag in post.tags limit: 4 %}
            <a href="/tag/{{ tag | slugify }}/" class="tag">{{ tag | replace: '_', ' ' | title }}</a>
          {% endfor %}
        </div>
      </article>
    {% endfor %}
  </div>
</section>

<!-- TRENDING CATEGORIES -->
<section class="trending-categories">
  <h2>📊 Drama by Category</h2>
  <div class="category-grid">
    {% assign categories = site.data.celebrities | group_by: 'category' %}
    {% for category_group in categories %}
      {% assign category = category_group.name %}
      {% assign celebrities = category_group.items %}
      {% assign avg_temp = 0 %}
      {% assign active_count = 0 %}

      {% for celeb in celebrities %}
        {% if celeb.drama_score > 0 %}
          {% assign avg_temp = avg_temp | plus: celeb.drama_score %}
          {% assign active_count = active_count | plus: 1 %}
        {% endif %}
      {% endfor %}

      {% if active_count > 0 %}
        {% assign avg_temp = avg_temp | divided_by: active_count %}
        {% assign temp_class = 'mild' %}
        {% if avg_temp >= 70 %}
          {% assign temp_class = 'hot' %}
        {% elsif avg_temp >= 50 %}
          {% assign temp_class = 'rising' %}
        {% elsif avg_temp < 30 %}
          {% assign temp_class = 'cooling' %}
        {% endif %}

        <div class="category-card temp-{{ temp_class }}">
          <h3>{{ category | default: 'Other' | title }}</h3>
          <div class="category-temp">{{ avg_temp }}°</div>
          <div class="category-count">{{ active_count }} active</div>
          <div class="category-total">{{ celebrities.size }} total</div>
        </div>
      {% endif %}
    {% endfor %}
  </div>
</section>

<!-- ALL RECENT POSTS -->
<section class="all-posts">
  <h2>📰 All Recent Drama</h2>
  <div class="posts-list">
    {% for post in site.posts limit: 20 %}
      {% assign temp_class = 'freezing' %}
      {% if post.drama_score >= 85 %}
        {% assign temp_class = 'explosive' %}
      {% elsif post.drama_score >= 70 %}
        {% assign temp_class = 'hot' %}
      {% elsif post.drama_score >= 50 %}
        {% assign temp_class = 'rising' %}
      {% elsif post.drama_score >= 30 %}
        {% assign temp_class = 'mild' %}
      {% elsif post.drama_score >= 10 %}
        {% assign temp_class = 'cooling' %}
      {% endif %}

      <article class="post-item temp-{{ temp_class }}">
        <h3><a href="{{ post.url | relative_url }}">{{ post.title }}</a></h3>
        <div class="post-meta">
          <span class="date">{{ post.date | date: "%B %d, %Y" }}</span>
          <span class="temperature">{{ post.drama_score | default: 0 }}°</span>
          {% if post.primary_celebrity %}
            <a href="/tag/{{ post.primary_celebrity | slugify }}/" class="primary-celeb">
              {{ post.primary_celebrity | replace: '_', ' ' | title }}
            </a>
          {% endif %}
        </div>
        <div class="post-tags">
          {% for tag in post.tags limit: 6 %}
            <a href="/tag/{{ tag | slugify }}/" class="tag">{{ tag | replace: '_', ' ' | title }}</a>
          {% endfor %}
        </div>
      </article>
    {% endfor %}
  </div>

  <div class="view-more">
    <a href="/archive/" class="btn-view-more">🔥 View All Drama Archive</a>
  </div>
</section>

<!-- TEMPERATURE EXPLANATION -->
<section class="temperature-explanation">
  <h2>🌡️ How Drama Temperature Works</h2>
  <div class="explanation-grid">
    <div class="explanation-item">
      <h3>🔥 Dynamic Scoring</h3>
      <p>Drama temperatures are calculated weekly based on recent activity, mentions, and trending velocity. Scores are always relative to current drama levels.</p>
    </div>
    <div class="explanation-item">
      <h3>📈 Real-Time Updates</h3>
      <p>Temperatures update automatically as new drama unfolds. Rising stars heat up quickly, while inactive celebrities cool down naturally.</p>
    </div>
    <div class="explanation-item">
      <h3>🎯 Always Relevant</h3>
      <p>Unlike static scores, our temperature system ensures the hottest drama is always at 100°, making comparisons meaningful over time.</p>
    </div>
  </div>
</section>
