# src/analyzer/release_analyzer.py
from packaging.version import parse, InvalidVersion

class ReleaseAnalyzer:
    def analyze(self, latest: str, previous: str, notes: dict) -> dict:
        try:
            v_latest = parse(latest)
            v_prev = parse(previous)
            
            if v_latest.major > v_prev.major:
                risk = "High"
                impact = "Major version bump. Breaking changes are guaranteed."
                rec = "Do not upgrade in production without extensive regression testing."
            elif v_latest.minor > v_prev.minor:
                risk = "Medium"
                impact = "Minor version bump. New features added, possible deprecations."
                rec = "Safe for staging. Review deprecation notices before production rollout."
            else:
                risk = "Low"
                impact = "Patch version bump. Primarily bug and security fixes."
                rec = "Highly recommended to upgrade immediately to ensure stability."
        
        except InvalidVersion:
            # Xử lý an toàn cho MinIO hoặc các tool không chuẩn SemVer
            risk = "Medium"
            impact = "Non-semantic version format detected (Date-based release)."
            rec = "Review release notes carefully. Automated version comparison is skipped."

        # === QUÉT BẢO MẬT ===
        has_security_patch = False
        for category, items in notes.items():
            if 'security' in category.lower() or 'cve' in category.lower():
                has_security_patch = True
                break
            
            for item in items:
                text_to_check = ""
                
                # SỬA LỖI TẠI ĐÂY: Kiểm tra kiểu dữ liệu trước khi xử lý
                if isinstance(item, str):
                    text_to_check = item.lower()
                elif isinstance(item, dict) and item.get('type') == 'table':
                    # Ép kiểu toàn bộ data của bảng thành string để quét từ khóa nhanh
                    text_to_check = str(item.get('data', [])).lower()

                if 'cve-' in text_to_check or 'vulnerability' in text_to_check:
                    has_security_patch = True
                    break
                    
            if has_security_patch:
                break

        if has_security_patch:
            rec += " CRITICAL: Security patches detected. Prioritize this upgrade."
            if risk == "Low":
                risk = "Medium" # Nâng mức cảnh báo nếu có vá lỗi bảo mật

        return {
            'risk_level': risk,
            'upgrade_impact': impact,
            'recommendation': rec,
            'breaking_changes': "See deprecations" if risk != "Low" else "None expected"
        }