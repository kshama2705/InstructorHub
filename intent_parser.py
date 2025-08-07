
import re
from typing import Optional, Dict, Any

def parse_question(q: str) -> Optional[Dict[str, Any]]:
    qn = q.strip().lower()

    def first_int_after(keyword):
        m = re.search(rf'{keyword}\s+(\d+)', qn)
        return int(m.group(1)) if m else None

    # 1) enrolled
    if re.search(r'how many.*(students?).*(enrolled|in the course|total)', qn):
        return {"metric":"students_enrolled","params":{}}

    # 2) completed module X
    if re.search(r'how many.*completed.*module', qn):
        mid = first_int_after('module')
        if mid is None: return None
        return {"metric":"students_completed_module","params":{"module_id": mid}}

    # 3) completed assessment X but not Y (project)
    if re.search(r'how many.*completed.*(assessment|project).*but.*not.*(assessment|project)', qn):
        ids = [int(x) for x in re.findall(r'(assessment|project)\s+(\d+)', qn)]
        # pattern returns list of tuples; take the numeric parts
        nums = [int(n) for _, n in re.findall(r'(?:assessment|project)\s+(\d+)', qn)]
        if len(nums) >= 2:
            return {"metric":"students_completed_assessment_but_not_other",
                    "params":{"assessment_x": nums[0], "assessment_y": nums[1]}}
        return None

    # 4) completed assessment X
    if re.search(r'how many.*completed.*(assessment|project)', qn):
        aid = first_int_after('assessment') or first_int_after('project')
        if aid is None: return None
        return {"metric":"students_completed_assessment","params":{"assessment_id": aid}}

    # 5) completed the course
    if re.search(r'how many.*completed.*course', qn):
        return {"metric":"students_completed_course","params":{}}

    # 6) average score on assessment X
    if re.search(r'(average|avg).*(score).*(assessment|project)', qn):
        aid = first_int_after('assessment') or first_int_after('project')
        if aid is None: return None
        return {"metric":"average_assessment_score","params":{"assessment_id": aid}}

    # 7) student Y's average score
    if re.search(r"(what|student).*(average|avg).*(score)", qn) and "project" not in qn and "assessment" not in qn:
        sid = first_int_after('student')
        if sid is None: return None
        return {"metric":"student_average_score","params":{"student_id": sid}}

    # 8) time on module X (total or average)
    if re.search(r'(how long|time).*module', qn):
        mid = first_int_after('module')
        if mid is None: return None
        if "average" in qn or "avg" in qn:
            return {"metric":"average_time_on_module_per_student","params":{"module_id": mid}}
        else:
            return {"metric":"total_time_on_module","params":{"module_id": mid}}

    # 9) average rating on module X
    if re.search(r'(average|avg).*(rating).*(module)', qn):
        mid = first_int_after('module')
        if mid is None: return None
        return {"metric":"average_module_rating","params":{"module_id": mid}}

    # 10) feedback count for module X
    if re.search(r'(how many|feedback|comments).*feedback.*(module)', qn):
        mid = first_int_after('module')
        if mid is None: return None
        return {"metric":"module_feedback_count","params":{"module_id": mid}}

    # 11) satisfaction rate for module X
    if re.search(r'(satisfaction|satisfied).*(rate|percentage).*(module)', qn):
        mid = first_int_after('module')
        if mid is None: return None
        return {"metric":"module_satisfaction_rate","params":{"module_id": mid}}

    # 12) course average rating
    if re.search(r'(average|avg).*(rating).*(course)', qn):
        return {"metric":"course_average_rating","params":{}}

    # 13) course satisfaction rate
    if re.search(r'(satisfaction|satisfied).*(rate|percentage).*(course)', qn):
        return {"metric":"course_satisfaction_rate","params":{}}

    # 14) low rated modules
    if re.search(r'(low|poor|worst).*(rated|rating|performance).*(modules?)', qn):
        return {"metric":"low_rated_modules","params":{}}

    return None
