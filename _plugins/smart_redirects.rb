# _plugins/smart_redirects.rb
module Jekyll
  class SmartRedirectGenerator < Generator
    safe true
    priority :high

    def generate(site)
      puts "🚀 Generating smart redirects..."

      posts_data = extract_posts_data(site)
      puts "📊 Found #{posts_data.length} posts to analyze"

      generate_celebrity_redirects(site, posts_data)
      generate_date_celebrity_redirects_with_fallback(site, posts_data)
      generate_fuzzy_fallback(site, posts_data)

      puts "✅ Smart redirects generated!"
    end

    private

    def extract_posts_data(site)
      site.posts.docs.map do |post|
        celebrities = extract_celebrities(post)
        {
          url: post.url,
          date: post.date,
          title: post.data['title'] || '',
          celebrities: celebrities,
          slug: post.data['slug'] || post.basename_without_ext,
          keywords: extract_keywords(post.data['title'] || '')
        }
      end
    end

    def extract_celebrities(post)
      celebrities = []
      title = post.data['title'] || ''

      # Extract from title - based on your RSS patterns
      celebrity_patterns = {
        'Taylor Swift' => /taylor\s*swift/i,
        'Travis Kelce' => /travis\s*kelce/i,
        'Justin Bieber' => /justin\s*bieber/i,
        'Ariana Grande' => /ariana\s*grande/i,
        'Selena Gomez' => /selena\s*gomez/i,
        'Dua Lipa' => /dua\s*lipa/i,
        'Billie Eilish' => /billie\s*eilish/i,
        'Harry Styles' => /harry\s*styles/i,
        'Olivia Rodrigo' => /olivia\s*rodrigo/i,
        'Bad Bunny' => /bad\s*bunny/i,
        'Kanye West' => /kanye\s*west|ye\s/i,
        'Kim Kardashian' => /kim\s*kardashian/i,
        'Beyoncé' => /beyonc[eé]/i,
        'Rihanna' => /rihanna/i,
        'Drake' => /drake/i
      }

      celebrity_patterns.each do |name, pattern|
        if title.match(pattern)
          celebrities << name
        end
      end

      # Extract from tags if available
      if post.data['tags']
        post.data['tags'].each do |tag|
          normalized = normalize_tag_to_celebrity(tag)
          celebrities << normalized if normalized
        end
      end

      celebrities.uniq
    end

    def normalize_tag_to_celebrity(tag)
      tag_map = {
        'taylorswift' => 'Taylor Swift',
        'traviskelce' => 'Travis Kelce',
        'justinbieber' => 'Justin Bieber',
        'arianagrande' => 'Ariana Grande',
        'selenagomez' => 'Selena Gomez',
        'dualipa' => 'Dua Lipa',
        'billieeilish' => 'Billie Eilish',
        'harrystyles' => 'Harry Styles',
        'oliviarodrigo' => 'Olivia Rodrigo',
        'badbunny' => 'Bad Bunny',
        'kanyewest' => 'Kanye West',
        'kimkardashian' => 'Kim Kardashian',
        'beyonce' => 'Beyoncé',
        'rihanna' => 'Rihanna',
        'drake' => 'Drake'
      }

      clean_tag = tag.downcase.gsub(/[^a-z]/, '')
      tag_map[clean_tag]
    end

    def extract_keywords(title)
      # Extract meaningful keywords from title
      stop_words = %w[the and or but in on at to for of with by]
      title.downcase
           .gsub(/[^\w\s]/, ' ')
           .split
           .reject { |word| stop_words.include?(word) || word.length < 3 }
           .uniq
    end

    def generate_celebrity_redirects(site, posts_data)
      celebrity_posts = {}

      posts_data.each do |post|
        post[:celebrities].each do |celebrity|
          celebrity_slug = slugify(celebrity)
          celebrity_posts[celebrity_slug] ||= []
          celebrity_posts[celebrity_slug] << post
        end
      end

      celebrity_posts.each do |celebrity_slug, posts|
        sorted_posts = posts.sort_by { |p| p[:date] }.reverse
        latest_post = sorted_posts.first

        # /celebrity-name/ -> latest post
        create_redirect_page(site, "/#{celebrity_slug}/", latest_post[:url])

        puts "📍 Created redirect: /#{celebrity_slug}/ -> #{latest_post[:url]}"
      end
    end

    def generate_date_celebrity_redirects_with_fallback(site, posts_data)
      date_celebrity_posts = {}
      celebrity_latest = {}

      # Build celebrity latest posts map for fallback
      posts_data.each do |post|
        post[:celebrities].each do |celebrity|
          celebrity_slug = slugify(celebrity)
          if !celebrity_latest[celebrity_slug] || post[:date] > celebrity_latest[celebrity_slug][:date]
            celebrity_latest[celebrity_slug] = post
          end
        end
      end

      # Build date-specific redirects
      posts_data.each do |post|
        date_path = post[:date].strftime('%Y/%m/%d')

        post[:celebrities].each do |celebrity|
          celebrity_slug = slugify(celebrity)
          key = "#{date_path}/#{celebrity_slug}"

          date_celebrity_posts[key] ||= []
          date_celebrity_posts[key] << post
        end
      end

      # Create date-specific redirects
      date_celebrity_posts.each do |key, posts|
        if posts.length > 1
          # Multiple posts - redirect to most recent
          latest_post = posts.sort_by { |p| p[:date] }.reverse.first
          create_redirect_page(site, "/#{key}/", latest_post[:url])
          puts "📍 Created date redirect: /#{key}/ -> #{latest_post[:url]}"
        else
          # Single post - create redirect
          create_redirect_page(site, "/#{key}/", posts.first[:url])
          puts "📍 Created date redirect: /#{key}/ -> #{posts.first[:url]}"
        end
      end

      # CREATE FALLBACK HANDLER for old dates (30+ days)
      create_fallback_handler(site, celebrity_latest)
    end

    def create_fallback_handler(site, celebrity_latest)
      # Create JavaScript handler for old date patterns
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
            // Smart redirect logic for old dates
            (function() {
              const path = window.location.pathname;
              const datePattern = /^\/(\d{4})\/(\d{2})\/(\d{2})\/([^\/]+)\/?$/;
              const match = path.match(datePattern);

              if (match) {
                const [, year, month, day, celebrity] = match;
                const requestDate = new Date(year, month - 1, day);
                const now = new Date();
                const daysDiff = (now - requestDate) / (1000 * 60 * 60 * 24);

                // If older than 30 days, redirect to latest
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

              // Show 404 for other cases
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
              <a href="/archive/" class="btn">📚 Archive</a>
            </div>
          </div>
        </body>
        </html>
      HTML

      fallback_page = Jekyll::Page.new(site, site.source, '', '404.html')
      fallback_page.content = fallback_content
      fallback_page.data['layout'] = nil

      site.pages << fallback_page
      puts "📍 Created smart 404 handler with 30+ day fallback"
    end

    def generate_fuzzy_fallback(site, posts_data)
      # Create smart search page for unmatched URLs
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

    def create_redirect_page(site, from_path, to_path)
      # Create HTML redirect page
      redirect_content = <<~HTML
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <title>Redirecting...</title>
          <meta http-equiv="refresh" content="0; url=#{to_path}">
          <link rel="canonical" href="#{to_path}">
          <script>window.location.href = "#{to_path}";</script>
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
              padding: 2rem;
            }
          </style>
        </head>
        <body>
          <div class="container">
            <h1>🚀 Redirecting...</h1>
            <p>Taking you to <a href="#{to_path}" style="color: #ff69b4;">#{to_path}</a></p>
          </div>
        </body>
        </html>
      HTML

      redirect_page = Jekyll::Page.new(site, site.source, '', 'index.html')
      redirect_page.content = redirect_content
      redirect_page.data['permalink'] = from_path
      redirect_page.data['layout'] = nil

      site.pages << redirect_page
    end

    def create_smart_search_page(site, posts_data)
      search_content = <<~HTML
        ---
        layout: default
        title: "Smart Search - The Gossip Room"
        permalink: /search/
        ---

        <div class="smart-search">
          <h1>🔍 Smart Search</h1>
          <p>Find any article by celebrity, topic, or keywords!</p>

          <div class="search-container">
            <input type="text" id="smart-search" placeholder="Search for celebrity, topic, or keywords..." />
            <div id="search-results"></div>
          </div>

          <script>
            const postsData = #{posts_data.to_json};

            document.getElementById('smart-search').addEventListener('input', function(e) {
              const query = e.target.value.toLowerCase();
              if (query.length < 2) {
                document.getElementById('search-results').innerHTML = '';
                return;
              }

              const results = postsData.filter(post => {
                return post.title.toLowerCase().includes(query) ||
                       post.celebrities.some(c => c.toLowerCase().includes(query)) ||
                       post.keywords.some(k => k.toLowerCase().includes(query));
              }).slice(0, 10);

              const resultsHtml = results.map(post => 
                `<div class="search-result">
                  <a href="${post.url}">
                    <h3>${post.title}</h3>
                    <p>📅 ${post.date} | 👤 ${post.celebrities.join(', ')}</p>
                  </a>
                </div>`
              ).join('');

              document.getElementById('search-results').innerHTML = resultsHtml;
            });
          </script>

          <style>
            .smart-search { max-width: 800px; margin: 2rem auto; padding: 0 1rem; }
            .search-container { margin: 2rem 0; }
            #smart-search { 
              width: 100%; 
              padding: 1rem; 
              font-size: 1.1rem; 
              border: 2px solid #ddd; 
              border-radius: 8px; 
            }
            .search-result { 
              margin: 1rem 0; 
              padding: 1rem; 
              border: 1px solid #eee; 
              border-radius: 6px; 
            }
            .search-result a { text-decoration: none; color: inherit; }
            .search-result:hover { background: #f9f9f9; }
          </style>
        </div>
      HTML

      search_page = Jekyll::Page.new(site, site.source, '', 'search.html')
      search_page.content = search_content
      search_page.data['layout'] = nil

      site.pages << search_page
      puts "📍 Created smart search page"
    end

    def slugify(text)
      text.downcase
          .gsub(/[^\w\s]/, '')
          .gsub(/\s+/, '-')
          .gsub(/^-|-$/, '')
    end
  end
end
