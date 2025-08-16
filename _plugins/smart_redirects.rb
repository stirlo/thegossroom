module Jekyll
  class SmartRedirects < Generator
    def generate(site)
      puts "🔍 DEBUG: Starting Smart Redirects Generator"

      # Create celebrity redirects (no temp threshold)
      create_celebrity_redirects(site)

      # Create date-based post redirects for missing posts
      create_missing_post_redirects(site)
    end

    private

    def create_celebrity_redirects(site)
      all_celebrities = get_all_celebrities(site)
      puts "📊 Total celebrities available: #{all_celebrities.length}"

      # Create URL aliases
      url_aliases = create_url_aliases(all_celebrities)

      # Process ALL celebrities (no limit, no temp threshold)
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

    def create_missing_post_redirects(site)
      # Handle specific missing posts that should redirect to related content
      missing_posts = [
        {
          path: "2025/08/13/travis-kelces-ex-teammate-says-he-outkicked-his-coverage-with-taylor-swift",
          redirect_to_celebrity: "travis_kelce"
        }
        # Add more missing posts here as needed
      ]

      missing_posts.each do |missing_post|
        latest_post = find_latest_celebrity_post(site, missing_post[:redirect_to_celebrity])

        if latest_post
          create_missing_post_redirect(site, missing_post[:path], latest_post.url)
          puts "📄 Created missing post redirect: /#{missing_post[:path]}/ → #{latest_post.url}"
        end
      end
    end

    def get_all_celebrities(site)
      return [] unless site.data['celebrities']

      # Get ALL celebrities (no drama score threshold)
      site.data['celebrities']
        .sort_by { |_, data| -(data['drama_score'] || 0) }
        .map { |key, _| key }
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
        when 'kylie_jenner'
          aliases['kylie'] = celeb_key
        when 'ariana_grande'
          aliases['ariana'] = celeb_key
        when 'selena_gomez'
          aliases['selena'] = celeb_key
        end

        # Auto-create first name aliases
        if celeb_key.include?('_')
          first_name = celeb_key.split('_').first
          aliases[first_name] = celeb_key unless aliases[first_name]
        end
      end

      aliases
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

    def create_redirect(site, celeb_key, target_url)
      redirect_page = SmartRedirectPage.new(site, celeb_key.gsub('_', '-'), target_url)
      site.pages << redirect_page
    end

    def create_redirect_with_custom_slug(site, slug, target_url)
      redirect_page = SmartRedirectPage.new(site, slug, target_url)
      site.pages << redirect_page
    end

    def create_missing_post_redirect(site, path, target_url)
      redirect_page = MissingPostRedirectPage.new(site, path, target_url)
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

  class MissingPostRedirectPage < Page
    def initialize(site, path, target_url)
      @site = site
      @base = site.source
      @dir = path
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
          <meta name="description" content="Get the latest celebrity gossip and drama from The Goss Room">
          <meta http-equiv="refresh" content="0; url=#{target_url}">
          <link rel="canonical" href="https://thegossroom.com#{target_url}">
          <meta name="robots" content="noindex,follow">
        </head>
        <body>
          <h1>🔥 Latest Celebrity Gossip</h1>
          <p>This story has been updated. Redirecting you to the latest gossip...</p>
          <p>If you're not redirected, <a href="#{target_url}">click here</a>.</p>
          <script>window.location.replace("#{target_url}");</script>
        </body>
        </html>
      HTML
    end
  end
end
