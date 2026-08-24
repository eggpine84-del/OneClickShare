# [파일명]: module.py (부품 모듈용 템플릿) | [원칙] 구역 준수해서작성, 로직 끝에 12세 수준 요약 주석 필수
# [체크] 1. 에러 경로에 log_error(...) 누락 방지 | 2. 배포 전 __main__ 테스트 코드 주석/삭제 필수
# [SYSTEM] Senior Staff Engineer (Google/Amazon) - Safe, Readable, Scalable Code.
import logging,asyncio; from typing import Dict,Any,Tuple,Optional
# [수정 1] LOG_FILE_PATH 제거 (메인에서 관리하므로 모듈에선 불필요)
ERR_VAL_CODE,ERR_VAL_MSG,ERR_SYSTEM_CODE="VAL_ERR_01","입력 데이터가 올바르지 않거나 비어 있습니다.","SYS_ERR_99"
# [수정 2] os.makedirs와 basicConfig를 지우고, 모듈 전용 이름표(getLogger)만 남김
default_logger=logging.getLogger(__name__)

async def log_error(code:str,message:str,logger:logging.Logger=default_logger)->None:
    """Logs system errors. Args: code(str), message(str), logger(logging.Logger)."""
    logger.error(f"[{code}] {message}") # [요약] 프로그램이 일하다가 실수한 내용을 외부에서 넘겨받은 '로그 메모장(logger)'에 안전하게 적어두는 기능입니다!
async def validate_and_prepare_input(raw_data:Optional[Dict[str,Any]])->Tuple[bool,Optional[Dict[str,Any]],str]:
    """Validates runtime input type."""
    if not isinstance(raw_data,dict): await log_error(ERR_VAL_CODE,ERR_VAL_MSG); return False,None,ERR_VAL_MSG # [체크 1] 에러 기록 누락 방지
    return True,raw_data,"검증 통과" # [요약] 들어온 상자가 찌그러지지 않은 올바른 상자(딕셔너리)인지 문지기처럼 꼼꼼하게 검사했습니다!
async def process_core_behavior(validated_data:Dict[str,Any])->Dict[str,Any]:
    """Executes business operations asynchronously."""
    try: return {"success":True,"result":{**validated_data,"processed_at":"2026-07-15"},"error":""} # [요약] 진짜 해야 할 중요한 일(연산/저장)을 원본 데이터의 훼손 없이 안전하게 마쳤습니다!
    except Exception as e: await log_error(ERR_SYSTEM_CODE,f"핵심 로직 실행 중 오류 발생: {e}"); return {"success":False,"result":None,"error":f"핵심 로직 실행 중 오류 발생: {e}"} # [체크 1] 에러 기록 누락 방지
async def run_main_workflow(raw_input:Optional[Dict[str,Any]])->Dict[str,Any]:
    """Coordinates the entire workflow lifecycle (Async Native)."""
    is_valid,clean_data,error_message=await validate_and_prepare_input(raw_input)
    if not is_valid: return {"success":False,"result":None,"error":error_message}
    return await process_core_behavior(clean_data)

def run_main_workflow_sync(raw_input:Optional[Dict[str,Any]])->Dict[str,Any]:
    """Provides a synchronous wrapper for legacy or synchronous environments."""
    try: loop=asyncio.get_running_loop()
    except RuntimeError: loop=None
    if loop and loop.is_running(): raise RuntimeError("이미 루프가 돌고 있습니다. await run_main_workflow()를 사용하세요.")
    return asyncio.run(run_main_workflow(raw_input)) 
    # [요약] 매니저가 비동기 손님과 동기 손닙 모두를 안전하게 맞이할 수 있도록 최종 출구를 두 개로 만든 결말 구역입니다!

# ================= (동기/비동기 다 품는 유니버설 테스트 구역) =================
# [체크 2] 본 테스트 코드는 Pure Function(FCIS) 검증용 단정문(assert) 구문으로 작성되었습니다.
if __name__=="__main__":
    async def _run_async_tests():
        res_suc,res_fail=await asyncio.gather(run_main_workflow({'test_key':'async_value'}),run_main_workflow(None))
        assert res_suc.get("success") is True
        assert res_fail.get("success") is False
    asyncio.run(_run_async_tests())
    res_sync_suc=run_main_workflow_sync({'test_key':'sync_value'})
    res_sync_fail=run_main_workflow_sync(None)
    assert res_sync_suc.get("success") is True
    assert res_sync_fail.get("success") is False