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
    {% if site.data.celebrities %}
      {% assign shown_hot = 0 %}
      {% for celebrity_pair in site.data.celebrities %}
        {% if shown_hot < 12 %}
          {% assign celebrity_name = celebrity_pair[0] %}
          {% assign celebrity_info = celebrity_pair[1] %}
          {% assign drama_score = celebrity_info.drama_score | default: 0 %}

          {% if drama_score >= 50 %}
            {% assign temp_class = 'mild' %}
            {% if drama_score >= 85 %}
              {% assign temp_class = 'explosive' %}
            {% elsif drama_score >= 70 %}
              {% assign temp_class = 'hot' %}
            {% elsif drama_score >= 50 %}
              {% assign temp_class = 'rising' %}
            {% endif %}

            <div class="celebrity-temp-card temp-{{ temp_class }}">
              <a href="/tag/{{ celebrity_name | slugify }}/" class="celebrity-link">
                <h3>{{ celebrity_info.display_name | default: celebrity_name | replace: '_', ' ' | title }}</h3>
                <div class="temperature">{{ drama_score }}°</div>
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

            {% assign shown_hot = shown_hot | plus: 1 %}
          {% endif %}
        {% endif %}
      {% endfor %}

      {% if shown_hot == 0 %}
        <div class="no-hot-celebs">
          <p>🔍 No hot celebrities right now. Check back soon for drama temperatures!</p>
        </div>
      {% endif %}
    {% else %}
      <div class="no-celebrities">
        <p>🔍 No celebrity data available yet. Check back soon for drama temperatures!</p>
      </div>
    {% endif %}
  </div>
</section>

<!-- RECENT EXPLOSIVE DRAMA -->
<section class="recent-posts">
  <h2>🚨 Latest Explosive Drama</h2>
  <div class="posts-grid">
    {% assign explosive_posts = site.posts | where_exp: "post", "post.drama_score >= 70" | sort: 'date' | reverse %}
    {% if explosive_posts.size > 0 %}
      {% for post in explosive_posts limit: 8 %}
        {% assign temp_class = 'mild' %}
        {% assign drama_score = post.drama_score | default: 0 %}
        {% if drama_score >= 85 %}
          {% assign temp_class = 'explosive' %}
        {% elsif drama_score >= 70 %}
          {% assign temp_class = 'hot' %}
        {% endif %}

        <article class="post-card temp-{{ temp_class }}">
          <h3><a href="{{ post.url | relative_url }}">{{ post.title }}</a></h3>
          <div class="post-meta">
            <span class="date">{{ post.date | date: "%b %d, %Y" }}</span>
            <span class="temperature">🌡️ {{ drama_score }}°</span>
            {% if post.primary_celebrity %}
              <a href="/tag/{{ post.primary_celebrity | slugify }}/" class="primary-celeb">
                {{ post.primary_celebrity | replace: '_', ' ' | title }}
              </a>
            {% endif %}
          </div>
          <p class="excerpt">{{ post.excerpt | strip_html | truncatewords: 25 }}</p>
          {% if post.tags and post.tags.size > 0 %}
            <div class="post-tags">
              {% for tag in post.tags limit: 4 %}
                <a href="/tag/{{ tag | slugify }}/" class="tag">{{ tag | replace: '_', ' ' | title }}</a>
              {% endfor %}
            </div>
          {% endif %}
        </article>
      {% endfor %}
    {% else %}
      <div class="no-posts">
        <p>🔥 No explosive drama yet! Check back soon for the hottest gossip.</p>
      </div>
    {% endif %}
  </div>
</section>

