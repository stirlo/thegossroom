module Jekyll
  class SmartRedirects < Generator
    def generate(site)
      puts "🔍 DEBUG: Starting Smart Redirects Generator"

      # Get ALL celebrities (remove drama score filter)
      all_celebrities = get_all_celebrities(site)
      puts "📊 Total celebrities available: #{all_celebrities.length}"

      # Process top celebrities first, then expand
      celebrities_to_process = all_celebrities.first(100) # Increased from 50

      celebrities_to_process.each do |celeb_key|
        latest_post = find_latest_celebrity_post(site, celeb_key)

        if latest_post
          # Create main redirect (e.g., /kanye-west/)
          create_redirect(site, celeb_key, latest_post.url)

          # Create date-based redirects for old Bluesky links
          create_date_redirects(site, celeb_key, latest_post)

          puts "📄 Created redirects for #{celeb_key}: #{latest_post.url}"
        else
          puts "❌ No posts found for #{celeb_key}"
        end
      end
    end

    private

    def get_all_celebrities(site)
      return [] unless site.data['celebrities']

      # Get ALL celebrities, sorted by drama score (no minimum threshold)
      site.data['celebrities']
        .select { |_, data| data['drama_score'] } # Just needs a drama score
        .sort_by { |_, data| -(data['drama_score'] || 0) }
        .map { |key, _| key }
    end

    def find_latest_celebrity_post(site, celeb_key)
      matching_posts = []

      site.posts.docs.each do |post|
        if celebrity_mentioned_in_post?(post, celeb_key)
          matching_posts << post
        end
      end

      # Return the most recent post
      matching_posts.max_by(&:date)
    end

    def celebrity_mentioned_in_post?(post, celeb_key)
      # Check mentions data first (most reliable)
      return true if post.data['mentions'] && post.data['mentions'][celeb_key]

      # Enhanced name variations
      celeb_name = celeb_key.gsub('_', ' ')
      search_terms = [
        celeb_name,
        celeb_name.split.map(&:capitalize).join(' '),
        celeb_key.gsub('_', '-'),
        # Add common variations
        celeb_name.split.first, # First name only
        celeb_name.split.last   # Last name only
      ].compact.uniq

      content_to_search = [
        post.data['title'] || '',
        post.content || '',
        post.data['excerpt'] || ''
      ].join(' ').downcase

      search_terms.any? { |term| content_to_search.include?(term.downcase) }
    end

    def create_redirect(site, celeb_key, target_url)
      redirect_page = SmartRedirectPage.new(site, celeb_key, target_url)
      site.pages << redirect_page
    end

    def create_date_redirects(site, celeb_key, latest_post)
      # Extract date from latest post URL
      if latest_post.url =~ %r{/(\d{4})/(\d{2})/(\d{2})/}
        year, month, day = $1, $2, $3

        # Create redirects for common date patterns
        date_patterns = [
          "#{year}/#{month}/#{day}/#{celeb_key.gsub('_', '-')}",
          "#{year}/#{month}/#{day}/#{celeb_key.gsub('_', '-')}-*", # Wildcard pattern
        ]

        date_patterns.each do |pattern|
          date_redirect = DateRedirectPage.new(site, pattern, latest_post.url)
          site.pages << date_redirect
        end
      end
    end
  end

  class SmartRedirectPage < Page
    def initialize(site, celeb_key, target_url)
      @site = site
      @base = site.source
      @dir = celeb_key.gsub('_', '-')
      @name = 'index.html'

      self.process(@name)
      self.data = {
        'layout' => nil,
        'permalink' => "/#{@dir}/",
        'sitemap' => false
      }

      celeb_name = celeb_key.gsub('_', ' ').split.map(&:capitalize).join(' ')

      self.content = create_redirect_html(celeb_name, target_url)
    end

    private

    def create_redirect_html(celeb_name, target_url)
      <<~HTML
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <title>Latest #{celeb_name} Gossip - The Goss Room</title>
          <meta name="description" content="Get the latest #{celeb_name} gossip and drama from The Goss Room">
          <meta http-equiv="refresh" content="0; url=#{target_url}">
          <link rel="canonical" href="https://thegossroom.com#{target_url}">
          <meta name="robots" content="noindex,follow">
        </head>
        <body>
          <h1>🔥 Latest #{celeb_name} Gossip</h1>
          <p>Redirecting you to the hottest #{celeb_name} tea...</p>
          <p>If you're not redirected, <a href="#{target_url}">click here</a>.</p>
          <script>
            // Immediate redirect
            window.location.replace("#{target_url}");
          </script>
        </body>
        </html>
      HTML
    end
  end

  class DateRedirectPage < Page
    def initialize(site, date_pattern, target_url)
      @site = site
      @base = site.source
      @dir = date_pattern
      @name = 'index.html'

      self.process(@name)
      self.data = {
        'layout' => nil,
        'permalink' => "/#{@dir}/",
        'sitemap' => false
      }

      self.content = <<~HTML
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta http-equiv="refresh" content="0; url=#{target_url}">
          <link rel="canonical" href="https://thegossroom.com#{target_url}">
          <meta name="robots" content="noindex,follow">
        </head>
        <body>
          <script>window.location.replace("#{target_url}");</script>
        </body>
        </html>
      HTML
    end
  end
end
