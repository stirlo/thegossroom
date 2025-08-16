module Jekyll
  class TemperatureFilter < Generator
    priority :high

    def generate(site)
      # Calculate article temperatures
      posts_with_temp = site.posts.docs.map do |post|
        temp = calculate_temperature(post)
        post.data['calculated_temperature'] = temp
        post
      end

      # Get top 33 daily posts
      daily_posts = posts_with_temp
        .select { |p| p.date > Time.now - (24 * 60 * 60) }
        .sort_by { |p| -p.data['calculated_temperature'] }
        .first(33)

      # Mark for publishing
      daily_posts.each { |p| p.data['publish'] = true }

      # Archive older posts gracefully
      archive_old_posts(site, posts_with_temp)
    end

    private

    def calculate_temperature(post)
      base_score = post.data['drama_score'] || 0
      celebrity_boost = calculate_celebrity_boost(post)
      time_decay = calculate_time_decay(post)

      (base_score + celebrity_boost) * time_decay
    end

    def calculate_celebrity_boost(post)
      return 0 unless post.data['mentions']

      celebrities = Jekyll.sites.first.data['celebrities']
      total_boost = 0

      post.data['mentions'].each do |celeb_key, mentions|
        celeb_temp = celebrities.dig(celeb_key, 'drama_score') || 0
        total_boost += celeb_temp * mentions
      end

      [total_boost, 100].min # Cap at 100
    end

    def calculate_time_decay(post)
      hours_old = (Time.now - post.date) / 3600
      return 1.0 if hours_old < 6
      return 0.8 if hours_old < 24
      return 0.5 if hours_old < 72
      0.2
    end

    def archive_old_posts(site, posts)
      cutoff = Time.now - (30 * 24 * 60 * 60) # 30 days

      posts.select { |p| p.date < cutoff }.each do |old_post|
        # Create redirect to latest story about same celebrity
        create_celebrity_redirect(site, old_post)
      end
    end

    def create_celebrity_redirect(site, old_post)
      primary_celeb = old_post.data['primary_celebrity']
      return unless primary_celeb

      # Find latest story about this celebrity
      latest = site.posts.docs
        .select { |p| p.data['primary_celebrity'] == primary_celeb }
        .select { |p| p.data['publish'] }
        .max_by(&:date)

      if latest && latest != old_post
        # Create redirect in _redirects.yml
        add_redirect(old_post.url, latest.url, primary_celeb)
      end
    end
  end
end
