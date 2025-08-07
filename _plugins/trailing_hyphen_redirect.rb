module Jekyll
  class TrailingHyphenRedirect < Generator
    safe true
    priority :low

    def generate(site)
      site.posts.docs.each do |post|
        correct_url = post.url

        # Only handle trailing hyphen before .html pattern
        if correct_url =~ /\/(\d{4})\/(\d{2})\/(\d{2})\/(.+)\.html$/
          date_path = "/#{$1}/#{$2}/#{$3}"
          slug = $4

          # Create redirect from trailing hyphen version
          broken_hyphen_url = "#{date_path}/#{slug}-.html"
          site.pages << RedirectPage.new(site, site.source, broken_hyphen_url, correct_url)
        end
      end
    end
  end

  class RedirectPage < Page
    def initialize(site, base, broken_url, correct_url)
      @site = site
      @base = base

      url_parts = broken_url.split('/')
      @dir = url_parts[0..-2].join('/')
      @name = url_parts[-1]

      self.process(@name)
      self.data = { 'layout' => nil, 'sitemap' => false }

      self.content = <<~HTML
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <title>Redirecting...</title>
          <meta http-equiv="refresh" content="0; url=#{correct_url}">
          <link rel="canonical" href="#{correct_url}">
        </head>
        <body>
          <p>Redirecting to <a href="#{correct_url}">#{correct_url}</a></p>
        </body>
        </html>
      HTML
    end
  end
end