<!-- SIMPLIFIED CATEGORIES - NO GROUP_BY -->
<section class="trending-categories">
  <h2>📊 Drama by Category</h2>
  <div class="category-grid">
    {% if site.data.celebrities %}
      {% comment %} Manual category counting {% endcomment %}
      {% assign reality_tv_count = 0 %}
      {% assign reality_tv_temp = 0 %}
      {% assign music_count = 0 %}
      {% assign music_temp = 0 %}
      {% assign acting_count = 0 %}
      {% assign acting_temp = 0 %}
      {% assign influencer_count = 0 %}
      {% assign influencer_temp = 0 %}

      {% for celebrity_pair in site.data.celebrities %}
        {% assign celebrity_info = celebrity_pair[1] %}
        {% assign drama_score = celebrity_info.drama_score | default: 0 %}
        {% assign category = celebrity_info.category | default: 'other' | downcase %}

        {% if drama_score > 0 %}
          {% if category contains 'reality' or category contains 'tv' %}
            {% assign reality_tv_count = reality_tv_count | plus: 1 %}
            {% assign reality_tv_temp = reality_tv_temp | plus: drama_score %}
          {% elsif category contains 'music' or category contains 'singer' or category contains 'rapper' %}
            {% assign music_count = music_count | plus: 1 %}
            {% assign music_temp = music_temp | plus: drama_score %}
          {% elsif category contains 'actor' or category contains 'actress' or category contains 'acting' %}
            {% assign acting_count = acting_count | plus: 1 %}
            {% assign acting_temp = acting_temp | plus: drama_score %}
          {% elsif category contains 'influencer' or category contains 'social' %}
            {% assign influencer_count = influencer_count | plus: 1 %}
            {% assign influencer_temp = influencer_temp | plus: drama_score %}
          {% endif %}
        {% endif %}
      {% endfor %}

      {% if reality_tv_count > 0 %}
        {% assign avg_reality = reality_tv_temp | divided_by: reality_tv_count %}
        <div class="category-card temp-{% if avg_reality >= 70 %}hot{% elsif avg_reality >= 50 %}rising{% else %}mild{% endif %}">
          <h3>Reality TV</h3>
          <div class="category-temp">{{ avg_reality }}°</div>
          <div class="category-count">{{ reality_tv_count }} active</div>
        </div>
      {% endif %}

      {% if music_count > 0 %}
        {% assign avg_music = music_temp | divided_by: music_count %}
        <div class="category-card temp-{% if avg_music >= 70 %}hot{% elsif avg_music >= 50 %}rising{% else %}mild{% endif %}">
          <h3>Music</h3>
          <div class="category-temp">{{ avg_music }}°</div>
          <div class="category-count">{{ music_count }} active</div>
        </div>
      {% endif %}

      {% if acting_count > 0 %}
        {% assign avg_acting = acting_temp | divided_by: acting_count %}
        <div class="category-card temp-{% if avg_acting >= 70 %}hot{% elsif avg_acting >= 50 %}rising{% else %}mild{% endif %}">
          <h3>Acting</h3>
          <div class="category-temp">{{ avg_acting }}°</div>
          <div class="category-count">{{ acting_count }} active</div>
        </div>
      {% endif %}

      {% if influencer_count > 0 %}
        {% assign avg_influencer = influencer_temp | divided_by: influencer_count %}
        <div class="category-card temp-{% if avg_influencer >= 70 %}hot{% elsif avg_influencer >= 50 %}rising{% else %}mild{% endif %}">
          <h3>Influencers</h3>
          <div class="category-temp">{{ avg_influencer }}°</div>
          <div class="category-count">{{ influencer_count }} active</div>
        </div>
      {% endif %}
    {% endif %}
  </div>
</section>

<!-- ALL RECENT POSTS -->
<section class="all-posts">
  <h2>📰 All Recent Drama</h2>
  <div class="posts-list">
    {% for post in site.posts limit: 20 %}
      {% assign temp_class = 'freezing' %}
      {% assign drama_score = post.drama_score | default: 0 %}
      {% if drama_score >= 85 %}
        {% assign temp_class = 'explosive' %}
      {% elsif drama_score >= 70 %}
        {% assign temp_class = 'hot' %}
      {% elsif drama_score >= 50 %}
        {% assign temp_class = 'rising' %}
      {% elsif drama_score >= 30 %}
        {% assign temp_class = 'mild' %}
      {% elsif drama_score >= 10 %}
        {% assign temp_class = 'cooling' %}
      {% endif %}

      <article class="post-item temp-{{ temp_class }}">
        <h3><a href="{{ post.url | relative_url }}">{{ post.title }}</a></h3>
        <div class="post-meta">
          <span class="date">{{ post.date | date: "%B %d, %Y" }}</span>
          <span class="temperature">{{ drama_score }}°</span>
          {% if post.primary_celebrity %}
            <a href="/tag/{{ post.primary_celebrity | slugify }}/" class="primary-celeb">
              {{ post.primary_celebrity | replace: '_', ' ' | title }}
            </a>
          {% endif %}
        </div>
        {% if post.tags and post.tags.size > 0 %}
          <div class="post-tags">
            {% for tag in post.tags limit: 6 %}
              <a href="/tag/{{ tag | slugify }}/" class="tag">{{ tag | replace: '_', ' ' | title }}</a>
            {% endfor %}
          </div>
        {% endif %}
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
