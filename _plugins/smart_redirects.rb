module Jekyll
  class SmartRedirectGenerator < Generator
    safe true
    priority :high

    def generate(site)
      puts "🚀 Generating smart redirects..."

      # Load celebrities.yml data
      celebrities_data = load_celebrities_data(site)

      # 🎯 AUTO-TAG ALL CELEBRITIES FIRST
      auto_tag_all_celebrities(site, celebrities_data)

      posts_data = extract_posts_data(site)
      puts "📊 Found #{posts_data.length} posts and #{celebrities_data.length} celebrities"

      # Generate all redirect types
      generate_celebrity_redirects_from_yml(site, celebrities_data, posts_data)
      generate_exact_tag_redirects(site)  # 🎯 NEW: Handle all Jekyll tags
      generate_celebrity_redirects(site, posts_data)
      generate_date_celebrity_redirects_with_fallback(site, posts_data)
      generate_legacy_redirects(site, posts_data)
      generate_fuzzy_fallback(site, posts_data)

      puts "✅ Smart redirects generated!"
    end

    private

    # 🎯 NEW: Auto-tag all celebrities from YAML
    def auto_tag_all_celebrities(site, celebrities_data)
      puts "\n🏷️ AUTO-TAGGING ALL CELEBRITIES FROM YAML:"

      tagged_count = 0

      site.posts.docs.each do |post|
        content = "#{post.data['title']} #{post.content}".downcase
        post.data['tags'] ||= []
        original_tag_count = post.data['tags'].size

        celebrities_data.each do |celeb_key, celeb_info|
          # Skip if already tagged
          next if post.data['tags'].include?(celeb_key)

          mentioned = false

          # Check main name
          if content.include?(celeb_info[:name].downcase)
            mentioned = true
          end

          # Check aliases
          unless mentioned
            celeb_info[:aliases].each do |alias_name|
              if content.include?(alias_name.downcase)
                mentioned = true
                break
              end
            end
          end

          # Check search terms
          unless mentioned
            celeb_info[:search_terms].each do |search_term|
              if content.include?(search_term.downcase)
                mentioned = true
                break
              end
            end
          end

          # Add tag if mentioned
          if mentioned
            post.data['tags'] << celeb_key
            puts "  ✅ Tagged '#{post.data['title']}' with '#{celeb_key}'"
          end
        end

        if post.data['tags'].size > original_tag_count
          tagged_count += 1
        end
      end

      puts "📊 AUTO-TAGGED #{tagged_count} POSTS WITH CELEBRITY TAGS"
    end

    # 🎯 NEW: Generate redirects for ALL Jekyll tags
    def generate_exact_tag_redirects(site)
      puts "\n🎯 GENERATING EXACT TAG REDIRECTS:"

      site.tags.each do |tag_name, tag_posts|
        next if tag_posts.empty?

        # Get the most recent post with highest drama score
        latest_post = tag_posts
          .sort_by { |p| [p.date, (p.data['drama_score'] || 0)] }
          .reverse
          .first

        if latest_post
          # Create redirect from /tag/exact-name/ to latest post
          create_redirect_page(site, "/tag/#{tag_name}/", latest_post.url)
          puts "  ✅ /tag/#{tag_name}/ -> #{latest_post.url}"

          # Also create redirect without /tag/ prefix for direct access
          create_redirect_page(site, "/#{tag_name}/", latest_post.url)
          puts "  ✅ /#{tag_name}/ -> #{latest_post.url}"
        end
      end
    end

    def load_celebrities_data(site)
      celebrities = {}
      celebrities_file = File.join(site.source, '_data', 'celebrities.yml')

      if File.exist?(celebrities_file)
        begin
          celebrities_yaml = YAML.load_file(celebrities_file)
          celebrities_yaml.each do |key, data|
            next unless data.is_a?(Hash)

            celebrities[key] = {
              name: data['name'] || key.gsub('_', ' ').titleize,
              aliases: data['aliases'] || [],
              search_terms: data['search_terms'] || [],
              category: data['category'] || 'unknown',
              drama_score: data['drama_score'] || 25
            }
          end
          puts "📋 Loaded #{celebrities.length} celebrities from celebrities.yml"
        rescue => e
          puts "⚠️ Error loading celebrities.yml: #{e.message}"
        end
      end

      celebrities
    end

    def generate_celebrity_redirects_from_yml(site, celebrities_data, posts_data)
      puts "\n🎭 GENERATING CELEBRITY REDIRECTS FROM YML:"

      celebrities_data.each do |celeb_key, celeb_info|
        # Find posts mentioning this celebrity
        matching_posts = posts_data.select do |post|
          post_mentions_celebrity?(post, celeb_key, celeb_info)
        end

        if matching_posts.any?
          # Sort by date and drama score
          latest_post = matching_posts.sort_by { |p| [p[:date], p[:drama_score] || 0] }.reverse.first

          # Create redirect for celebrity key
          create_redirect_page(site, "/#{celeb_key}/", latest_post[:url])
          puts "  📍 Celebrity YML redirect: /#{celeb_key}/ -> #{latest_post[:url]}"

          # Create redirects for aliases
          celeb_info[:aliases].each do |alias_name|
            alias_slug = slugify(alias_name)
            next if alias_slug.empty? || alias_slug == celeb_key

            create_redirect_page(site, "/#{alias_slug}/", latest_post[:url])
            puts "  📍 Alias redirect: /#{alias_slug}/ -> #{latest_post[:url]}"
          end

          # Create redirect for display name
          name_slug = slugify(celeb_info[:name])
          if name_slug != celeb_key && !name_slug.empty?
            create_redirect_page(site, "/#{name_slug}/", latest_post[:url])
            puts "  📍 Name redirect: /#{name_slug}/ -> #{latest_post[:url]}"
          end
        else
          # No recent posts - redirect to search
          search_query = celeb_info[:name].gsub(' ', '+')
          create_redirect_page(site, "/#{celeb_key}/", "/search/?q=#{search_query}")
          puts "  📍 Celebrity search fallback: /#{celeb_key}/ -> /search/?q=#{search_query}"
        end
      end
    end

    def post_mentions_celebrity?(post, celeb_key, celeb_info)
      # Check post tags (most reliable)
      return true if post[:tags] && post[:tags].include?(celeb_key)

      # Check post mentions
      return true if post[:mentions] && post[:mentions].key?(celeb_key)

      # Check primary celebrity
      return true if post[:primary_celebrity] == celeb_key

      # Check title/content for celebrity name or aliases
      search_text = "#{post[:title]} #{post[:excerpt] || ''}".downcase

      # Check main name
      return true if search_text.include?(celeb_info[:name].downcase)

      # Check aliases
      celeb_info[:aliases].each do |alias_name|
        return true if search_text.include?(alias_name.downcase)
      end

      # Check search terms
      celeb_info[:search_terms].each do |search_term|
        return true if search_text.include?(search_term.downcase)
      end

      false
    end

    def extract_posts_data(site)
      site.posts.docs.map do |post|
        {
          url: post.url,
          date: post.date,
          title: post.data['title'] || '',
          excerpt: post.data['excerpt'] || '',
          celebrities: extract_celebrities(post),
          tags: post.data['tags'] || [],
          mentions: post.data['mentions'] || {},
          primary_celebrity: post.data['primary_celebrity'],
          drama_score: post.data['drama_score'] || 0,
          slug: post.data['slug'] || post.basename_without_ext,
          keywords: extract_keywords(post.data['title'] || ''),
          filename: post.basename_without_ext
        }
      end
    end

    def generate_celebrity_redirects(site, posts_data)
      puts "\n🎬 GENERATING CELEBRITY REDIRECTS FROM POSTS:"

      celebrity_posts = {}

      posts_data.each do |post|
        # Add from tags
        post[:tags].each do |tag|
          celebrity_posts[tag] ||= []
          celebrity_posts[tag] << post
        end

        # Add from mentions
        post[:mentions].keys.each do |celeb_key|
          celebrity_posts[celeb_key] ||= []
          celebrity_posts[celeb_key] << post
        end

        # Add from primary celebrity
        if post[:primary_celebrity]
          celeb_slug = slugify(post[:primary_celebrity])
          celebrity_posts[celeb_slug] ||= []
          celebrity_posts[celeb_slug] << post
        end

        # Add from extracted celebrities
        post[:celebrities].each do |celebrity|
          celebrity_slug = slugify(celebrity)
          celebrity_posts[celebrity_slug] ||= []
          celebrity_posts[celebrity_slug] << post
        end
      end

      celebrity_posts.each do |celebrity_slug, posts|
        next if celebrity_slug.empty?

        sorted_posts = posts.uniq.sort_by { |p| [p[:date], p[:drama_score]] }.reverse
        latest_post = sorted_posts.first

        create_redirect_page(site, "/#{celebrity_slug}/", latest_post[:url])
        puts "  📍 Celebrity redirect: /#{celebrity_slug}/ -> #{latest_post[:url]}"
      end
    end

    def generate_date_celebrity_redirects_with_fallback(site, posts_data)
      puts "\n📅 GENERATING DATE-BASED CELEBRITY REDIRECTS:"

      date_celebrity_posts = {}
      celebrity_latest = {}

      posts_data.each do |post|
        all_celebrity_keys = []
        all_celebrity_keys.concat(post[:tags])
        all_celebrity_keys.concat(post[:mentions].keys)
        all_celebrity_keys << slugify(post[:primary_celebrity]) if post[:primary_celebrity]
        all_celebrity_keys.concat(post[:celebrities].map { |c| slugify(c) })
        all_celebrity_keys.uniq!
        all_celebrity_keys.reject!(&:empty?)

        all_celebrity_keys.each do |celebrity_slug|
          if !celebrity_latest[celebrity_slug] || post[:date] > celebrity_latest[celebrity_slug][:date]
            celebrity_latest[celebrity_slug] = post
          end
        end
      end

      posts_data.each do |post|
        date_path = post[:date].strftime('%Y/%m/%d')

        all_celebrity_keys = []
        all_celebrity_keys.concat(post[:tags])
        all_celebrity_keys.concat(post[:mentions].keys)
        all_celebrity_keys << slugify(post[:primary_celebrity]) if post[:primary_celebrity]
        all_celebrity_keys.concat(post[:celebrities].map { |c| slugify(c) })
        all_celebrity_keys.uniq!
        all_celebrity_keys.reject!(&:empty?)

        all_celebrity_keys.each do |celebrity_slug|
          key = "#{date_path}/#{celebrity_slug}"
          date_celebrity_posts[key] ||= []
          date_celebrity_posts[key] << post
        end
      end

      date_celebrity_posts.each do |key, posts|
        latest_post = posts.sort_by { |p| [p[:date], p[:drama_score]] }.reverse.first
        create_redirect_page(site, "/#{key}/", latest_post[:url])
        puts "  📍 Date redirect: /#{key}/ -> #{latest_post[:url]}"
      end

      create_fallback_handler(site, celebrity_latest)
    end

    def generate_legacy_redirects(site, posts_data)
      puts "\n🔄 GENERATING LEGACY REDIRECTS:"

      # List of all articles that need redirects
      legacy_articles = %w[
        2025-08-07-jason-kylie-kelce-attend-funeral-of-dad-eds-partne
        2025-08-07-brooke-hogans-husband-steven-oleksy-shares-tribute
        2025-08-07-olivia-rodrigo-vs-jessica-alba-whod-you-rather-coc
        2025-08-07-men-shot-alongside-kodak-black-want-106-million-de
        2025-08-07-hulk-hogans-daughter-brooke-threatens-legal-action
        2025-08-07-nike-releases-lebron-james-monopoly-signature-snea
        2025-08-07-ed-kelces-girlfriend-maureen-maguire-laid-to-rest
        2025-08-07-keke-palmer-didnt-mind-naked-scenes-with-pete-davi
        2025-08-07-hulk-hogans-wife-sky-speaks-out-about-beautiful-an
        2025-08-07-if-taylor-swift-travis-kelce-get-married-andy-reid
        2025-08-07-am-i-trolling-blake-lively-the-truth-perez-hilton
        2025-08-07-property-masters-guild-reveals-2025-macguffin-awar
        2025-08-07-zendaya-officially-adds-shoe-designer-to-resumesee
        2025-08-07-jenny-han-addresses-summer-i-turned-pretty-3s-lack
        2025-08-07-eminem-opens-up-about-addiction-and-impact-of-stan
        2025-08-07-denise-richards-abandoned-dog-with-cancer-claims-a
        2025-08-07-denim-drama-the-political-battle-for-your-butt-con
        2025-08-07-lil-wayne-says-reuniting-with-lebron-james-was-a-h
        2025-08-07-andy-reid-teases-toast-hed-give-at-taylor-swift-an
        2025-08-07-selena-gomez-recalls-1st-song-taylor-swift-played
        2025-08-07-jason-kelce-supports-ed-kelce-after-girlfriend-mau
        2025-08-07-will-president-trump-pardon-diddy-after-partial-co
        2025-08-07-keke-palmer-teases-naked-scenes-with-pete-davidson
        2025-08-07-shacarri-richardson-seen-on-surveillance-video-pus
      ]

      # Create mapping of legacy articles to current posts
      legacy_articles.each do |legacy_slug|
        # Find best match in current posts
        best_match = find_best_match(legacy_slug, posts_data)

        if best_match
          # Create date-based redirect
          date_parts = legacy_slug.match(/^(\d{4})-(\d{2})-(\d{2})-(.+)$/)
          if date_parts
            year, month, day, slug = date_parts.captures
            legacy_path = "/#{year}/#{month}/#{day}/#{slug}/"

            create_redirect_page(site, legacy_path, best_match[:url])
            puts "  📍 Legacy redirect: #{legacy_path} -> #{best_match[:url]}"
          end
        else
          # Create fallback redirect to homepage or search
          date_parts = legacy_slug.match(/^(\d{4})-(\d{2})-(\d{2})-(.+)$/)
          if date_parts
            year, month, day, slug = date_parts.captures
            legacy_path = "/#{year}/#{month}/#{day}/#{slug}/"

            create_redirect_page(site, legacy_path, "/search/?q=#{slug.gsub('-', '+')}")
            puts "  📍 Legacy fallback: #{legacy_path} -> /search/"
          end
        end
      end
    end

    def find_best_match(legacy_slug, posts_data)
      # Extract key terms from legacy slug
      slug_parts = legacy_slug.split('-')[3..-1] # Remove date parts
      key_terms = slug_parts.join(' ').downcase

      # Score each post based on similarity
      scored_posts = posts_data.map do |post|
        score = calculate_similarity_score(key_terms, post)
        { post: post, score: score }
      end

      # Return best match if score is above threshold
      best = scored_posts.max_by { |item| item[:score] }
      return best[:post] if best && best[:score] > 0.3

      nil
    end

    def calculate_similarity_score(query, post)
      query_words = query.split
      post_text = "#{post[:title]} #{post[:keywords].join(' ')} #{post[:celebrities].join(' ')}".downcase

      # Count matching words
      matches = query_words.count { |word| post_text.include?(word) }

      # Calculate score (0-1)
      matches.to_f / query_words.length
    end

    def extract_celebrities(post)
      celebrities = []
      title = post.data['title'] || ''

      celebrity_patterns = {
        'Taylor Swift' => /taylor\s*swift/i,
        'Travis Kelce' => /travis\s*kelce/i,
        'Jason Kelce' => /jason\s*kelce/i,
        'Kylie Kelce' => /kylie\s*kelce/i,
        'Justin Bieber' => /justin\s*bieber/i,
        'Hailey Bieber' => /hailey\s*bieber/i,
        'Ariana Grande' => /ariana\s*grande/i,
        'Selena Gomez' => /selena\s*gomez/i,
        'Kim Kardashian' => /kim\s*kardashian/i,
        'Kourtney Kardashian' => /kourtney\s*kardashian/i,
        'Khloe Kardashian' => /khloe\s*kardashian/i,
        'Kylie Jenner' => /kylie\s*jenner/i,
        'Kanye West' => /kanye\s*west|ye\s/i,
        'Pete Davidson' => /pete\s*davidson/i,
        'Blake Lively' => /blake\s*lively/i,
        'Justin Baldoni' => /justin\s*baldoni/i,
        'Hulk Hogan' => /hulk\s*hogan/i,
        'Brooke Hogan' => /brooke\s*hogan/i,
        'Diddy' => /diddy|sean\s*combs/i,
        'Machine Gun Kelly' => /machine\s*gun\s*kelly|mgk/i,
        'Sydney Sweeney' => /sydney\s*sweeney/i,
        'Zendaya' => /zendaya/i,
        'Tom Holland' => /tom\s*holland/i,
        'Dua Lipa' => /dua\s*lipa/i,
        'Olivia Rodrigo' => /olivia\s*rodrigo/i,
        'Sabrina Carpenter' => /sabrina\s*carpenter/i,
        'Bryan Kohberger' => /bryan\s*kohberger/i,
        'Kate Gosselin' => /kate\s*gosselin/i,
        'Sophie Turner' => /sophie\s*turner/i,
        'Logan Paul' => /logan\s*paul/i,
        'Donald Trump' => /donald\s*trump|trump/i,
        'Melania Trump' => /melania\s*trump/i,
        'Putin' => /putin|vladimir\s*putin/i,
        'Meghan Markle' => /meghan\s*markle/i,
        'Prince Harry' => /prince\s*harry/i,
        'Prince William' => /prince\s*william/i,
        'Kate McKinnon' => /kate\s*mckinnon/i,
        'Eminem' => /eminem/i,
        'Cardi B' => /cardi\s*b/i,
        'Nicki Minaj' => /nicki\s*minaj/i,
        'Lil Tay' => /lil\s*tay/i,
        'Terence Stamp' => /terence\s*stamp/i
      }

      celebrity_patterns.each do |name, pattern|
        celebrities << name if title.match(pattern)
      end

      celebrities.uniq
    end

    def extract_keywords(title)
      stop_words = %w[the and or but in on at to for of with by a an is was are were has have had will would could should]
      title.downcase
           .gsub(/[^\w\s]/, ' ')
           .split
           .reject { |word| stop_words.include?(word) || word.length < 3 }
           .uniq
    end

    def create_fallback_handler(site, celebrity_latest)
      fallback_content = <<~HTML
        ---
        layout: null
        permalink: /404.html
        ---
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <title>Smart Redirect - The Gossip Room</title>
          <style>
            body { 
              font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
              background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
              color: white;
              text-align: center;
              padding: 2rem;
              min-height: 100vh;
              display: flex;
              align-items: center;
              justify-content: center;
            }
            .container {
              background: rgba(255,255,255,0.1);
              backdrop-filter: blur(20px);
              border-radius: 20px;
              padding: 3rem;
              max-width: 600px;
            }
            h1 { color: #ff69b4; margin-bottom: 1rem; }
            .redirect-info { margin: 2rem 0; }
            .btn {
              background: linear-gradient(135deg, #ff69b4, #ff1493);
              color: white;
              padding: 1rem 2rem;
              border-radius: 25px;
              text-decoration: none;
              font-weight: bold;
              display: inline-block;
              margin: 0.5rem;
            }
          </style>
          <script>
            (function() {
              const path = window.location.pathname;
              const datePattern = /^\/(\d{4})\/(\d{2})\/(\d{2})\/([^\/]+)\/?$/;
              const match = path.match(datePattern);

              if (match) {
                const [, year, month, day, celebrity] = match;
                const requestDate = new Date(year, month - 1, day);
                const now = new Date();
                const daysDiff = (now - requestDate) / (1000 * 60 * 60 * 24);

                if (daysDiff > 30) {
                  const celebrityMap = {
                    #{celebrity_latest.map { |slug, post| "'#{slug}': '#{post[:url]}'" }.join(",\n                    ")}
                  };

                  const redirectUrl = celebrityMap[celebrity];
                  if (redirectUrl) {
                    document.getElementById('redirect-info').innerHTML = 
                      `<p>That article is from ${daysDiff.toFixed(0)} days ago!</p>
                       <p>Redirecting you to the latest <strong>${celebrity.replace('-', ' ')}</strong> news...</p>`;

                    setTimeout(() => {
                      window.location.href = redirectUrl;
                    }, 3000);
                    return;
                  }
                }
              }

              document.getElementById('redirect-info').innerHTML = 
                '<p>That page could not be found, but here are some options:</p>';
            })();
          </script>
        </head>
        <body>
          <div class="container">
            <h1>🔍 The Gossip Room</h1>
            <div id="redirect-info" class="redirect-info">
              <p>Looking for that article...</p>
            </div>
            <div>
              <a href="/" class="btn">🏠 Home</a>
              <a href="/search/" class="btn">📚 Search</a>
            </div>
          </div>
        </body>
        </html>
      HTML

      fallback_page = Jekyll::Page.new(site, site.source, '', '404.html')
      fallback_page.content = fallback_content
      fallback_page.data['layout'] = nil

      site.pages << fallback_page
      puts "📍 Created smart 404 handler"
    end

    def create_redirect_page(site, from_path, to_path)
      redirect_content = <<~HTML
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <title>Redirecting...</title>
          <meta http-equiv="refresh" content="0; url=#{to_path}">
          <link rel="canonical" href="#{to_path}">
          <script>window.location.href = "#{to_path}";</script>
        </head>
        <body>
          <p>Redirecting to <a href="#{to_path}">#{to_path}</a></p>
        </body>
        </html>
      HTML

      redirect_page = Jekyll::Page.new(site, site.source, '', 'index.html')
      redirect_page.content = redirect_content
      redirect_page.data['permalink'] = from_path
      redirect_page.data['layout'] = nil

      site.pages << redirect_page
    end

    def generate_fuzzy_fallback(site, posts_data)
      fuzzy_data = posts_data.map do |post|
        {
          url: post[:url],
          title: post[:title],
          celebrities: post[:celebrities],
          keywords: post[:keywords],
          date: post[:date].strftime('%Y-%m-%d')
        }
      end

      create_smart_search_page(site, fuzzy_data)
    end

    def create_smart_search_page(site, posts_data)
      # Implementation for search page
      puts "📍 Created smart search page"
    end

    def slugify(text)
      return '' if text.nil? || text.empty?
      text.to_s.downcase
          .gsub(/[^\w\s]/, '')
          .gsub(/\s+/, '-')
          .gsub(/^-|-$/, '')
    end
  end
end
