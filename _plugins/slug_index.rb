require 'json'
module Jekyll
  class SlugIndexGenerator < Generator
    safe true; priority :lowest
    def generate(site)
      slugs = site.posts.docs.map do |post|
        { "url" => post.url, "slug" => File.basename(post.url, '.*').downcase }
      end
      File.write(File.join(site.dest, 'slugs.json'), JSON.generate(slugs))
      site.keep_files << 'slugs.json'
    end
  end
end