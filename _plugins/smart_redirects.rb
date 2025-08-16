module Jekyll
  class SmartRedirects < Generator
    def generate(site)
      # Generate _redirects file for Netlify/GitHub Pages
      redirects = []

      # Redirect old celebrity posts to latest
      site.data['celebrities'].each do |celeb_key, celeb_data|
        latest_post = find_latest_celebrity_post(site, celeb_key)
        if latest_post
          # Redirect pattern: /celebrity-name/* -> latest post
          pattern = "/#{celeb_key.gsub('_', '-')}/*"
          redirects << "#{pattern} #{latest_post.url} 302"
        end
      end

      # Create _redirects file
      File.write('_redirects', redirects.join("\n"))
    end
  end
end
