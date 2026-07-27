import os
import json
import time
import logging
from pydantic import BaseModel

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

logger = logging.getLogger(__name__)

class ReleaseItem(BaseModel):
    title: str
    description: str
    ticket_id: str
    ticket_url: str

class BreakingChangeItem(BaseModel):
    title: str
    description: str
    ticket_id: str
    ticket_url: str
    change_type: str

class AdvisorSummary(BaseModel):
    overview: str

class SummarizedRelease(BaseModel):
    advisor_summary: AdvisorSummary
    cves: list[ReleaseItem]
    breaking_changes: list[BreakingChangeItem]
    bug_fixes: list[ReleaseItem]
    new_features: list[ReleaseItem]

class BlogSummary(BaseModel):
    summary_content: str
    keywords_tags: list[str]

class GeminiClient:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        self.model_id = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
        
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            logger.warning("GEMINI_API_KEY is missing or not set properly.")
        
        if genai and self.api_key and self.api_key != "your_gemini_api_key_here":
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def _generate_with_retry(self, prompt: str, config, max_retries=3):
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=prompt,
                    config=config
                )
                return response
            except Exception as e:
                error_str = str(e)
                if '429' in error_str or '429 Too Many Requests' in error_str or 'RESOURCE_EXHAUSTED' in error_str:
                    wait_time = 15 * (attempt + 1)
                    logger.warning(f"Rate limit hit (429). Waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Gemini API Error: {e}")
                    raise e
        raise Exception("Max retries exceeded for Gemini API due to Rate Limits.")

    def summarize_release_one_shot(self, notes_dict: dict) -> dict:
        if not self.client:
            logger.error("GeminiClient not initialized. Missing API Key.")
            return {}
            
        safe_content = json.dumps(notes_dict, ensure_ascii=False)[:100000]
            
        prompt = f"""
        You are a senior software/data engineer analyzing release notes. Please read the entire Release Notes below:
        {safe_content}
        
        Task:
        1. Classify ALL items in the release notes into exactly 4 groups. DO NOT MISS ANY ITEM. Follow these STRICT rules:
           - CVEs: Security vulnerabilities, CVEs, and security patches.
           - Breaking Changes: Any backwards-incompatible changes, removals (e.g., dropping databases/columns), deprecations, or downgrade compatibility issues. (Example: Dropping a column family on downgrade MUST be a Breaking Change).
           - Bug Fixes: Error resolutions, memory leak fixes, crash preventions, and logic corrections.
           - New Features: New capabilities, performance optimizations, refactoring, and documentation updates. (NOTE: All documentation updates MUST go here, NOT in Bug Fixes).
        2. For each item, extract the `ticket_id` (e.g. KAFKA-14902) and `ticket_url`.
        3. Rewrite the content of each item (`title` and `description`) to be smooth, professional, and easy to understand for end-users, while preserving the core technical meaning.
        4. For Breaking Changes, you MUST classify the `change_type` as one of: REMOVED, REPLACED, DEPRECATED, or OTHER.
        5. Create an `advisor_summary.overview` that provides an objective, narrative summary of the main focus of this release (e.g., "This release focuses on..."). DO NOT use imperative language like "Upgrade immediately".
        6. CRITICAL LANGUAGE AND CONTEXT RULES:
           - Output EVERYTHING entirely in English.
           - DO NOT compress or shorten the technical context. Ensure the rewritten descriptions remain fully detailed, comprehensive, and preserve all original technical nuances and configurations.
        """
        
        logger.info("Calling Gemini API to summarize release one-shot...")
        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SummarizedRelease,
                temperature=0.2
            )
            time.sleep(4)
            response = self._generate_with_retry(prompt, config)
            result = json.loads(response.text)
            return result
        except Exception as e:
            logger.error(f"Failed to summarize release via Gemini: {e}")
            return {}

    def summarize_blog_post(self, content: str) -> dict:
        if not self.client:
            return {"summary_content": "No API Key provided. Cannot summarize.", "keywords_tags": []}
            
        safe_content = content[:100000] # Gemini Flash supports large context
        word_count = len(safe_content.split())
        
        if word_count < 1000:
            length_instruction = "Viết tóm tắt ngắn gọn khoảng 100 - 150 từ (tương đương 3-4 câu hoặc 1 đoạn ngắn + 2-3 bullet points)."
        elif word_count < 3000:
            length_instruction = "Viết tóm tắt chi tiết khoảng 200 - 300 từ (chia 2-3 ý chính, mỗi ý có giải thích kèm bullet points để không bỏ sót các thiết lập/luận điểm quan trọng)."
        else:
            length_instruction = "Viết tóm tắt tổng thể khoảng 400 - 500 từ (tập trung vào bức tranh tổng thể và kết quả, lọc bỏ các chi tiết mã nguồn rườm rà)."
            
        prompt = f"""
Bạn là một chuyên gia phân tích dữ liệu và công nghệ (Data Engineering/Data Science). 
Hãy đọc, hiểu và tóm tắt lại bài viết blog dưới đây một cách súc tích, phản ánh trọn vẹn và rõ ý nội dung xuyên suốt.

NỘI DUNG BÀI VIẾT:
{safe_content}

YÊU CẦU ĐỊNH DẠNG:
- summary_content: Một đoạn văn bản Markdown trình bày trôi chảy. Tùy thuộc vào loại bài viết (tutorial, chia sẻ kiến trúc, bản tin...), hãy tóm tắt linh hoạt sao cho người đọc nắm được: bài toán/bối cảnh, kiến trúc/giải pháp đề xuất, công nghệ sử dụng, các điểm triển khai kỹ thuật cần lưu ý, và kết quả/hiệu năng (nếu có). Trình bày kết hợp văn xuôi và danh sách (bullet points) sao cho tự nhiên nhất.
- keywords_tags: Mảng các chuỗi hashtag liên quan đến công nghệ (ví dụ: #kafka) và lĩnh vực (ví dụ: #data-engineering, #lakehouse).

GÓC NHÌN TRÌNH BÀY (QUAN TRỌNG):
- TUYỆT ĐỐI KHÔNG dùng các cụm từ mở đầu như "Bài viết này...", "Tác giả chia sẻ...", "Blog này hướng dẫn...".
- Viết tóm tắt dưới dạng truyền đạt trực tiếp kiến thức/nội dung. Người đọc summary phải có cảm giác họ đang đọc chính bài viết đó nhưng ở phiên bản cô đọng nhất. Bắt đầu thẳng vào vấn đề!

YÊU CẦU ĐỘ DÀI:
{length_instruction}
"""
        logger.info(f"Calling Gemini API to summarize blog post ({word_count} words)...")
        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=BlogSummary,
                temperature=0.3
            )
            time.sleep(4)
            response = self._generate_with_retry(prompt, config)
            result = json.loads(response.text)
            return result
        except Exception as e:
            logger.error(f"Failed to summarize blog via Gemini: {e}")
            return {"summary_content": "", "keywords_tags": []}
