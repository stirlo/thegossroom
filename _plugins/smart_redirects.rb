module Jekyll
  class SmartRedirects < Generator
    def generate(site)
      puts "🔍 DEBUG: Starting Smart Redirects Generator"

      # Create celebrity redirects
      create_celebrity_redirects(site)

      # Create universal date-based catch-all redirects
      create_universal_date_redirects(site)
    end

    private

    def create_celebrity_redirects(site)
      all_celebrities = get_all_celebrities(site)
      puts "📊 Total celebrities available: #{all_celebrities.length}"

      url_aliases = create_url_aliases(all_celebrities)

      # Process ALL celebrities
      all_celebrities.each do |celeb_key|
        latest_post = find_latest_celebrity_post(site, celeb_key)

        if latest_post
          create_redirect(site, celeb_key, latest_post.url)
          puts "📄 Created redirects for #{celeb_key}: #{latest_post.url}"
        end
      end

      # Process URL aliases
      url_aliases.each do |alias_slug, actual_key|
        latest_post = find_latest_celebrity_post(site, actual_key)

        if latest_post
          create_redirect_with_custom_slug(site, alias_slug, latest_post.url)
          puts "📄 Created alias redirect: #{alias_slug} → #{latest_post.url}"
        end
      end
    end

    def create_universal_date_redirects(site)
      puts "🔍 Creating universal date-based redirects..."

      # Get all celebrities with posts
      celebrities_with_posts = get_celebrities_with_posts(site)

      # Create date patterns for each celebrity
      celebrities_with_posts.each do |celeb_key, latest_post|
        celeb_variations = get_celebrity_url_variations(celeb_key)

        # Create redirects for multiple date patterns
        (2020..2025).each do |year|
          (1..12).each do |month|
            (1..31).each do |day|
              month_str = month.to_s.rjust(2, '0')
              day_str = day.to_s.rjust(2, '0')

              celeb_variations.each do |variation|
                # Create pattern: /YYYY/MM/DD/celebrity-name-anything/
                date_path = "#{year}/#{month_str}/#{day_str}/#{variation}"
                create_date_wildcard_redirect(site, date_path, latest_post.url, celeb_key)
              end
            end
          end
        end
      end
    end

    def get_celebrities_with_posts(site)
      celebrities_with_posts = {}

      get_all_celebrities(site).each do |celeb_key|
        latest_post = find_latest_celebrity_post(site, celeb_key)
        if latest_post
          celebrities_with_posts[celeb_key] = latest_post
        end
      end

      celebrities_with_posts
    end

    def get_celebrity_url_variations(celeb_key)
      variations = []

      # Main variation
      main_slug = celeb_key.gsub('_', '-')
      variations << main_slug

      # Add common patterns
      case celeb_key
      when 'travis_kelce'
        variations += ['travis-kelce', 'travis-kelces', 'kelce', 'kelces']
      when 'taylor_swift'
        variations += ['taylor-swift', 'taylor-swifts', 'taylor', 'swift']
      when 'kim_kardashian'
        variations += ['kim-kardashian', 'kim-kardashians', 'kim-k', 'kardashian']
      when 'kanye_west'
        variations += ['kanye-west', 'kanye', 'ye', 'west']
      when 'justin_bieber'
        variations += ['justin-bieber', 'justin-biebers', 'bieber', 'justin']
      else
        # Auto-generate variations
        name_parts = celeb_key.split('_')
        if name_parts.length == 2
          first, last = name_parts
          variations += [
            "#{first}-#{last}",
            "#{first}-#{last}s",
            first,
            last
          ]
        end
      end

      variations.uniq
    end

    def create_date_wildcard_redirect(site, date_path, target_url, celeb_key)
      # Only create for high-priority celebrities to avoid too many redirects
      priority_celebrities = ['travis_kelce', 'taylor_swift', 'kim_kardashian', 'kanye_west', 'justin_bieber']

      return unless priority_celebrities.include?(celeb_key)

      redirect_page = DateWildcardRedirectPage.new(site, date_path, target_url)
      site.pages << redirect_page
    end

    def get_all_celebrities(site)
      return [] unless site.data['celebrities']

      site.data['celebrities']
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

      matching_posts.max_by(&:date)
    end

    def celebrity_mentioned_in_post?(post, celeb_key)
      return true if post.data['mentions'] && post.data['mentions'][celeb_key]

      celeb_name = celeb_key.gsub('_', ' ')
      search_terms = [
        celeb_name,
        celeb_name.split.map(&:capitalize).join(' '),
        celeb_key.gsub('_', '-'),
        celeb_name.split.first,
        celeb_name.split.last
      ].compact.uniq

      content_to_search = [
        post.data['title'] || '',
        post.content || '',
        post.data['excerpt'] || ''
      ].join(' ').downcase

      search_terms.any? { |term| content_to_search.include?(term.downcase) }
    end

    def create_url_aliases(celebrities)
      aliases = {}

      celebrities.each do |celeb_key|
        case celeb_key
        when 'kim_kardashian'
          aliases['kim-k'] = celeb_key
          aliases['kim'] = celeb_key
        when 'kanye_west'
          aliases['kanye'] = celeb_key
          aliases['ye'] = celeb_key
        when 'justin_bieber'
          aliases['bieber'] = celeb_key
          aliases['justin'] = celeb_key
        when 'taylor_swift'
          aliases['taylor'] = celeb_key
          aliases['tswift'] = celeb_key
        when 'travis_kelce'
          aliases['travis'] = celeb_key
        end

        if celeb_key.include?('_')
          first_name = celeb_key.split('_').first
          aliases[first_name] = celeb_key unless aliases[first_name]
        end
      end

      aliases
    end

    def create_redirect(site, celeb_key, target_url)
      redirect_page = SmartRedirectPage.new(site, celeb_key.gsub('_', '-'), target_url)
      site.pages << redirect_page
    end

    def create_redirect_with_custom_slug(site, slug, target_url)
      redirect_page = SmartRedirectPage.new(site, slug, target_url)
      site.pages << redirect_page
    end
  end

  class SmartRedirectPage < Page
    def initialize(site, slug, target_url)
      @site = site
      @base = site.source
      @dir = slug
      @name = 'index.html'

      self.process(@name)
      self.data = {
        'layout' => nil,
        'permalink' => "/#{@dir}/",
        'sitemap' => false  # Keeps redirect pages out of sitemap
      }

      celeb_name = slug.gsub('-', ' ').split.map(&:capitalize).join(' ')

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
          <script>window.location.replace("#{target_url}");</script>
        </body>
        </html>
      HTML
    end
  end

  class DateWildcardRedirectPage < Page
    def initialize(site, date_path, target_url)
      @site = site
      @base = site.source
      @dir = date_path
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
          <title>The Goss Room - Latest Celebrity News</title>
          <meta http-equiv="refresh" content="0; url=#{target_url}">
          <link rel="canonical" href="https://thegossroom.com#{target_url}">
          <meta name="robots" content="noindex,follow">
        </head>
        <body>
          <h1>🔥 Updated Story</h1>
          <p>This story has been updated. Redirecting to latest news...</p>
          <script>window.location.replace("#{target_url}");</script>
        </body>
        </html>
      HTML
    end
  end
end
