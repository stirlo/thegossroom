module Jekyll
  class SmartRedirects < Generator
    def generate(site)
      puts "🔍 DEBUG: Starting FAST Smart Redirects Generator"

      # Only create celebrity redirects + a few strategic date patterns
      create_celebrity_redirects(site)
      create_strategic_date_redirects(site)

      puts "✅ Fast redirects complete!"
    end

    private

    def create_celebrity_redirects(site)
      all_celebrities = get_all_celebrities(site)
      puts "📊 Total celebrities available: #{all_celebrities.length}"

      url_aliases = create_url_aliases(all_celebrities)

      # Process top 50 celebrities only (fast!)
      top_celebrities = all_celebrities.first(50)

      top_celebrities.each do |celeb_key|
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

    def create_strategic_date_redirects(site)
      puts "🔍 Creating strategic date redirects..."

      # Only create for TOP 10 celebrities to keep it fast
      priority_celebrities = {
        'travis_kelce' => ['travis-kelce', 'kelce', 'travis'],
        'taylor_swift' => ['taylor-swift', 'taylor', 'swift'],
        'kim_kardashian' => ['kim-kardashian', 'kim-k', 'kim'],
        'kanye_west' => ['kanye-west', 'kanye', 'ye'],
        'donald_trump' => ['trump', 'donald-trump'],
        'justin_bieber' => ['justin-bieber', 'bieber'],
        'selena_gomez' => ['selena-gomez', 'selena'],
        'ariana_grande' => ['ariana-grande', 'ariana'],
        'beyonce' => ['beyonce'],
        'drake' => ['drake']
      }

      priority_celebrities.each do |celeb_key, variations|
        latest_post = find_latest_celebrity_post(site, celeb_key)
        next unless latest_post

        variations.each do |variation|
          # Create a catch-all redirect that matches any date + celebrity pattern
          create_regex_redirect(site, variation, latest_post.url)
        end
      end
    end

    def create_regex_redirect(site, celebrity_slug, target_url)
      # This creates a single redirect that catches ALL date patterns for this celebrity
      redirect_page = RegexRedirectPage.new(site, celebrity_slug, target_url)
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
        when 'kanye_west'
          aliases['kanye'] = celeb_key
          aliases['ye'] = celeb_key
        when 'justin_bieber'
          aliases['bieber'] = celeb_key
        when 'taylor_swift'
          aliases['taylor'] = celeb_key
          aliases['tswift'] = celeb_key
        when 'travis_kelce'
          aliases['travis'] = celeb_key
        when 'donald_trump'
          aliases['trump'] = celeb_key
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
        'sitemap' => false
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

  class RegexRedirectPage < Page
    def initialize(site, celebrity_slug, target_url)
      @site = site
      @base = site.source
      @dir = "regex-#{celebrity_slug}"
      @name = 'index.html'

      self.process(@name)
      self.data = {
        'layout' => nil,
        'permalink' => "/regex-#{celebrity_slug}/",
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
          <script>
            // Smart regex redirect for date patterns
            const path = window.location.pathname;
            const datePattern = /\/(\d{4})\/(\d{2})\/(\d{2})\/.*#{celebrity_slug}.*/i;

            if (datePattern.test(path)) {
              window.location.replace("#{target_url}");
            }
          </script>
          <h1>🔥 Updated Story</h1>
          <p>Redirecting to latest news...</p>
        </body>
        </html>
      HTML
    end
  end
end
