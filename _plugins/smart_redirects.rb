module Jekyll
  class SmartRedirects < Generator
    def generate(site)
      puts "🔍 DEBUG: Starting Smart Redirects Generator"

      all_celebrities = get_all_celebrities(site)
      puts "📊 Total celebrities available: #{all_celebrities.length}"

      # Create URL aliases for common variations
      url_aliases = create_url_aliases(all_celebrities)

      # Process main celebrities
      celebrities_to_process = all_celebrities.first(100)

      celebrities_to_process.each do |celeb_key|
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

    private

    def create_url_aliases(celebrities)
      aliases = {}

      celebrities.each do |celeb_key|
        # Create common short versions
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

        # Auto-create first name aliases for two-word names
        if celeb_key.include?('_')
          first_name = celeb_key.split('_').first
          aliases[first_name] = celeb_key unless aliases[first_name]
        end
      end

      aliases
    end

    def get_all_celebrities(site)
      return [] unless site.data['celebrities']

      site.data['celebrities']
        .select { |_, data| data['drama_score'] }
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

      self.content = <<~HTML
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
end
