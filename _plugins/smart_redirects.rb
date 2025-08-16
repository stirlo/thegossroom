module Jekyll
  class SmartRedirects < Generator
    def generate(site)
      # Create redirect pages for GitHub Pages
      site.data['celebrities'].each do |celeb_key, celeb_data|
        latest_post = find_latest_celebrity_post(site, celeb_key)
        if latest_post
          # Create redirect page
          redirect_page = RedirectPage.new(site, celeb_key, latest_post.url)
          site.pages << redirect_page
        end
      end
    end

    private

    def find_latest_celebrity_post(site, celeb_key)
      latest_post = nil
      latest_date = nil

      site.posts.docs.each do |post|
        if post.data['mentions'] && post.data['mentions'][celeb_key]
          post_date = post.date
          if latest_date.nil? || post_date > latest_date
            latest_date = post_date
            latest_post = post
          end
        end
      end

      latest_post
    end
  end

  class RedirectPage < Page
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

      self.content = <<~HTML
        <!DOCTYPE html>
        <html>
        <head>
          <meta http-equiv="refresh" content="0; url=#{target_url}">
          <link rel="canonical" href="#{target_url}">
        </head>
        <body>
          <p>Redirecting to <a href="#{target_url}">latest #{celeb_key.humanize} gossip</a>...</p>
        </body>
        </html>
      HTML
    end
  end
end
