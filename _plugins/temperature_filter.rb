module Jekyll
  class TemperatureFilter < Generator
    priority :high

    def generate(site)
      return unless site.config['temperature_system']

      config = site.config['temperature_system']
      daily_limit = config['daily_post_limit'] || 33
      min_temp = config['minimum_temperature'] || 25

      # Calculate temperatures for all posts
      posts_with_temp = site.posts.docs.map do |post|
        temp = calculate_temperature(site, post)
        post.data['live_temperature'] = temp
        post.data['publish'] = temp >= min_temp
        post
      end

      # Filter and limit daily posts
      hot_posts = posts_with_temp
        .select { |p| p.data['publish'] }
        .sort_by { |p| [-p.data['live_temperature'], -p.date.to_f] }
        .first(daily_limit)

      # Mark only top posts for publishing
      site.posts.docs.each { |p| p.data['publish'] = false }
      hot_posts.each { |p| p.data['publish'] = true }

      Jekyll.logger.info "Temperature Filter:", "#{hot_posts.length} hot posts selected (min temp: #{min_temp}°)"
    end

    private

    def calculate_temperature(site, post)
      base_score = post.data['drama_score'] || 0
      celebrity_boost = calculate_celebrity_boost(site, post)
      time_decay = calculate_time_decay(post)

      temperature = (base_score + celebrity_boost) * time_decay
      [temperature, 100].min.to_i
    end

    def calculate_celebrity_boost(site, post)
      return 0 unless post.data['mentions']

      celebrities = site.data['celebrities'] || {}
      total_boost = 0

      post.data['mentions'].each do |celeb_key, mentions|
        celeb_temp = celebrities.dig(celeb_key, 'drama_score') || 0
        total_boost += celeb_temp * mentions
      end

      post.data['mentions'].empty? ? 0 : total_boost / post.data['mentions'].size
    end

    def calculate_time_decay(post)
      hours_old = (Time.now - post.date) / 3600

      return 1.0 if hours_old < 6
      return 0.8 if hours_old < 24
      return 0.5 if hours_old < 72
      0.2
    end
  end
end
