module Jekyll
  class SmartRedirects < Generator
    def generate(site)
      # Create redirect pages for GitHub Pages
      site.data['celebrities'].each do |celeb_key, celeb_data|
        latest_post = find_latest_celebrity_post(site, celeb_key)
        if latest_post
          # Create redirect page
          redirect_page = SmartRedirectPage.new(site, celeb_key, latest_post.url)
          site.pages << redirect_page
        end
      end
    end

    private

    def find_latest_celebrity_post(site, celeb_key)
      latest_post = nil
      latest_date = nil

      site.posts.docs.each do |post|
        # Check if celebrity is mentioned in the post
        if celebrity_mentioned_in_post?(post, celeb_key)
          post_date = post.date
          if latest_date.nil? || post_date > latest_date
            latest_date = post_date
            latest_post = post
          end
        end
      end

      latest_post
    end

    def celebrity_mentioned_in_post?(post, celeb_key)
      # Check mentions data
      if post.data['mentions'] && post.data['mentions'][celeb_key]
        return true
      end

      # Check title and content for celebrity name variations
      celeb_name = celeb_key.gsub('_', ' ')
      search_terms = [
        celeb_name,
        celeb_name.split.map(&:capitalize).join(' '),
        celeb_name.downcase,
        celeb_name.upcase
      ]

      content_to_search = [
        post.data['title'] || '',
        post.content || '',
        post.data['excerpt'] || ''
      ].join(' ').downcase

      search_terms.any? { |term| content_to_search.include?(term.downcase) }
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

      # Simple, bulletproof HTML
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
