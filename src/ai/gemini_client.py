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

class FeatureExtraction(BaseModel):
    feature_name: str
    original_text: str
    link: str

class ExtractedFeatures(BaseModel):
    features: list[FeatureExtraction]

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

    def extract_features(self, notes_dict: dict) -> list[dict]:
        if not self.client:
            logger.error("GeminiClient not initialized. Missing API Key or google-genai package.")
            return []
            
        prompt = f"""
        Bạn là một chuyên gia phân tích phần mềm. Hãy đọc cấu trúc Release Notes dưới đây:
        {json.dumps(notes_dict, ensure_ascii=False, indent=2)}
        
        Nhiệm vụ:
        1. Đọc và phân loại toàn bộ các mục trong Release Notes.
        2. CHỈ GIỮ LẠI các mục mô tả "Tính năng mới" (New Features) hoặc "Cải tiến" (Enhancements).
        3. LOẠI BỎ hoàn toàn: Bản vá lỗi (Bug fixes), Cập nhật tài liệu (Docs), Chores.
        4. Trích xuất đường link gốc đi kèm (nếu có) vào trường 'link'. Nếu không có để chuỗi rỗng "".
        """
        
        logger.info("Calling Gemini API to extract features (Semantic Filtering)...")
        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ExtractedFeatures,
                temperature=0.1
            )
            response = self._generate_with_retry(prompt, config)
            result = json.loads(response.text)
            return result.get("features", [])
        except Exception as e:
            logger.error(f"Failed to extract features via Gemini: {e}")
            return []

    def summarize_feature(self, issue_content: str) -> str:
        if not self.client:
            return "No API Key provided. Cannot summarize."
            
        # Giới hạn độ dài text nạp vào để tránh lỗi quota/context window quá khổ nếu crawl rác
        safe_content = issue_content[:50000] 
            
        prompt = f"""
        Bạn là một chuyên gia phân tích phần mềm. Hãy tóm tắt nội dung cuộc thảo luận / Pull Request / Issue dưới đây.
        
        NỘI DUNG:
        {safe_content}
        
        YÊU CẦU BẮT BUỘC:
        1. TUYỆT ĐỐI KHÔNG SỬ DỤNG CÂU DẪN DẮT (ví dụ: "Dưới đây là tóm tắt...", "Tuyệt vời...", "Tôi là AI..."). BẮT ĐẦU NGAY LẬP TỨC vào nội dung tóm tắt.
        2. Linh hoạt độ dài tùy độ khó, nhưng TUYỆT ĐỐI KHÔNG VƯỢT QUÁ 7 CÂU.
        3. Bắt buộc làm rõ 3 khía cạnh:
           - Bối cảnh / Vấn đề (Context/Problem)
           - Giải pháp kỹ thuật (Solution)
           - Giá trị mang lại (Impact/Benefit)
        4. Viết súc tích, dễ hiểu, có thể dùng format danh sách (bullet points).
        """
        
        logger.info("Calling Gemini API to summarize feature...")
        try:
            config = types.GenerateContentConfig(temperature=0.3)
            # Sleep 4s explicitly before summarizing each feature to smooth out requests (15 RPM limit)
            time.sleep(4) 
            response = self._generate_with_retry(prompt, config)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Failed to summarize via Gemini: {e}")
            return ""

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
