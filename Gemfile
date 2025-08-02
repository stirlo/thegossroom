source "https://rubygems.org"

# Use GitHub Pages gem for compatibility
gem "github-pages", "~> 228", group: :jekyll_plugins

# If you want to use GitHub Pages, remove the "gem "jekyll"" above and
# uncomment the line below. To upgrade, run `bundle update github-pages`.
# gem "jekyll", "~> 4.3.0"  # COMMENTED OUT - conflicts with github-pages

# This is the default theme for new Jekyll sites.
gem "minima", "~> 2.5"

# If you have any plugins, put them here!
group :jekyll_plugins do
  gem "jekyll-feed", "~> 0.12"
  gem "jekyll-sitemap"
  gem "jekyll-seo-tag"
  gem "jekyll-paginate"
  # Remove these - not supported by GitHub Pages
  # gem "jekyll-archives"
  # gem "jekyll-redirect-from"
  # gem "jekyll-compose"
end

# Windows and JRuby does not include zoneinfo files, so bundle the tzinfo-data gem
# and associated library.
platforms :mingw, :x64_mingw, :mswin, :jruby do
  gem "tzinfo", ">= 1", "< 3"
  gem "tzinfo-data"
end

# Performance-booster for watching directories on Windows
gem "wdm", "~> 0.1.1", :platforms => [:mingw, :x64_mingw, :mswin]

# Lock `http_parser.rb` gem to `v0.6.x` on JRuby builds since newer versions of the gem
# do not have a Java counterpart.
gem "http_parser.rb", "~> 0.6.0", :platforms => [:jruby]

# Remove these - they're for local development, not GitHub Pages
# gem "nokogiri", "~> 1.15"
# gem "feedjira", "~> 3.2"
# gem "chronic", "~> 0.10"
# gem "sanitize", "~> 6.0"
