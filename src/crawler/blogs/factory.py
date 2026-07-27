from src.crawler.blogs.rss_blog_adapter import RssBlogAdapter
from src.crawler.blogs.generic_html_adapter import GenericHtmlAdapter
from src.crawler.blogs.base_blog_adapter import BaseBlogAdapter

class BlogAdapterFactory:
    @staticmethod
    def get_adapter(config: dict) -> BaseBlogAdapter:
        crawl_type = config.get('crawl_type', 'auto')
        
        if crawl_type == 'rss':
            return RssBlogAdapter(config)
        elif crawl_type == 'html':
            return GenericHtmlAdapter(config)
        else:
            class AutoAdapter(BaseBlogAdapter):
                def fetch_new_posts(self):
                    rss = RssBlogAdapter(self.config)
                    posts = rss.fetch_new_posts()
                    if not posts:
                        html = GenericHtmlAdapter(self.config)
                        posts = html.fetch_new_posts()
                    return posts
            return AutoAdapter(config)
