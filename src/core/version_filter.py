import re
import logging
from packaging.specifiers import SpecifierSet
from packaging.version import Version, InvalidVersion

logger = logging.getLogger(__name__)

def extract_lower_bound(constraints: list[str]) -> Version | None:
    """
    Trích xuất phiên bản cũ nhất (giới hạn dưới) cần thiết từ bộ constraints.
    Nếu có bất kỳ constraint nào mang tính mở xuống dưới (như 'all' hoặc '<'), trả về None (không có Lower Bound).
    """
    min_req_version = None
    
    for c in constraints:
        c = c.strip()
        if c == "all" or c == "latest":
            return None
            
        # Prefix == cho bản trơn
        if not any(c.startswith(op) for op in ['<', '>', '=', '~', '^', '!']):
            c = f"=={c}"
        if c.startswith('=') and not c.startswith('=='):
            c = "=" + c
            
        try:
            spec = SpecifierSet(c)
            for s in spec:
                if s.operator in ('>=', '>', '==', '~='):
                    try:
                        v = Version(s.version)
                        if min_req_version is None or v < min_req_version:
                            min_req_version = v
                    except InvalidVersion:
                        pass
                else:
                    # Nếu có < hoặc <= thì nó trôi về vô cực âm, không có lower bound
                    return None
        except Exception:
            pass
            
    return min_req_version

def resolve_target_versions(page_versions: list[str], constraint_config) -> tuple[list[str], bool]:
    """
    Nhận vào danh sách version của 1 trang (page) và trả về:
    - Danh sách các version thoả mãn.
    - Cờ báo hiệu (True/False) xem có nên dừng phân trang (Early Stop) hay không.
    """
    if not constraint_config or constraint_config == "all" or constraint_config == ["all"]:
        return page_versions, False
        
    if constraint_config == "latest" or constraint_config == ["latest"]:
        # Chế độ latest: Chỉ lấy phần tử đầu tiên của trang đầu tiên và NGẮT NGAY
        return ([page_versions[0]] if page_versions else []), True
        
    if isinstance(constraint_config, str):
        if constraint_config.strip() == "all":
            return page_versions, False
        if constraint_config.strip() == "latest":
            return ([page_versions[0]] if page_versions else []), True
            
        if ',' in constraint_config:
            parts = [c.strip() for c in constraint_config.split(',')]
            if all(bool(re.match(r'^={0,2}\s*[\w\.\-]+$', p)) for p in parts):
                constraints = parts
            else:
                constraints = [constraint_config]
        else:
            constraints = [constraint_config]
    elif isinstance(constraint_config, list):
        constraints = constraint_config
    else:
        return [], False

    matched_versions = set()
    
    for c in constraints:
        c = str(c).strip()
        if c == "all":
            return page_versions, False
            
        if c == "latest":
            if page_versions:
                matched_versions.add(page_versions[0])
            continue
            
        if not any(c.startswith(op) for op in ['<', '>', '=', '~', '^', '!']):
            c = f"=={c}"
        if c.startswith('=') and not c.startswith('=='):
            c = "=" + c
            
        try:
            spec = SpecifierSet(c)
            for v in page_versions:
                try:
                    if Version(v) in spec:
                        matched_versions.add(v)
                except InvalidVersion:
                    if c.startswith('==') and v == c[2:].strip():
                        matched_versions.add(v)
        except Exception as e:
            logger.error(f"Invalid version constraint '{c}': {e}")
            
    result_versions = [v for v in page_versions if v in matched_versions]
    
    # Lazy Evaluation: Kiểm tra xem đã vượt quá điểm đáy (lower bound) chưa
    should_stop = False
    
    # Nếu danh sách trang có dữ liệu và không phải 'all' hay mở đáy
    if page_versions and constraints:
        lower_bound = extract_lower_bound(constraints)
        if lower_bound:
            try:
                # Version cũ nhất của trang là phần tử cuối (vì mảng đã được sort desc)
                oldest_in_page = Version(page_versions[-1])
                if oldest_in_page < lower_bound:
                    should_stop = True
            except InvalidVersion:
                pass

    return result_versions, should_stop
