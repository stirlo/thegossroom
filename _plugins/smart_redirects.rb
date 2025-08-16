module Jekyll
  class SmartRedirects < Generator
    def generate(site)
      puts "\n🔍 DEBUG: Starting Smart Redirects Generator"
      puts "📊 Total celebrities in data: #{site.data['celebrities']&.keys&.count || 0}"
      puts "📊 Total posts: #{site.posts.docs.count}"

      # Test specific celebrities
      test_celebs = ['travis_kelce', 'taylor_swift']

      test_celebs.each do |celeb_key|
        puts "\n🎯 TESTING: #{celeb_key}"

        if site.data['celebrities'][celeb_key]
          puts "  ✅ Found in celebrities data"

          latest_post = find_latest_celebrity_post(site, celeb_key)
          if latest_post
            puts "  ✅ Found latest post: #{latest_post.url}"
            puts "  📅 Post date: #{latest_post.date}"
            puts "  📝 Post title: #{latest_post.data['title']}"

            # Create redirect page
            redirect_page = SmartRedirectPage.new(site, celeb_key, latest_post.url)
            site.pages << redirect_page

            puts "  📄 Created redirect: /#{celeb_key.gsub('_', '-')}/ → #{latest_post.url}"
          else
            puts "  ❌ No posts found for #{celeb_key}"
          end
        else
          puts "  ❌ Not found in celebrities data"
        end
      end

      puts "\n🎉 Debug completed"
    end

    private

    def find_latest_celebrity_post(site, celeb_key)
      latest_post = nil
      latest_date = nil
      found_posts = []

      site.posts.docs.each do |post|
        if celebrity_mentioned_in_post?(post, celeb_key)
          found_posts << {
            title: post.data['title'],
            date: post.date,
            url: post.url,
            mentions: post.data['mentions']
          }

          if latest_date.nil? || post.date > latest_date
            latest_date = post.date
            latest_post = post
          end
        end
      end

      puts "  📝 Posts found for #{celeb_key}: #{found_posts.count}"
      found_posts.each do |post|
        puts "    - #{post[:title]} (#{post[:date]}) - #{post[:url]}"
        puts "      Mentions: #{post[:mentions]}"
      end

      latest_post
    end

    def celebrity_mentioned_in_post?(post, celeb_key)
      # Check mentions data first
      if post.data['mentions'] && post.data['mentions'][celeb_key]
        puts "    ✅ Found #{celeb_key} in mentions data"
        return true
      end

      # Check title and content for celebrity name variations
      celeb_name = celeb_key.gsub('_', ' ')
      search_terms = [
        celeb_name,
        celeb_name.split.map(&:capitalize).join(' '),
        celeb_name.downcase,
        celeb_name.upcase,
        'Travis Kelce',
        'Taylor Swift'
      ]

      content_to_search = [
        post.data['title'] || '',
        post.content || '',
        post.data['excerpt'] || ''
      ].join(' ').downcase

      found_term = search_terms.find { |term| content_to_search.include?(term.downcase) }
      if found_term
        puts "    ✅ Found term '#{found_term}' in content for #{celeb_key}"
        return true
      end

      puts "    ❌ No mention of #{celeb_key} found"
      false
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
        'redirect_to' => target_url
      }

      celeb_name = celeb_key.gsub('_', ' ').split.map(&:capitalize).join(' ')

      self.content = "<!DOCTYPE html>
<html>
<head>
  <meta http-equiv=\"refresh\" content=\"0; url=#{target_url}\">
  <link rel=\"canonical\" href=\"#{target_url}\">
  <title>Redirecting to Latest #{celeb_name} Gossip</title>
</head>
<body>
  <h1>🔥 Redirecting...</h1>
  <p>Taking you to the latest <strong>#{celeb_name}</strong> gossip!</p>
  <p>If you're not redirected automatically, <a href=\"#{target_url}\">click here</a>.</p>
</body>
</html>"
    end
  end
end
